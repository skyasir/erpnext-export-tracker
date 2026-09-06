// A proforma behaves exactly like a Sales Order because it is one, minus the
// commitment: extending erpnext's SellingController gives item fetching, price
// lists, pricing rules, tax templates and live totals without reimplementing any
// of it. Export is a flag on the document, not its purpose.

frappe.provide("erpnext.selling");

frappe.ui.form.on("Proforma Invoice", {
	setup(frm) {
		frm.custom_make_buttons = { "Sales Order": "Sales Order" };
	},

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

function make_sales_order(frm) {
	frappe.model.open_mapped_doc({
		method: "erpnext_export_tracker.export_tracker.doctype.proforma_invoice"
			+ ".proforma_invoice.make_sales_order",
		frm: frm,
		freeze_message: __("Raising the sales order..."),
	});
}

// ERPNext's calculation engine, borrowed rather than reimplemented: item
// fetching, price lists, pricing rules, tax templates, discounts and live
// totals all come from it.
//
// `erpnext.selling.SellingController` is only defined on pages ERPNext loads its
// selling bundle for, which a custom doctype is not -- `erpnext.TransactionController`
// is the base that is always there. Preferring the richer one when it happens to
// be loaded, and falling back, means the form works either way; and if neither
// exists the document still saves, because the same calculations run server-side
// in the Python controller.
(function attach_controller() {
	const Base =
		(window.erpnext && erpnext.selling && erpnext.selling.SellingController) ||
		(window.erpnext && erpnext.TransactionController);

	if (!Base) return;

	erpnext.selling = erpnext.selling || {};
	erpnext.selling.ProformaInvoiceController = class ProformaInvoiceController extends Base {
		company() {
			super.company && super.company();
		}
	};

	if (typeof cur_frm !== "undefined" && cur_frm && typeof extend_cscript === "function") {
		extend_cscript(cur_frm.cscript, new erpnext.selling.ProformaInvoiceController({ frm: cur_frm }));
	}
})();
