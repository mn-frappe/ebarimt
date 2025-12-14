// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('POS Invoice', {
	refresh: function(frm) {
		// Check if eBarimt is enabled
		if (!frappe.boot.ebarimt || !frappe.boot.ebarimt.enabled) {
			return;
		}
		
		// Show eBarimt status for submitted invoices
		if (frm.doc.docstatus === 1) {
			if (frm.doc.custom_ebarimt_receipt_id) {
				frm.dashboard.add_indicator(
					__('eBarimt: ✓ {0}', [frm.doc.custom_ebarimt_lottery || 'Sent']),
					'green'
				);
			} else {
				frm.dashboard.add_indicator(__('eBarimt: Not Sent'), 'orange');
			}
		}
	},
	
	customer: function(frm) {
		// Auto-set B2B for customers with TIN
		if (frm.doc.customer) {
			frappe.db.get_value('Customer', frm.doc.customer, 'custom_tin', (r) => {
				if (r && r.custom_tin) {
					frm.set_value('custom_ebarimt_bill_type', 'B2B_RECEIPT');
				} else {
					frm.set_value('custom_ebarimt_bill_type', 'B2C_RECEIPT');
				}
			});
		}
	}
});
