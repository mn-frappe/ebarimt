// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('Company', {
	refresh: function(frm) {
		// Check if eBarimt is enabled globally
		if (!frappe.boot.ebarimt || !frappe.boot.ebarimt.enabled) {
			return;
		}
		
		// Show eBarimt status indicator
		if (frm.doc.custom_ebarimt_enabled) {
			frm.dashboard.add_indicator(__('eBarimt Enabled'), 'green');
			
			// Add verification button
			frm.add_custom_button(__('Verify Registration'), function() {
				verify_ebarimt_registration(frm);
			}, __('eBarimt'));
			
			// Add sync button
			frm.add_custom_button(__('Sync Taxpayer Info'), function() {
				sync_company_taxpayer(frm);
			}, __('eBarimt'));
		} else {
			frm.dashboard.add_indicator(__('eBarimt Disabled'), 'gray');
		}
	},
	
	custom_ebarimt_enabled: function(frm) {
		// Toggle field visibility
		frm.toggle_reqd('custom_operator_tin', frm.doc.custom_ebarimt_enabled);
	},
	
	custom_operator_tin: function(frm) {
		// Validate TIN format
		if (frm.doc.custom_operator_tin) {
			let tin = frm.doc.custom_operator_tin.trim();
			if (!/^\d{7,12}$/.test(tin)) {
				frappe.msgprint(__('Invalid TIN format. TIN should be 7-12 digits.'));
			}
		}
	}
});

function verify_ebarimt_registration(frm) {
	frappe.call({
		method: 'ebarimt.integrations.company.verify_company_registration',
		args: {
			company: frm.doc.name
		},
		freeze: true,
		freeze_message: __('Verifying eBarimt registration...'),
		callback: function(r) {
			if (r.message) {
				if (r.message.success && r.message.registered) {
					let info = r.message.pos_info;
					frappe.msgprint({
						title: __('Registration Verified'),
						indicator: 'green',
						message: __('POS is registered and active.<br><br>' +
							'<b>POS No:</b> {0}<br>' +
							'<b>Merchant TIN:</b> {1}<br>' +
							'<b>Status:</b> {2}',
							[info.pos_no, info.merchant_tin, info.status || 'Active']
						)
					});
				} else if (r.message.success && !r.message.registered) {
					frappe.msgprint({
						title: __('Registration Issue'),
						indicator: 'orange',
						message: r.message.message || __('POS not registered or inactive')
					});
				} else {
					frappe.msgprint({
						title: __('Verification Failed'),
						indicator: 'red',
						message: r.message.message || __('Could not verify registration')
					});
				}
			}
		}
	});
}

function sync_company_taxpayer(frm) {
	frappe.call({
		method: 'ebarimt.integrations.company.sync_company_taxpayer_info',
		args: {
			company: frm.doc.name
		},
		freeze: true,
		freeze_message: __('Syncing taxpayer information...'),
		callback: function(r) {
			if (r.message) {
				if (r.message.success) {
					let data = r.message.data;
					frappe.msgprint({
						title: __('Taxpayer Info'),
						indicator: 'green',
						message: __('<b>TIN:</b> {0}<br>' +
							'<b>Name:</b> {1}<br>' +
							'<b>VAT Payer:</b> {2}<br>' +
							'<b>City Tax Payer:</b> {3}',
							[data.tin, data.name, 
							 data.vat_payer ? __('Yes') : __('No'),
							 data.city_payer ? __('Yes') : __('No')]
						)
					});
				} else {
					frappe.msgprint({
						title: __('Sync Failed'),
						indicator: 'red',
						message: r.message.message
					});
				}
			}
		}
	});
}
