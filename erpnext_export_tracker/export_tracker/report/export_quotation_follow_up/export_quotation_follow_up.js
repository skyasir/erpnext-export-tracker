frappe.query_reports["Export Quotation Follow-up"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
		  default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Data" },
		{ fieldname: "overdue_only", label: __("Follow-up Overdue Only"), fieldtype: "Check" },
		{ fieldname: "include_closed", label: __("Include Ordered / Lost / Expired"),
		  fieldtype: "Check" },
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "days_idle" && data && data.days_idle > 14) {
			value = `<span style="color: var(--red-500)">${value}</span>`;
		}
		return value;
	},
};
