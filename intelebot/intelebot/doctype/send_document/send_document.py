# -*- coding: utf-8 -*-
# Copyright (c) 2021, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import telegram
import json
from six import string_types
from frappe.model.document import Document
from frappe.utils import get_files_path
from frappe import _

class SendDocument(Document):
	def after_insert(self):
		if self.file:
			self.send_document()
		else:
			frappe.throw(_("Please select File"))

	def send_document(self):
		try:
			token = frappe.db.get_value('Telegram Bot', self.bot, 'api_token')
			chat_id = frappe.db.get_value('Telegram Chat', self.telegram_chat, 'chat_id')
			file_name = frappe.db.get_value('File', self.file, 'file_name')
			if self.status == 'Error':
				self.resend_count += 1
			bot = telegram.Bot(token = token)
			res = bot.sendDocument(chat_id, document=open(get_files_path(file_name, is_private=0), "rb"))
			if res:
				self.status = 'Completed'
				self.error_message = None
				if self.delete_linked_file_after_sent:
					file_name = self.file
					self.file = None
					self.save(ignore_permissions=True)
					frappe.delete_doc('File', file_name, force=1)

		except:
			self.status = 'Error'
			self.error_message = frappe.get_traceback()
		self.save(ignore_permissions=True)

def process_unsent_document():
	# Called every 30 minutes via hooks
	unsent_doc_list = frappe.db.get_all('Send Document',{'status':['in', ['Queued','Error']]},['name'])
	for doc_name in unsent_doc_list:
		doc = frappe.get_doc('Send Document', doc_name['name'])
		if not doc.resend_count > 10 and doc.file:
			if doc.error_message and not doc.error_message.split('\n')[-2] == 'telegram.error.TimedOut: Timed out':
				continue
			doc.send_document()

@frappe.whitelist()
def send_doc_to_telegram(doc):
	if isinstance(doc, string_types):
		doc = frappe._dict(json.loads(doc))

	if doc.file:
		doc = frappe.get_doc('Send Document', doc.name)
		doc.send_document()
	else:
		frappe.throw(_("Please select File"))