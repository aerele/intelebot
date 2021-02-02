# -*- coding: utf-8 -*-
# Copyright (c) 2021, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import telegram
from frappe.model.document import Document
from frappe.utils import get_files_path

class TelegramBot(Document):
	pass

def create_telegram_chat():
	# Called every 30 minutes via hooks
	bot_doc_list = []
	bots = frappe.db.get_all('Telegram Bot',{'disabled':0},['name'])

	for bot in bots:
		bot_doc_list.append(frappe.get_doc('Telegram Bot', bot['name']))

	updates = get_updates(bot_doc_list)

	for bot in updates.keys():
		for chat in updates[bot]:
			existing_tele_chat = frappe.db.get_value("Telegram Chat", {'chat_id':chat['id'],'bot':bot})
			if not existing_tele_chat:
				tele_chat = frappe.get_doc({
					'doctype': 'Telegram Chat',
					'chat_id':chat['id'],
					'bot':bot,
					'chat_type':chat['type']})
				assign_values_based_on_type(tele_chat, chat)
			else:
				doc = frappe.get_doc('Telegram Chat',{'chat_id':chat['id'],'bot':bot})
				assign_values_based_on_type(doc, chat)

def assign_values_based_on_type(tele_chat, chat):
	if tele_chat.chat_type == 'private':
		tele_chat.first_name = chat['first_name']
		tele_chat.last_name = chat['last_name']
		tele_chat.username = chat['username']
	if tele_chat.chat_type == 'supergroup' or 'channel':
		tele_chat.title = chat['title']
		tele_chat.username = chat['username']
	if tele_chat.chat_type == 'group':
		tele_chat.title = chat['title']
	tele_chat.save()

def get_updates(bot_doc_list):
	update_list = {}
	for bot_doc in bot_doc_list:
		try:
			chats = []
			bot = telegram.Bot(token = bot_doc.api_token)
			updates = bot.get_updates(limit=100,offset = bot_doc.last_update_id)
			for update in updates:
				if update['message']:
					chats.append(update['message']['chat'])

				if update['channel_post']:
					chats.append(update['channel_post']['chat'])
				
				bot_doc.last_update_id = update['update_id']
			bot_doc.save()

		except Exception as e:
			frappe.log_error(frappe.get_traceback(), f'{bot_doc.name} get updates error')
			continue

		update_list[bot_doc.name] = set(chats)
	return update_list

def send_document(token, chat_id, file_name = None, file_url = None):
	try:
		bot = telegram.Bot(token = token)
		if file_name:
			res = bot.sendDocument(chat_id, document=open(get_files_path(file_name, is_private=0), "rb"))
		if file_url:
			res = bot.sendDocument(chat_id, file_url)
		if (file_name or file_url) and res:
			return {'status': 'Sent'}
		else:
			return {'status': 'Error', 'message': 'Mention file_url or file_name to send document'}
	except:
		return {'status': 'Error', 'message': frappe.get_traceback()}