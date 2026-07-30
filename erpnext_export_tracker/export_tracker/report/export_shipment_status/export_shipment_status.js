frappe.query_reports["Export Shipment Status"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
		  default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "from_date", label: __("ETD From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("ETD To"), fieldtype: "Date" },
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select",
		  options: ["", "Order Confirmed", "Indent Approved", "Freight Finalised",
			"Dispatch Planned", "Customs Docs Prepared", "Container Loaded", "Shipped",
			"Post-Shipment Docs Prepared", "Docs Submitted", "Payment Received",
			"XAR Generated", "Bank Submission Done", "EBRC Generated"].join("\n") },
		{ fieldname: "payment_route", label: __("Route"), fieldtype: "Select",
		  options: ["", "Direct through Client", "Through Bank",
			"Through Letter of Credit"].join("\n") },
		{ fieldname: "payment_status", label: __("Payment Status"), fieldtype: "Select",
		  options: ["", "Unpaid", "Partly Paid", "Fully Paid"].join("\n") },
		{ fieldname: "destination_country", label: __("Destination"), fieldtype: "Link",
		  options: "Country" },
		{ fieldname: "hide_closed", label: __("Hide Closed (EBRC done)"), fieldtype: "Check",
		  default: 1 },
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data) {
			const colour = data.ebrc_no ? "green" : data.shipping_bill_no ? "blue" : "orange";
			value = `<span style="color: var(--text-on-light-${colour}, inherit)">${value}</span>`;
		}
		if (column.fieldname === "outstanding_amount" && data && data.outstanding_amount > 0) {
			value = `<span style="color: var(--red-500)">${value}</span>`;
		}
		return value;
	},
};
