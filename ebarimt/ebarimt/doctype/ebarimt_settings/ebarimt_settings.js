// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('eBarimt Settings', {
	refresh: function(frm) {
		// Render connection status HTML
		render_connection_status(frm);
		
		// Environment warning
		if (frm.doc.environment === 'Staging') {
			frm.set_intro(__('You are using the STAGING environment. Switch to Production for live transactions.'), 'orange');
		}
	},
	
	test_connection_btn: function(frm) {
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
	},
	
	detect_district_btn: function(frm) {
		frm.call({
			method: 'detect_district',
			doc: frm.doc,
			freeze: true,
			freeze_message: __('Detecting location...'),
			callback: function(r) {
				if (r.message && r.message.success) {
					frappe.msgprint({
						title: __('Location Detected'),
						indicator: 'green',
						message: r.message.message
					});
					frm.reload_doc();
				} else {
					frappe.msgprint({
						title: __('Detection Failed'),
						indicator: 'red',
						message: r.message ? r.message.message : __('Could not detect location')
					});
				}
			}
		});
	},
	
	environment: function(frm) {
		// Clear connection status when environment changes
		frm.set_value('connection_status', '');
		frm.set_value('operator_name', '');
		frm.set_value('operator_tin', '');
		frm.set_value('left_lotteries', 0);
	}
});


function render_connection_status(frm) {
	let html = '';
	
	if (frm.doc.connection_status === 'Connected') {
		html = `
			<div class="alert alert-success d-flex align-items-center" style="margin: 0; padding: 10px 15px;">
				<span class="indicator-pill green" style="margin-right: 10px;"></span>
				<div>
					<strong>${__('Connected')}</strong><br>
					<small class="text-muted">
						${frm.doc.operator_name || ''} 
						${frm.doc.left_lotteries ? '• ' + frm.doc.left_lotteries + ' ' + __('lotteries') : ''}
					</small>
				</div>
			</div>
		`;
	} else if (frm.doc.connection_status === 'Disconnected') {
		html = `
			<div class="alert alert-danger d-flex align-items-center" style="margin: 0; padding: 10px 15px;">
				<span class="indicator-pill red" style="margin-right: 10px;"></span>
				<div>
					<strong>${__('Disconnected')}</strong><br>
					<small>${__('Check credentials and test connection')}</small>
				</div>
			</div>
		`;
	} else {
		html = `
			<div class="alert alert-warning d-flex align-items-center" style="margin: 0; padding: 10px 15px;">
				<span class="indicator-pill yellow" style="margin-right: 10px;"></span>
				<div>
					<strong>${__('Not Configured')}</strong><br>
					<small>${__('Enter credentials and test connection')}</small>
				</div>
			</div>
		`;
	}
	
	frm.fields_dict.connection_status_html.$wrapper.html(html);
}
