// Copyright (c) 2024, Orchlon and contributors
// For license information, please see license.txt

frappe.ui.form.on("eBarimt Tax Code", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("View Usage"), function () {
				frappe.set_route("List", "eBarimt Receipt Log", {
					tax_code: frm.doc.name,
				});
			});
		}
	},
});
