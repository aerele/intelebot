# -*- coding: utf-8 -*-
# Copyright (c) 2021, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals 
import frappe
import telegram

def send_document(bot_token, url_list):
	for url_info in url_list:
		for chat_id in url_info['chat_id_list']:
			try:
				bot = telegram.Bot(token=bot_token)
				res = bot.sendDocument(chat_id, url_info['url'])
			except:
				error_message = frappe.get_traceback()
				frappe.log_error(error_message, "Telegram Group - Send Reports Error")
				raise