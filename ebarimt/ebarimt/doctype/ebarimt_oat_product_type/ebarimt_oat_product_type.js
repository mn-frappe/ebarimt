// Copyright (c) 2024, Orchlon and contributors
// For license information, please see license.txt

frappe.ui.form.on("eBarimt OAT Product Type", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("View Items"), function () {
				frappe.set_route("List", "Item", {
					ebarimt_oat_product_type: frm.doc.name,
				});
			});
		}
	},
});
