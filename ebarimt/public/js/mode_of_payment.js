// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('Mode of Payment', {
	refresh: function(frm) {
		// Check if eBarimt is enabled
		if (!frappe.boot.ebarimt || !frappe.boot.ebarimt.enabled) {
			return;
		}
		
		// Show mapping status
		if (frm.doc.custom_ebarimt_payment_type) {
			frm.dashboard.add_indicator(
				__('eBarimt Mapped: {0}', [frm.doc.custom_ebarimt_payment_type]), 
				'green'
			);
		} else {
			frm.dashboard.add_indicator(__('Not Mapped to eBarimt'), 'orange');
		}
		
		// Add mapping button
		if (!frm.doc.custom_ebarimt_payment_type) {
			frm.add_custom_button(__('Map to eBarimt'), function() {
				show_mapping_dialog(frm);
			}, __('eBarimt'));
		}
	},
	
	custom_ebarimt_payment_type: function(frm) {
		// Show confirmation when mapping changes
		if (frm.doc.custom_ebarimt_payment_type) {
			frappe.show_alert({
				message: __('Mapped to eBarimt Payment Type: {0}', 
					[frm.doc.custom_ebarimt_payment_type]),
				indicator: 'green'
			}, 5);
		}
	}
});

function show_mapping_dialog(frm) {
	// Get available payment types
	frappe.call({
		method: 'ebarimt.integrations.payment_entry.get_ebarimt_payment_types',
		callback: function(r) {
			if (r.message && r.message.length > 0) {
				let options = r.message.map(pt => ({
					label: `${pt.payment_code} - ${pt.payment_name}`,
					value: pt.name
				}));
				
				let d = new frappe.ui.Dialog({
					title: __('Map to eBarimt Payment Type'),
					fields: [
						{
							fieldtype: 'Select',
							fieldname: 'payment_type',
							label: __('eBarimt Payment Type'),
							options: options,
							reqd: 1
						},
						{
							fieldtype: 'HTML',
							options: '<div class="text-muted small">' +
								'<b>P</b> - Cash (Бэлэн)<br>' +
								'<b>T</b> - Bank Transfer (Шилжүүлэг)<br>' +
								'<b>C</b> - Card (Карт)<br>' +
								'<b>O</b> - Other (Бусад)' +
								'</div>'
						}
					],
					primary_action_label: __('Map'),
					primary_action: function(values) {
						frm.set_value('custom_ebarimt_payment_type', values.payment_type);
						d.hide();
					}
				});
				d.show();
			} else {
				frappe.msgprint(__('No eBarimt Payment Types configured. Please set up payment types first.'));
			}
		}
	});
}

// Add list view indicator
frappe.listview_settings['Mode of Payment'] = frappe.listview_settings['Mode of Payment'] || {};

frappe.listview_settings['Mode of Payment'].add_fields = ['custom_ebarimt_payment_type'];

frappe.listview_settings['Mode of Payment'].get_indicator = function(doc) {
	if (frappe.boot.ebarimt && frappe.boot.ebarimt.enabled) {
		if (doc.custom_ebarimt_payment_type) {
			return [__('eBarimt Mapped'), 'green', 'custom_ebarimt_payment_type,is,set'];
		}
	}
	return null;
};
