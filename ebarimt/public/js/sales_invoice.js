// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('Sales Invoice', {
	refresh: function(frm) {
		// Check if eBarimt is enabled
		if (!frappe.boot.ebarimt || !frappe.boot.ebarimt.enabled) {
			return;
		}
		
		// Show eBarimt status
		if (frm.doc.docstatus === 1) {
			if (frm.doc.custom_ebarimt_receipt_id) {
				// Receipt exists - show success indicator
				frm.dashboard.add_indicator(
					__('eBarimt: ✓ {0}', [frm.doc.custom_ebarimt_lottery || frm.doc.custom_ebarimt_receipt_id]),
					'green'
				);
				
				// Add QR code button
				if (frm.doc.custom_ebarimt_qr_data) {
					frm.add_custom_button(__('Show QR'), function() {
						show_ebarimt_qr(frm.doc);
					}, __('eBarimt'));
				}
				
				// Add void button
				frm.add_custom_button(__('Void Receipt'), function() {
					void_ebarimt_receipt(frm);
				}, __('eBarimt'));
			} else {
				// No receipt - allow manual submission
				frm.dashboard.add_indicator(__('eBarimt: Not Sent'), 'orange');
				
				frm.add_custom_button(__('Send to eBarimt'), function() {
					submit_to_ebarimt(frm);
				}, __('eBarimt'));
			}
		}
		
		// For drafts, show bill type selector
		if (frm.doc.docstatus === 0) {
			// Auto-set bill type based on customer
			if (frm.doc.customer && !frm.doc.custom_ebarimt_bill_type) {
				frappe.db.get_value('Customer', frm.doc.customer, 'custom_tin', (r) => {
					if (r && r.custom_tin) {
						frm.set_value('custom_ebarimt_bill_type', 'B2B_RECEIPT');
					} else {
						frm.set_value('custom_ebarimt_bill_type', 'B2C_RECEIPT');
					}
				});
			}
		}
	},
	
	customer: function(frm) {
		// Auto-set bill type when customer changes
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

function submit_to_ebarimt(frm) {
	frappe.confirm(
		__('Submit this invoice to eBarimt?'),
		function() {
			frappe.call({
				method: 'ebarimt.integrations.sales_invoice.manual_submit_receipt',
				args: {
					invoice_name: frm.doc.name
				},
				freeze: true,
				freeze_message: __('Submitting to eBarimt...'),
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __('eBarimt receipt submitted successfully'),
							indicator: 'green'
						});
						frm.reload_doc();
					}
				}
			});
		}
	);
}

function void_ebarimt_receipt(frm) {
	frappe.confirm(
		__('Are you sure you want to void this eBarimt receipt? This action cannot be undone.'),
		function() {
			frappe.call({
				method: 'ebarimt.integrations.sales_invoice.void_invoice_receipt',
				args: {
					invoice_name: frm.doc.name
				},
				freeze: true,
				freeze_message: __('Voiding receipt...'),
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __('Receipt voided successfully'),
							indicator: 'green'
						});
						frm.reload_doc();
					}
				}
			});
		}
	);
}

function show_ebarimt_qr(doc) {
	let qr_html = `
		<div style="text-align: center; padding: 20px;">
			<div id="ebarimt-qr-code" style="margin: 0 auto;"></div>
			<p style="margin-top: 15px; font-weight: bold; font-size: 16px;">
				${doc.custom_ebarimt_lottery || ''}
			</p>
			<p style="margin-top: 5px; color: #666; font-size: 12px;">
				${__('Receipt ID')}: ${doc.custom_ebarimt_receipt_id}
			</p>
		</div>
	`;
	
	let d = new frappe.ui.Dialog({
		title: __('eBarimt QR Code'),
		fields: [{
			fieldtype: 'HTML',
			fieldname: 'qr_display',
			options: qr_html
		}],
		primary_action_label: __('Print'),
		primary_action: function() {
			let print_content = d.$wrapper.find('#ebarimt-qr-code').parent().html();
			let win = window.open('', '', 'width=400,height=400');
			win.document.write('<html><head><title>eBarimt QR</title></head><body>');
			win.document.write(print_content);
			win.document.write('</body></html>');
			win.document.close();
			win.print();
		}
	});
	
	d.show();
	
	// Generate QR code
	setTimeout(function() {
		if (typeof QRCode !== 'undefined') {
			new QRCode(d.$wrapper.find('#ebarimt-qr-code')[0], {
				text: doc.custom_ebarimt_qr_data,
				width: 200,
				height: 200
			});
		}
	}, 100);
}
