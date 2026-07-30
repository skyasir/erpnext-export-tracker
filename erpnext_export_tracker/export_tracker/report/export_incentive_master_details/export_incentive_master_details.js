frappe.query_reports["Export Incentive Master Details"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
		  default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "from_date", label: __("Shipping Bill From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("Shipping Bill To"), fieldtype: "Date" },
		{ fieldname: "incentive_status", label: __("Incentive Status"), fieldtype: "Select",
		  options: ["", "Not Started", "Details Sent", "Scrip Received"].join("\n") },
		{ fieldname: "include_unclosed", label: __("Include shipments without EBRC"),
		  fieldtype: "Check" },
	],
};
