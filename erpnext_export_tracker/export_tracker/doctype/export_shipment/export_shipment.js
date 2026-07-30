frappe.ui.form.on("Export Shipment", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Load Document Checklist"), () => load_checklist(frm), __("Documents"));
			frm.add_custom_button(__("Reload from Template (overwrite)"), () => {
				frappe.confirm(
					__("This clears both document tables and reloads them from the template. Continue?"),
					() => load_checklist(frm, true)
				);
			}, __("Documents"));
		}

		set_indicators(frm);
	},

	payment_route(frm) {
		frm.set_df_property(
			"management_signed",
			"reqd",
			frm.doc.payment_route !== "Direct through Client"
		);
	},
});

frappe.ui.form.on("Export CHA Quote", {
	is_selected(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.is_selected) return;
		// only one quote may win
		(frm.doc.cha_quotes || []).forEach((r) => {
			if (r.name !== row.name && r.is_selected) {
				frappe.model.set_value(r.doctype, r.name, "is_selected", 0);
			}
		});
	},

	freight_amount(frm, cdt, cdn) {
		recalc_quote(cdt, cdn);
	},

	other_charges(frm, cdt, cdn) {
		recalc_quote(cdt, cdn);
	},
});

function recalc_quote(cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(
		cdt,
		cdn,
		"total_amount",
		flt(row.freight_amount) + flt(row.other_charges)
	);
}

function load_checklist(frm, overwrite) {
	frm.call({
		doc: frm.doc,
		method: "load_document_checklist",
		args: { overwrite: overwrite ? 1 : 0 },
		freeze: true,
		freeze_message: __("Loading document checklist..."),
	}).then((r) => {
		if (!r || !r.message) return;
		frm.refresh_field("pre_shipment_documents");
		frm.refresh_field("post_shipment_documents");
		frappe.show_alert({
			message: __("{0} document(s) added from template {1}", [
				r.message.added,
				r.message.template,
			]),
			indicator: r.message.added ? "green" : "orange",
		});
	});
}

function set_indicators(frm) {
	if (frm.is_new()) return;

	const pending = (table) =>
		(frm.doc[table] || []).filter((r) => r.is_required && !r.prepared).length;

	const pre = pending("pre_shipment_documents");
	const post = pending("post_shipment_documents");

	if (pre) {
		frm.dashboard.add_indicator(__("Pre-Shipment docs pending: {0}", [pre]), "orange");
	}
	if (post) {
		frm.dashboard.add_indicator(__("Post-Shipment docs pending: {0}", [post]), "orange");
	}
	if (frm.doc.payment_status) {
		frm.dashboard.add_indicator(
			__("Payment: {0}", [__(frm.doc.payment_status)]),
			frm.doc.payment_status === "Fully Paid" ? "green" : "red"
		);
	}
	if (frm.doc.ebrc_no) {
		frm.dashboard.add_indicator(__("EBRC {0}", [frm.doc.ebrc_no]), "green");
	}
}
