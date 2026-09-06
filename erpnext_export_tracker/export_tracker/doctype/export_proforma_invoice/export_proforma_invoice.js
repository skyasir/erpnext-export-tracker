// The proforma is the earlier document: it becomes the order, not the other way
// round. Everything the export desk agreed with the buyer is captured here once.

frappe.ui.form.on("Export Proforma Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.sales_order) {
			frm.add_custom_button(__("Sales Order"), () => make_sales_order(frm), __("Create"));
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}
		if (frm.doc.sales_order) {
			frm.add_custom_button(__("Sales Order"), () =>
				frappe.set_route("Form", "Sales Order", frm.doc.sales_order), __("View"));
		}
	},

	buyer_same_as_consignee(frm) {
		if (frm.doc.buyer_same_as_consignee) {
			frm.set_value("buyer_name", frm.doc.consignee_name);
			frm.set_value("buyer_address", frm.doc.consignee_address);
		}
	},

	destination_country(frm) {
		if (!frm.doc.country_of_final_destination && frm.doc.destination_country) {
			frm.set_value("country_of_final_destination",
				frm.doc.destination_country.toUpperCase());
		}
	},
});

frappe.ui.form.on("Export Indent Item", {
	qty: (frm, cdt, cdn) => amount(frm, cdt, cdn),
	rate: (frm, cdt, cdn) => amount(frm, cdt, cdn),
});

function amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
}

function make_sales_order(frm) {
	frappe.model.open_mapped_doc({
		method: "erpnext_export_tracker.export_tracker.doctype.export_proforma_invoice"
			+ ".export_proforma_invoice.make_sales_order",
		frm: frm,
		freeze_message: __("Raising the sales order..."),
	});
}
