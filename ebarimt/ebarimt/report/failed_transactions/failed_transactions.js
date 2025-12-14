// Copyright (c) 2024, Orchlon and contributors
// For license information, please see license.txt

frappe.query_reports["Failed Transactions"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -7),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "error_type",
			label: __("Error Contains"),
			fieldtype: "Data",
		},
	],

	onload: function (report) {
		report.page.add_inner_button(__("Retry All Failed"), function () {
			frappe.confirm(
				__("This will attempt to retry all failed transactions. Continue?"),
				function () {
					frappe.call({
						method: "ebarimt.ebarimt.api.api.retry_all_failed",
						callback: function (r) {
							if (r.message) {
								frappe.msgprint(
									__("Retry initiated for {0} transactions", [r.message])
								);
								report.refresh();
							}
						},
					});
				}
			);
		});
	},
};
