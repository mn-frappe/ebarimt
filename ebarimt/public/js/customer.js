// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('Customer', {
	refresh: function(frm) {
		// Check if eBarimt is enabled
		if (!frappe.boot.ebarimt || !frappe.boot.ebarimt.enabled) {
			return;
		}
		
		// Add lookup button
		frm.add_custom_button(__('Lookup Taxpayer'), function() {
			lookup_taxpayer(frm);
		}, __('eBarimt'));
		
		// Show sync status
		if (frm.doc.custom_taxpayer_synced) {
			frm.dashboard.add_indicator(__('Taxpayer Synced'), 'green');
		} else if (frm.doc.custom_tin) {
			frm.dashboard.add_indicator(__('Taxpayer Not Synced'), 'orange');
		}
	},
	
	custom_tin: function(frm) {
		// Auto-lookup when TIN is entered
		if (frm.doc.custom_tin && frm.doc.custom_tin.length >= 7) {
			lookup_taxpayer(frm, false);
		}
	}
});

function lookup_taxpayer(frm, show_dialog = true) {
	if (!frm.doc.custom_tin && !frm.doc.custom_regno) {
		if (show_dialog) {
			// Show dialog to enter TIN or Regno
			let d = new frappe.ui.Dialog({
				title: __('Lookup Taxpayer'),
				fields: [
					{
						fieldtype: 'Data',
						fieldname: 'tin',
						label: __('TIN (ТИН)'),
						description: __('Taxpayer Identification Number')
					},
					{
						fieldtype: 'Data',
						fieldname: 'regno',
						label: __('Registration No (РД)'),
						description: __('Company Registration Number')
					}
				],
				primary_action_label: __('Lookup'),
				primary_action: function(values) {
					if (!values.tin && !values.regno) {
						frappe.msgprint(__('Please enter TIN or Registration Number'));
						return;
					}
					
					d.hide();
					do_lookup(frm, values.tin, values.regno);
				}
			});
			d.show();
		}
		return;
	}
	
	do_lookup(frm, frm.doc.custom_tin, frm.doc.custom_regno);
}

function do_lookup(frm, tin, regno) {
	frappe.call({
		method: 'ebarimt.integrations.customer.lookup_taxpayer',
		args: {
			tin: tin,
			regno: regno
		},
		freeze: true,
		freeze_message: __('Looking up taxpayer...'),
		callback: function(r) {
			if (r.message && r.message.success) {
				let data = r.message;
				
				// Update form fields
				frm.set_value('custom_tin', data.tin);
				frm.set_value('custom_taxpayer_name', data.name);
				frm.set_value('custom_vat_payer', data.vat_payer ? 1 : 0);
				frm.set_value('custom_city_payer', data.city_payer ? 1 : 0);
				frm.set_value('custom_taxpayer_synced', 1);
				
				if (data.regno) {
					frm.set_value('custom_regno', data.regno);
				}
				
				// Update customer name if empty
				if (!frm.doc.customer_name || frm.doc.customer_name === 'New Customer') {
					frm.set_value('customer_name', data.name);
				}
				
				frappe.show_alert({
					message: __('Taxpayer found: {0}', [data.name]),
					indicator: 'green'
				});
			} else {
				frappe.msgprint({
					message: r.message.message || __('Taxpayer not found'),
					indicator: 'red'
				});
			}
		}
	});
}
