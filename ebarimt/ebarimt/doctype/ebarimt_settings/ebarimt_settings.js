// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on('eBarimt Settings', {
	refresh: function(frm) {
		// Render connection status HTML
		render_connection_status(frm);
		
		// Toggle integration sections based on installed apps
		toggle_integration_sections(frm);
		
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


/**
 * Show/hide integration sections based on installed apps
 */
function toggle_integration_sections(frm) {
	// Check for installed apps via boot flags
	const apps = {
		healthcare: frappe.boot.has_healthcare || false,
		education: frappe.boot.has_education || false,
		lending: frappe.boot.has_lending || false
	};
	
	// Healthcare section fields
	const healthcare_fields = [
		'section_healthcare',
		'enable_healthcare_integration',
		'auto_receipt_patient_encounter',
		'column_break_healthcare',
		'auto_receipt_patient_invoice'
	];
	
	// Education section fields
	const education_fields = [
		'section_education',
		'enable_education_integration',
		'auto_receipt_fee_collection',
		'column_break_education',
		'auto_receipt_fee_schedule'
	];
	
	// Lending section fields
	const lending_fields = [
		'section_lending',
		'enable_lending_integration',
		'auto_receipt_loan_repayment',
		'column_break_lending',
		'auto_receipt_loan_disbursement'
	];
	
	// Toggle visibility
	healthcare_fields.forEach(f => frm.toggle_display(f, apps.healthcare));
	education_fields.forEach(f => frm.toggle_display(f, apps.education));
	lending_fields.forEach(f => frm.toggle_display(f, apps.lending));
}
