"""Frappe controller regression tests with database and Telegram I/O mocked.

Run with a bench interpreter to use the actual Frappe Document/decorator APIs.
No site, bot credentials, database writes or live Telegram calls are required.
"""

import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from telegram import Chat, Message, Update
from telegram.error import TimedOut

from intelebot.intelebot.doctype.send_document import send_document as sending
from intelebot.intelebot.doctype.telegram_bot import telegram_bot as discovery


class FrappeTestCase(unittest.TestCase):
	def setUp(self):
		self.enterContext(patch.object(frappe.local, "flags", frappe._dict(in_test=True), create=True))
		self.db = Mock()
		for name, value in {
			"db": self.db, "get_doc": Mock(), "get_all": Mock(),
			"log_error": Mock(), "get_traceback": Mock(return_value="Traceback\ntelegram.error.TimedOut: Timed out\n"),
			"delete_doc": Mock(), "only_for": Mock(),
		}.items():
			self.enterContext(patch.object(frappe, name, value))
		self.enterContext(patch.object(sending, "_", lambda text: text))
		self.enterContext(patch.object(discovery, "_", lambda text: text))
		self.enterContext(patch.object(discovery, "msgprint", Mock()))
		def throw(message, *args, **kwargs):
			raise ValueError(message)
		self.enterContext(patch.object(frappe, "throw", throw))


class TestChatDiscovery(FrappeTestCase):
	def bot(self, name="test_bot", last_id="0"):
		return SimpleNamespace(name=name, api_token="123:TEST", last_update_id=last_id, save=Mock(), check_permission=Mock())

	def update(self, id, chat, channel=False):
		message = Message(id, datetime.now(timezone.utc), chat)
		return Update(id, **{"channel_post" if channel else "message": message})

	def test_chat_types_optional_fields_and_removed_fields(self):
		for chat in [Chat(1, "private", first_name="Pat"), Chat(-1, "group", title="Group"), Chat(-2, "supergroup", title="Super"), Chat(-3, "channel", title="News")]:
			with self.subTest(type=chat.type):
				doc = SimpleNamespace(chat_type="private", first_name="old", last_name="old", username="old", title="old", save=Mock())
				discovery.assign_values_based_on_type(doc, chat)
				self.assertEqual(doc.chat_type, chat.type)
				self.assertEqual(doc.first_name, "Pat" if chat.type == "private" else None)
				self.assertEqual(doc.title, chat.title)
				self.assertIsNone(doc.last_name)
				self.assertIsNone(doc.username)
				doc.save.assert_called_once()

	def test_update_offset_is_integer_and_duplicate_chats_use_latest_data(self):
		bot = self.bot(last_id="42")
		updates = [self.update(43, Chat(1, "private", first_name="Old")), self.update(44, Chat(1, "private", first_name="New")), self.update(45, Chat(-1, "channel", title="News"), channel=True), Update(46)]
		with patch.object(discovery.telegram_client, "get_updates", return_value=updates) as fetch:
			result = discovery.get_updates([bot])
		fetch.assert_called_once_with("123:TEST", 43)
		self.assertEqual(bot.last_update_id, "46")
		self.assertEqual({chat.id for chat in result[bot.name]}, {1, -1})
		self.assertEqual(next(chat for chat in result[bot.name] if chat.id == 1).first_name, "New")
		bot.save.assert_called_once()

	def test_empty_poll_succeeds_without_advancing_offset(self):
		bot = self.bot()
		frappe.get_doc.return_value = bot
		with patch.object(discovery.telegram_client, "get_updates", return_value=()):
			discovery.create_telegram_chat(bot.name)
		bot.save.assert_not_called()
		discovery.msgprint.assert_called_once()

	def test_one_failed_bot_does_not_stop_other_bots(self):
		first, second = self.bot("first", "5"), self.bot("second")
		with patch.object(discovery.telegram_client, "get_updates", side_effect=[TimedOut(), ()]):
			self.assertEqual(discovery.get_updates([first, second]), {"second": set()})
		self.assertEqual(first.last_update_id, "5")
		first.save.assert_not_called()
		frappe.log_error.assert_called_once()

	def test_scheduler_filters_disabled_bots_and_updates_existing_chat(self):
		bot = self.bot()
		chat_doc = SimpleNamespace(chat_type="private", save=Mock())
		frappe.get_all.return_value = [frappe._dict(name=bot.name)]
		frappe.get_doc.side_effect = [bot, chat_doc]
		self.db.get_value.return_value = "TC-1"
		with patch.object(discovery.telegram_client, "get_updates", return_value=[self.update(1, Chat(1, "private", first_name="Pat"))]):
			discovery.create_telegram_chat()
		self.assertEqual(frappe.get_all.call_args.kwargs["filters"], {"disabled": 0})
		self.assertEqual(chat_doc.first_name, "Pat")
		self.assertEqual(frappe.get_doc.call_args.args, ("Telegram Chat", "TC-1"))

	def test_manual_fetch_requires_permission_before_network_call(self):
		bot = self.bot()
		bot.check_permission.side_effect = PermissionError
		frappe.get_doc.return_value = bot
		with patch.object(discovery.telegram_client, "get_updates") as fetch:
			with self.assertRaises(PermissionError):
				discovery.create_telegram_chat(bot.name)
		fetch.assert_not_called()


class TestSending(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.file_doc = SimpleNamespace(is_private=0, is_remote_file=False, get_full_path=Mock(return_value="/site/public/files/file.pdf"))
		frappe.get_doc.return_value = self.file_doc
		self.db.get_value.side_effect = lambda doctype, *args: "123:TEST" if doctype == "Telegram Bot" else "456"
		self.send = self.enterContext(patch.object(sending.telegram_client, "send_document", return_value=object()))

	def document(self, **overrides):
		# Use the real controller class, replacing only database persistence.
		doc = sending.SendDocument.__new__(sending.SendDocument)
		doc.__dict__.update(dict(name="SD-1", bot="test_bot", telegram_chat="TC-1", file="FILE-1", status="Queued", resend_count=0, error_message=None, delete_linked_file_after_sent=0, save=Mock(), check_permission=Mock()))
		doc.__dict__.update(overrides)
		return doc

	def test_insert_sends_synchronously_before_marking_completed(self):
		doc = self.document()
		def send(*args):
			self.assertEqual(doc.status, "Queued")
			return object()
		self.send.side_effect = send
		doc.after_insert()
		self.assertEqual(doc.status, "Completed")
		self.assertIsNone(doc.error_message)
		self.send.assert_called_once_with("123:TEST", "456", "/site/public/files/file.pdf")
		frappe.delete_doc.assert_not_called()

	def test_error_does_not_delete_file_and_retry_increments_counter(self):
		doc = self.document(status="Error", resend_count=None, delete_linked_file_after_sent=1)
		self.send.side_effect = TimedOut()
		doc.send_document()
		self.assertEqual(doc.status, "Error")
		self.assertEqual(doc.resend_count, 1)
		self.assertEqual(doc.file, "FILE-1")
		self.assertIn("TimedOut", doc.error_message)
		frappe.delete_doc.assert_not_called()

	def test_delete_only_after_confirmed_success(self):
		doc = self.document(delete_linked_file_after_sent=1)
		def delete(*args, **kwargs):
			self.assertEqual(doc.status, "Completed")
			self.assertIsNone(doc.file)
		frappe.delete_doc.side_effect = delete
		doc.send_document()
		frappe.delete_doc.assert_called_once_with("File", "FILE-1", force=1)

	def test_cleanup_failure_keeps_completed_and_restores_file_link(self):
		doc = self.document(delete_linked_file_after_sent=1)
		frappe.delete_doc.side_effect = OSError("cleanup failed")
		doc.send_document()
		self.assertEqual(doc.status, "Completed")
		self.assertEqual(doc.file, "FILE-1")
		self.db.rollback.assert_called_once_with(save_point="intelebot_file_cleanup")
		doc.send_document()
		self.send.assert_called_once()

	def test_unconfirmed_send_stays_error(self):
		doc = self.document(delete_linked_file_after_sent=1)
		self.send.return_value = None
		doc.send_document()
		self.assertEqual(doc.status, "Error")
		frappe.delete_doc.assert_not_called()

	def test_private_or_remote_file_is_not_sent(self):
		for field in ["is_private", "is_remote_file"]:
			with self.subTest(field=field):
				setattr(self.file_doc, field, True)
				doc = self.document()
				doc.send_document()
				self.assertEqual(doc.status, "Error")
				setattr(self.file_doc, field, False)
		self.send.assert_not_called()

	def test_scheduler_preserves_retry_policy_and_limit(self):
		docs = [self.document(name="queued"), self.document(name="timeout", status="Error", error_message="Traceback\ntelegram.error.TimedOut: Timed out\n"), self.document(name="bad", status="Error", error_message="telegram.error.BadRequest: Invalid chat"), self.document(name="exhausted", resend_count=11), self.document(name="missing", file=None)]
		for doc in docs:
			doc.send_document = Mock()
		frappe.get_all.return_value = [frappe._dict(name=doc.name) for doc in docs]
		frappe.get_doc.side_effect = docs
		sending.process_unsent_document()
		self.assertEqual([doc.send_document.call_count for doc in docs], [1, 1, 0, 0, 0])

	def test_manual_send_uses_persisted_file_and_checks_permission(self):
		doc = self.document()
		frappe.get_doc.side_effect = [doc, self.file_doc]
		sending.send_doc_to_telegram(json.dumps({"name": doc.name, "file": "spoofed"}))
		doc.check_permission.assert_called_once_with("write")
		self.assertEqual(frappe.get_doc.call_args.args, ("File", "FILE-1"))

	def test_completed_document_is_not_resent(self):
		doc = self.document(status="Completed", file=None)
		frappe.get_doc.return_value = doc
		sending.send_doc_to_telegram({"name": doc.name})
		self.send.assert_not_called()
