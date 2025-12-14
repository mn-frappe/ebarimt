// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('Item', {
	refresh: function(frm) {
		// Check if eBarimt is enabled
		if (!frappe.boot.ebarimt || !frappe.boot.ebarimt.enabled) {
			return;
		}
		
		// Add lookup button
		frm.add_custom_button(__('Lookup Barcode'), function() {
			lookup_barcode(frm);
		}, __('eBarimt'));
		
		// Show sync status
		if (frm.doc.custom_barcode_synced) {
			frm.dashboard.add_indicator(__('Barcode Synced'), 'green');
		} else if (frm.doc.custom_ebarimt_barcode) {
			frm.dashboard.add_indicator(__('Barcode Not Synced'), 'orange');
		}
	},
	
	custom_ebarimt_barcode: function(frm) {
		// Auto-lookup when barcode is entered
		if (frm.doc.custom_ebarimt_barcode && frm.doc.custom_ebarimt_barcode.length >= 8) {
			lookup_barcode(frm, false);
		}
	}
});

function lookup_barcode(frm, show_dialog = true) {
	let barcode = frm.doc.custom_ebarimt_barcode;
	
	// Try to get barcode from barcodes table
	if (!barcode && frm.doc.barcodes && frm.doc.barcodes.length > 0) {
		barcode = frm.doc.barcodes[0].barcode;
	}
	
	if (!barcode) {
		if (show_dialog) {
			// Show dialog to enter barcode
			let d = new frappe.ui.Dialog({
				title: __('Lookup Barcode'),
				fields: [
					{
						fieldtype: 'Data',
						fieldname: 'barcode',
						label: __('Barcode'),
						description: __('Enter BUNA, EAN, or UPC barcode')
					}
				],
				primary_action_label: __('Lookup'),
				primary_action: function(values) {
					if (!values.barcode) {
						frappe.msgprint(__('Please enter a barcode'));
						return;
					}
					
					d.hide();
					do_barcode_lookup(frm, values.barcode);
				}
			});
			d.show();
		}
		return;
	}
	
	do_barcode_lookup(frm, barcode);
}

function do_barcode_lookup(frm, barcode) {
	frappe.call({
		method: 'ebarimt.integrations.item.lookup_barcode',
		args: {
			barcode: barcode
		},
		freeze: true,
		freeze_message: __('Looking up barcode...'),
		callback: function(r) {
			if (r.message && r.message.success) {
				let data = r.message;
				
				// Update form fields
				frm.set_value('custom_ebarimt_barcode', data.barcode || barcode);
				frm.set_value('custom_ebarimt_product_name', data.name);
				frm.set_value('custom_ebarimt_manufacturer', data.manufacturer);
				frm.set_value('custom_barcode_synced', 1);
				
				if (data.tax_product_code) {
					frm.set_value('custom_ebarimt_tax_code', data.tax_product_code);
				}
				
				frappe.show_alert({
					message: __('Barcode found: {0}', [data.name]),
					indicator: 'green'
				});
			} else {
				frappe.msgprint({
					message: r.message.message || __('Barcode not found in eBarimt database'),
					indicator: 'orange',
					title: __('Not Found')
				});
				
				// Still set the barcode
				frm.set_value('custom_ebarimt_barcode', barcode);
			}
		}
	});
}
