// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('Payment Entry', {
	refresh: function(frm) {
		// Check if eBarimt is enabled
		if (!frappe.boot.ebarimt || !frappe.boot.ebarimt.enabled) {
			return;
		}
		
		// Check if linked to eBarimt invoice
		let has_ebarimt_invoice = check_ebarimt_invoices(frm);
		
		if (has_ebarimt_invoice) {
			frm.dashboard.add_indicator(__('eBarimt Invoice'), 'blue');
			
			// Show payment code if set
			if (frm.doc.custom_ebarimt_payment_code) {
				frm.dashboard.add_indicator(
					__('Payment Code: {0}', [frm.doc.custom_ebarimt_payment_code]), 
					'green'
				);
			}
		}
	},
	
	mode_of_payment: function(frm) {
		// Auto-set payment code from Mode of Payment mapping
		if (frm.doc.mode_of_payment && !frm.doc.custom_ebarimt_payment_code) {
			frappe.call({
				method: 'ebarimt.integrations.mode_of_payment.get_ebarimt_payment_code',
				args: {
					mode_of_payment: frm.doc.mode_of_payment
				},
				callback: function(r) {
					if (r.message) {
						// Get payment type name from code
						frappe.db.get_value('eBarimt Payment Type', 
							{payment_code: r.message}, 
							'name',
							function(data) {
								if (data && data.name) {
									frm.set_value('custom_ebarimt_payment_code', data.name);
								}
							}
						);
					}
				}
			});
		}
	}
});

function check_ebarimt_invoices(frm) {
	let has_ebarimt = false;
	
	if (frm.doc.references && frm.doc.references.length > 0) {
		for (let ref of frm.doc.references) {
			if (ref.reference_doctype === 'Sales Invoice' || ref.reference_doctype === 'POS Invoice') {
				// Check if invoice has eBarimt receipt
				frappe.db.get_value(ref.reference_doctype, ref.reference_name, 
					'custom_ebarimt_receipt_id',
					function(data) {
						if (data && data.custom_ebarimt_receipt_id) {
							has_ebarimt = true;
						}
					}
				);
			}
		}
	}
	
	return has_ebarimt;
}
