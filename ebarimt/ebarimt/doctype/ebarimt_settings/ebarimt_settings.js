// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('eBarimt Settings', {
	refresh: function(frm) {
		// Add test connection button
		frm.add_custom_button(__('Test Connection'), function() {
			frm.call({
				method: 'test_connection',
				doc: frm.doc,
				freeze: true,
				freeze_message: __('Testing connection...'),
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __('Connection Successful'),
							indicator: 'green',
							message: __('Connected to eBarimt!<br><br>' +
								'Operator: {0}<br>' +
								'POS No: {1}<br>' +
								'Lotteries: {2}<br>' +
								'Merchants: {3}',
								[r.message.data.operator,
								 r.message.data.pos_no,
								 r.message.data.lotteries,
								 r.message.data.merchants])
						});
						frm.reload_doc();
					} else {
						frappe.msgprint({
							title: __('Connection Failed'),
							indicator: 'red',
							message: r.message ? r.message.message : __('Unknown error')
						});
					}
				}
			});
		}, __('Actions'));
		
		// Add sync fixtures button
		frm.add_custom_button(__('Sync Fixtures'), function() {
			frm.call({
				method: 'sync_fixtures',
				doc: frm.doc,
				freeze: true,
				freeze_message: __('Syncing districts and tax codes...'),
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __('Sync Complete'),
							indicator: 'green',
							message: r.message.message
						});
					} else {
						frappe.msgprint({
							title: __('Sync Failed'),
							indicator: 'red',
							message: r.message ? r.message.message : __('Unknown error')
						});
					}
				}
			});
		}, __('Actions'));
		
		// Show status indicator
		if (frm.doc.connection_status === 'Connected') {
			frm.dashboard.set_headline_alert(
				`<div class="alert alert-success">
					<span class="indicator-pill green"></span>
					${__('Connected')} - ${frm.doc.operator_name || ''} 
					(${frm.doc.left_lotteries || 0} ${__('lotteries remaining')})
				</div>`
			);
		} else if (frm.doc.connection_status === 'Disconnected') {
			frm.dashboard.set_headline_alert(
				`<div class="alert alert-danger">
					<span class="indicator-pill red"></span>
					${__('Disconnected')} - ${__('Please check credentials and test connection')}
				</div>`
			);
		}
		
		// Environment warning
		if (frm.doc.environment === 'Staging') {
			frm.set_intro(__('You are using the STAGING environment. Switch to Production for live transactions.'), 'orange');
		}
	},
	
	environment: function(frm) {
		// Clear connection status when environment changes
		frm.set_value('connection_status', '');
		frm.set_value('operator_name', '');
		frm.set_value('operator_tin', '');
		frm.set_value('left_lotteries', 0);
	}
});
