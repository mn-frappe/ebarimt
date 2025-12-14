// Copyright (c) 2024, Orchlon and contributors
// For license information, please see license.txt

frappe.ui.form.on("eBarimt Product Code", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("View Items"), function () {
				frappe.set_route("List", "Item", {
					ebarimt_product_code: frm.doc.name,
				});
			});
		}
	},

	product_code(frm) {
		// Auto-format product code
		if (frm.doc.product_code) {
			frm.set_value("product_code", frm.doc.product_code.trim());
		}
	},
});
