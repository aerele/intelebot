# Copyright (c) 2021, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from intelebot import telegram_client


class SendDocument(Document):
	def after_insert(self):
		if not self.file:
			frappe.throw(_("Please select File"))
		self.send_document()

	def send_document(self):
		if self.status == "Completed":
			return
		if self.status == "Error":
			self.resend_count = cint(self.resend_count) + 1
		try:
			token = frappe.db.get_value("Telegram Bot", self.bot, "api_token")
			chat_id = frappe.db.get_value("Telegram Chat", self.telegram_chat, "chat_id")
			file_doc = frappe.get_doc("File", self.file)
			# Preserve the public-local-file contract, resolving the actual URL
			# instead of guessing the disk path from the display filename.
			if file_doc.is_private or file_doc.is_remote_file:
				frappe.throw(_("Please select a public file stored on this site"))
			result = telegram_client.send_document(token, chat_id, file_doc.get_full_path())
			if not result:
				raise RuntimeError("Telegram did not confirm document delivery")
		except Exception:
			self.status = "Error"
			self.error_message = frappe.get_traceback()
			self.save(ignore_permissions=True)
			return

		self.status = "Completed"
		self.error_message = None
		self.save(ignore_permissions=True)
		if self.delete_linked_file_after_sent:
			file_name = self.file
			frappe.db.savepoint("intelebot_file_cleanup")
			try:
				self.file = None
				self.save(ignore_permissions=True)
				frappe.delete_doc("File", file_name, force=1)
			except Exception:
				# Telegram already accepted the upload. Cleanup failure must not
				# turn it into an Error and trigger a duplicate scheduled send.
				frappe.db.rollback(save_point="intelebot_file_cleanup")
				self.file = file_name
				self.error_message = frappe.get_traceback()
				self.save(ignore_permissions=True)
				frappe.log_error(title="Telegram file cleanup failed", message=self.error_message)


def process_unsent_document():
	# Preserve scheduled retries for queued items and timed-out sends only.
	unsent = frappe.get_all(
		"Send Document", filters={"status": ["in", ["Queued", "Error"]]}, fields=["name"]
	)
	for row in unsent:
		doc = frappe.get_doc("Send Document", row.name)
		if cint(doc.resend_count) > 10 or not doc.file:
			continue
		if doc.error_message:
			lines = doc.error_message.strip().splitlines()
			if not lines or not lines[-1].startswith("telegram.error.TimedOut:"):
				continue
		doc.send_document()


@frappe.whitelist()
def send_doc_to_telegram(doc):
	if isinstance(doc, str):
		doc = json.loads(doc)
	# Read persisted state rather than trusting submitted status/file fields.
	stored = frappe.get_doc("Send Document", doc.get("name"))
	stored.check_permission("write")
	if stored.status == "Completed":
		return
	if not stored.file:
		frappe.throw(_("Please select File"))
	stored.send_document()
