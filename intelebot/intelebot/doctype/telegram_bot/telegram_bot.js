// Copyright (c) 2021, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Telegram Bot', {
	fetch_now: function(frm){
		frappe.call({
			method: "intelebot.intelebot.doctype.telegram_bot.telegram_bot.create_telegram_chat",
			args: {bot_name: frm.doc.name},
			freeze: true
		})
	}
});
