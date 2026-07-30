frappe.query_reports["Export Outstanding Payment Statement"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
		  default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
		{ fieldname: "from_date", label: __("Invoice From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("Invoice To"), fieldtype: "Date" },
		{ fieldname: "include_paid", label: __("Include Fully Paid"), fieldtype: "Check" },
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "age" && data && data.age > 90) {
			value = `<span style="color: var(--red-500); font-weight: 600">${value}</span>`;
		}
		return value;
	},
};
