frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || !frm.doc.custom_is_export) return;

		frm.add_custom_button(__("Export Shipment"), () => {
			const create = () =>
				frappe.call({
					method:
						"erpnext_export_tracker.export_tracker.doctype.export_shipment.export_shipment.make_export_shipment",
					args: { sales_order: frm.doc.name },
					freeze: true,
					callback(r) {
						if (r.message) frappe.set_route("Form", "Export Shipment", r.message);
					},
				});

			// an additional shipment means a part-shipment -- worth confirming
			frappe.call({
				method:
					"erpnext_export_tracker.export_tracker.doctype.export_shipment.export_shipment.count_shipments",
				args: { sales_order: frm.doc.name },
				callback(r) {
					if (r.message) {
						frappe.confirm(
							__(
								"This order already has {0} shipment(s). Create another one for a part-shipment?",
								[r.message]
							),
							create
						);
					} else {
						create();
					}
				},
			});
		}, __("Create"));

		frm.add_custom_button(__("Export Indent"), () => {
			frappe.call({
				method:
					"erpnext_export_tracker.export_tracker.doctype.export_indent.export_indent.make_export_indent",
				args: { sales_order: frm.doc.name },
				freeze: true,
				callback(r) {
					if (r.message) frappe.set_route("Form", "Export Indent", r.message);
				},
			});
		}, __("Create"));

		show_export_status(frm);
	},

	custom_is_export(frm) {
		if (!frm.doc.custom_is_export || frm.doc.custom_consignee_name) return;
		frm.set_value("custom_consignee_name", frm.doc.customer_name);
	},
});

function show_export_status(frm) {
	frappe.db
		.get_list("Export Shipment", {
			filters: { sales_order: frm.doc.name },
			fields: ["name", "status", "payment_status", "ebrc_no"],
			limit: 5,
		})
		.then((rows) => {
			(rows || []).forEach((row) => {
				const colour = row.ebrc_no ? "green" : row.status === "Shipped" ? "blue" : "orange";
				frm.dashboard.add_indicator(
					__("{0}: {1}", [row.name, __(row.status)]),
					colour
				);
			});
		});
}
