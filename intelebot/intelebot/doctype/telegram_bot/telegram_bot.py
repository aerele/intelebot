# Copyright (c) 2021, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _, msgprint
from frappe.model.document import Document
from frappe.utils import cint

from intelebot import telegram_client


class TelegramBot(Document):
	pass


@frappe.whitelist()
def create_telegram_chat(bot_name=None):
	# Called every 30 minutes via hooks, or by the Fetch Now button.
	if bot_name:
		bot_doc = frappe.get_doc("Telegram Bot", bot_name)
		bot_doc.check_permission("write")
		bot_doc_list = [bot_doc]
	else:
		frappe.only_for("System Manager")
		bots = frappe.get_all("Telegram Bot", filters={"disabled": 0}, fields=["name"])
		bot_doc_list = [frappe.get_doc("Telegram Bot", bot.name) for bot in bots]

	updates = get_updates(bot_doc_list)
	for bot, chats in updates.items():
		for chat in chats:
			existing = frappe.db.get_value("Telegram Chat", {"chat_id": str(chat.id), "bot": bot})
			if existing:
				tele_chat = frappe.get_doc("Telegram Chat", existing)
			else:
				tele_chat = frappe.get_doc({
					"doctype": "Telegram Chat",
					"chat_id": str(chat.id),
					"bot": bot,
				})
			assign_values_based_on_type(tele_chat, chat)

	if bot_name:
		if bot_name in updates:
			msgprint(_("Telegram chats created"))
		else:
			frappe.throw(_("An error occurred. Check error log for more info"))


def assign_values_based_on_type(tele_chat, chat):
	# Optional fields are absent for many private/group chats. Retain support
	# for dictionaries accepted by the original helper.
	data = chat.to_dict() if hasattr(chat, "to_dict") else chat
	tele_chat.chat_type = data.get("type", tele_chat.chat_type)
	tele_chat.first_name = data.get("first_name") if tele_chat.chat_type == "private" else None
	tele_chat.last_name = data.get("last_name") if tele_chat.chat_type == "private" else None
	tele_chat.title = data.get("title") if tele_chat.chat_type in {"group", "supergroup", "channel"} else None
	tele_chat.username = data.get("username")
	tele_chat.save()


def get_updates(bot_doc_list):
	update_list = {}
	for bot_doc in bot_doc_list:
		try:
			# The existing field stores the last seen ID, not the next offset.
			last_id = cint(bot_doc.last_update_id)
			updates = telegram_client.get_updates(bot_doc.api_token, last_id + 1 if last_id else 0)
			chats = {}
			for update in updates:
				chat = update.effective_chat
				if chat is not None:
					chats[chat.id] = chat
				last_id = max(last_id, update.update_id)
			if updates:
				bot_doc.last_update_id = str(last_id)
				bot_doc.save()
			# Empty polling is successful too; Fetch Now must not report an error.
			update_list[bot_doc.name] = set(chats.values())
		except Exception:
			frappe.log_error(title=f"{bot_doc.name} get updates error", message=frappe.get_traceback())
	return update_list
