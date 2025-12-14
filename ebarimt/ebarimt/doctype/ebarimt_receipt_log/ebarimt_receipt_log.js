// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('eBarimt Receipt Log', {
	refresh: function(frm) {
		// Add void button for successful B2C receipts
		if (frm.doc.status === 'Success' && frm.doc.bill_type === 'B2C_RECEIPT') {
			frm.add_custom_button(__('Void Receipt'), function() {
				frappe.confirm(
					__('Are you sure you want to void this receipt? This action cannot be undone.'),
					function() {
						frm.call({
							method: 'void_receipt',
							doc: frm.doc,
							freeze: true,
							freeze_message: __('Voiding receipt...'),
							callback: function(r) {
								if (r.message && r.message.success) {
									frappe.msgprint(__('Receipt voided successfully'));
									frm.reload_doc();
								}
							}
						});
					}
				);
			}, __('Actions')).addClass('btn-danger');
		}
		
		// Show QR code if available
		if (frm.doc.qr_data) {
			frm.add_custom_button(__('Show QR Code'), function() {
				// Generate QR code display
				let qr_html = `
					<div style="text-align: center; padding: 20px;">
						<div id="qr-code"></div>
						<p style="margin-top: 10px; font-size: 12px; word-break: break-all;">
							${frm.doc.lottery_number || frm.doc.receipt_id}
						</p>
					</div>
				`;
				
				let d = new frappe.ui.Dialog({
					title: __('eBarimt QR Code'),
					fields: [{
						fieldtype: 'HTML',
						fieldname: 'qr_display',
						options: qr_html
					}]
				});
				
				d.show();
				
				// Generate QR using frappe's QR library if available
				if (typeof QRCode !== 'undefined') {
					new QRCode(d.$wrapper.find('#qr-code')[0], {
						text: frm.doc.qr_data,
						width: 200,
						height: 200
					});
				}
			});
		}
		
		// Status indicator
		if (frm.doc.status === 'Success') {
			frm.dashboard.set_headline_alert(
				`<div class="alert alert-success">
					${__('Receipt sent successfully')}
					${frm.doc.lottery_number ? ' - ' + __('Lottery') + ': ' + frm.doc.lottery_number : ''}
				</div>`
			);
		} else if (frm.doc.status === 'Failed') {
			frm.dashboard.set_headline_alert(
				`<div class="alert alert-danger">
					${__('Receipt failed')}: ${frm.doc.error_message || __('Unknown error')}
				</div>`
			);
		} else if (frm.doc.status === 'Voided') {
			frm.dashboard.set_headline_alert(
				`<div class="alert alert-warning">
					${__('This receipt has been voided')}
				</div>`
			);
		}
		
		// Link to invoice
		if (frm.doc.sales_invoice) {
			frm.add_custom_button(__('View Invoice'), function() {
				frappe.set_route('Form', 'Sales Invoice', frm.doc.sales_invoice);
			});
		}
	}
});
