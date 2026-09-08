"""Synchronous boundary for Frappe hooks and python-telegram-bot's async API.

Only Telegram I/O runs in the event loop. Frappe documents and database access
stay in the calling thread/context. A Bot is never reused across event loops.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import telegram


def _run(operation, *args):
	try:
		asyncio.get_running_loop()
	except RuntimeError:
		return asyncio.run(operation(*args))
	# Support synchronous callers embedded in an already-running event loop.
	# Frappe I/O must stay outside this worker thread.
	with ThreadPoolExecutor(max_workers=1) as executor:
		return executor.submit(lambda: asyncio.run(operation(*args))).result()


def get_updates(token, offset):
	return _run(_get_updates, token, offset)


async def _get_updates(token, offset):
	async with telegram.Bot(token=token) as bot:
		return await bot.get_updates(limit=100, offset=offset)


def send_document(token, chat_id, file_path):
	return _run(_send_document, token, chat_id, file_path)


async def _send_document(token, chat_id, file_path):
	async with telegram.Bot(token=token) as bot:
		with open(file_path, "rb") as document:
			return await bot.send_document(chat_id=chat_id, document=document)
