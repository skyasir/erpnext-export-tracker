// Quotation -> Proforma Invoice -> Sales Order. The order is raised from the
// proforma, not from the quotation, so the proforma is the step that carries
// the export block and the agreed figures.

frappe.ui.form.on("Quotation", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.status === "Lost") return;
		// a proforma may be addressed to a Lead or Prospect as well as a
		// Customer, the same three a Quotation accepts; the party converts
		// later, when the Sales Order is raised

		frm.add_custom_button(__("Proforma Invoice"), () => {
			frappe.model.open_mapped_doc({
				method: "erpnext_export_tracker.export_tracker.doctype.proforma_invoice"
					+ ".proforma_invoice.make_proforma_invoice",
				frm: frm,
				freeze_message: __("Raising the proforma invoice..."),
			});
		}, __("Create"));
	},
});
