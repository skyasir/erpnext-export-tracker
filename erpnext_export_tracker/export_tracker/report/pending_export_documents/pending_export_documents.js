frappe.query_reports["Pending Export Documents"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
		  default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "shipment", label: __("Shipment"), fieldtype: "Link",
		  options: "Export Shipment" },
		{ fieldname: "stage", label: __("Stage"), fieldtype: "Select",
		  options: ["", "Pre-Shipment", "Post-Shipment"].join("\n") },
		{ fieldname: "responsibility", label: __("Responsibility"), fieldtype: "Select",
		  options: ["", "Export Dept", "CHA", "Accounts", "Consultant", "Bank", "Customer",
			"Insurer"].join("\n") },
		{ fieldname: "only_required", label: __("Only Required Documents"), fieldtype: "Check",
		  default: 1 },
		{ fieldname: "include_closed", label: __("Include Closed Shipments"),
		  fieldtype: "Check" },
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "days_to_etd" && data && data.days_to_etd !== null) {
			const colour = data.days_to_etd < 0 ? "red" : data.days_to_etd <= 7 ? "orange" : "green";
			value = `<span style="color: var(--${colour}-500)">${value}</span>`;
		}
		return value;
	},
};
