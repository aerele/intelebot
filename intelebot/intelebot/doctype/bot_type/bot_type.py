# -*- coding: utf-8 -*-
# Copyright (c) 2021, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class BotType(Document):
	pass

def create_default_bot_type():
	bot_type_doc = frappe.get_doc({'doctype':'Bot Type','type':'Send Report'})
	bot_type_doc.save()