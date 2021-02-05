// Copyright (c) 2021, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Send Document', {
	refresh: function(frm) {
		if(!frm.doc.__islocal && frm.doc.status != 'Completed') {
			frm.add_custom_button(__("Send To Telegram"), function() {
				frm.trigger('send_to_telegram');
			});
		}
	},
	send_to_telegram: function(frm){
		frappe.call({
			method: "intelebot.intelebot.doctype.send_document.send_document.send_doc_to_telegram",
			freeze: true,
			args: {doc: frm.doc},
			callback: function(r) {
				frm.reload_doc();
			}
		})
	}
});
