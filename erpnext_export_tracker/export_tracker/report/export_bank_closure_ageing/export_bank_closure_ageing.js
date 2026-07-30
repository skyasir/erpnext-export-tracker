frappe.query_reports["Export Bank Closure Ageing"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
		  default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
		{ fieldname: "stage", label: __("Closure Stage"), fieldtype: "Select",
		  options: ["", "Awaiting Final Payment", "Pending XAR", "Pending Bank Submission",
			"Pending EBRC (DGFT)", "Closed - EBRC Generated"].join("\n") },
		{ fieldname: "include_closed", label: __("Include Closed"), fieldtype: "Check" },
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "days_left" && data && data.days_left !== null) {
			const colour = data.days_left < 0 ? "red" : data.days_left <= 30 ? "orange" : "green";
			value = `<span style="color: var(--${colour}-500); font-weight: 600">${value}</span>`;
		}
		return value;
	},
};
