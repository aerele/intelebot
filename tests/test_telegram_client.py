"""Exercise the real PTB 22 transport without contacting Telegram."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import telegram
from telegram.request import HTTPXRequest

from intelebot import telegram_client


class TestTelegramClient(unittest.TestCase):
	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp.cleanup)
		self.path = Path(self.temp.name) / "sample.pdf"
		self.path.write_bytes(b"%PDF-test-payload")
		self.calls = []
		self.requests = []
		self.fail_send = False
		bot_class = telegram.Bot

		def respond(request):
			method = request.url.path.rsplit("/", 1)[-1]
			self.calls.append((method, request.read()))
			if method == "getMe":
				result = {"id": 123, "is_bot": True, "first_name": "Test", "username": "test_bot"}
			elif method == "getUpdates":
				result = [{"update_id": 9, "message": {
					"message_id": 1, "date": 1,
					"chat": {"id": 456, "type": "private", "first_name": "Customer"},
				}}]
			elif method == "sendDocument":
				if self.fail_send:
					return httpx.Response(400, json={"ok": False, "error_code": 400, "description": "Bad Request: chat not found"})
				result = {"message_id": 2, "date": 1, "chat": {"id": 456, "type": "private", "first_name": "Customer"}}
			else:
				raise AssertionError(f"Unexpected Telegram method: {method}")
			return httpx.Response(200, json={"ok": True, "result": result})

		def make_bot(token):
			requests = [HTTPXRequest(httpx_kwargs={"transport": httpx.MockTransport(respond)}) for _ in range(2)]
			self.requests.extend(requests)
			return bot_class(token=token, request=requests[0], get_updates_request=requests[1])

		self.addCleanup(patch.stopall)
		patch.object(telegram_client.telegram, "Bot", side_effect=make_bot).start()

	def assert_closed(self):
		self.assertTrue(self.requests)
		self.assertTrue(all(request._client.is_closed for request in self.requests))

	def test_get_updates_returns_real_updates_and_awaits_transport(self):
		updates = telegram_client.get_updates("123:TEST", 8)
		self.assertIsInstance(updates[0], telegram.Update)
		self.assertEqual(updates[0].effective_chat.id, 456)
		body = next(body for method, body in self.calls if method == "getUpdates")
		self.assertIn(b"offset=8", body)
		self.assertIn(b"limit=100", body)
		self.assert_closed()

	def test_repeated_sends_use_new_loops_and_upload_original_bytes(self):
		for _ in range(2):
			result = telegram_client.send_document("123:TEST", "456", self.path)
			self.assertIsInstance(result, telegram.Message)
			self.assertEqual(result.message_id, 2)
		bodies = [body for method, body in self.calls if method == "sendDocument"]
		self.assertEqual(len(bodies), 2)
		self.assertTrue(all(b"%PDF-test-payload" in body for body in bodies))
		self.assert_closed()

	def test_failure_propagates_and_closes_file_and_http_clients(self):
		self.fail_send = True
		handles = []
		def open_document(*args, **kwargs):
			handle = open(*args, **kwargs)
			handles.append(handle)
			return handle
		with patch("intelebot.telegram_client.open", side_effect=open_document, create=True):
			with self.assertRaises(telegram.error.BadRequest):
				telegram_client.send_document("123:TEST", "456", self.path)
		self.assertEqual(len(handles), 1)
		self.assertTrue(handles[0].closed)
		self.assert_closed()

	def test_sync_boundary_also_works_inside_running_loop(self):
		async def caller():
			return telegram_client.get_updates("123:TEST", 0)
		self.assertEqual(asyncio.run(caller())[0].update_id, 9)
		self.assert_closed()
