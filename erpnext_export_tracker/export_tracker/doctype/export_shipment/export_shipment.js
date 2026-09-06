// The export desk works one shipment at a time through thirteen states. The
// panel at the top of the form is the whole point of this file: it says where
// the shipment is, what the next button is called, and exactly what is still
// missing -- so nobody has to press an action to find out why it is refused.

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
			frm.add_custom_button(__("Download Document Pack"), () => document_pack(frm), __("Documents"));

			frm.add_custom_button(__("Compare Freight Quotes"), () => compare_quotes(frm), __("Freight"));
			frm.add_custom_button(__("Add Weekly Update"), () => production_update(frm), __("Production"));
		}

		set_indicators(frm);
		refresh_panels(frm);
	},

	onload_post_render(frm) {
		render_country_note(frm);
	},

	payment_route(frm) {
		frm.set_df_property(
			"management_signed",
			"reqd",
			frm.doc.payment_route !== "Direct through Client"
		);
	},

	destination_country(frm) {
		render_country_note(frm);
	},
});

// ---------------------------------------------------------------------------
// guidance panel
// ---------------------------------------------------------------------------
// One round trip feeds both the next-step panel and the closure checklist --
// they answer the same question and the shipment is a big document to post.
function refresh_panels(frm) {
	const guidance = frm.get_field("next_step_html");

	if (frm.is_new()) {
		if (guidance) {
			guidance.$wrapper.html(
				blank_state(__("Save the shipment to see what the export desk owes next."))
			);
		}
		return;
	}

	frm.call({ doc: frm.doc, method: "get_next_step" }).then((r) => {
		const d = r && r.message;
		if (!d) return;
		paint(frm, guidance, guidance_html(d));
		paint(frm, frm.get_field("closure_checklist_html"), closure_html(frm, d));
	});
}

function paint(frm, field, html) {
	if (!field) return;
	field.$wrapper.html(html);
	field.$wrapper.find("[data-goto]").on("click", function () {
		frm.scroll_to_field($(this).attr("data-goto"));
	});
}

function guidance_html(d) {
	const pct = Math.round((d.current_index / (d.total_stages - 1)) * 100);
	const steps = d.stages
		.map((s) => {
			const cls = s.current ? "current" : s.done ? "done" : "todo";
			return `<span class="et-step et-${cls}" title="${frappe.utils.escape_html(s.state)}"></span>`;
		})
		.join("");

	let body = "";
	if (!d.next_state) {
		body = `<div class="et-done-msg">${__("Every stage is complete. This shipment is closed.")}</div>`;
	} else {
		const heading = d.next_action
			? __("Next: {0} &rarr; {1}", [
					`<b>${frappe.utils.escape_html(d.next_action)}</b>`,
					frappe.utils.escape_html(d.next_state),
			  ])
			: __("Next: {0}", [frappe.utils.escape_html(d.next_state)]);

		const blockers = d.blockers.length
			? `<div class="et-group">
					<div class="et-group-title et-red">${__("Blocking ({0})", [d.blockers.length])}</div>
					${d.blockers.map((b) => item(b, "et-red")).join("")}
			   </div>`
			: `<div class="et-group"><div class="et-group-title et-green">${__(
					"Nothing blocking &mdash; you can run this action now."
			  )}</div></div>`;

		const todos = d.todos.length
			? `<div class="et-group">
					<div class="et-group-title et-amber">${__("Recommended ({0})", [d.todos.length])}</div>
					${d.todos.map((t) => item(t, "et-amber")).join("")}
			   </div>`
			: "";

		body = `<div class="et-next">${heading}</div>${blockers}${todos}`;
	}

	const note = d.country_note
		? `<div class="et-note">${frappe.utils.escape_html(d.country_note)}</div>`
		: "";

	return `${STYLE}
		<div class="et-panel">
			<div class="et-head">
				<div class="et-stage">${frappe.utils.escape_html(d.current_state)}</div>
				<div class="et-count">${__("Stage {0} of {1}", [d.current_index + 1, d.total_stages])} &middot; ${pct}%</div>
			</div>
			<div class="et-steps">${steps}</div>
			${note}
			${body}
		</div>`;
}

function item(req, colour) {
	const hint = req.hint ? `<span class="et-hint">${frappe.utils.escape_html(req.hint)}</span>` : "";
	const label = frappe.utils.escape_html(req.label);
	const goto = req.fieldname
		? `<a class="et-goto" data-goto="${frappe.utils.escape_html(req.fieldname)}">${__("go")}</a>`
		: "";
	return `<div class="et-item"><span class="et-dot ${colour}"></span><span class="et-label">${label}${hint}</span>${goto}</div>`;
}

function blank_state(msg) {
	return `${STYLE}<div class="et-panel"><div class="et-blank">${msg}</div></div>`;
}

// ---------------------------------------------------------------------------
// closure checklist -- SOP section 37
// ---------------------------------------------------------------------------
function closure_html(frm, d) {
	const currency = frm.doc.currency === "INR" ? "INR" : __("foreign currency");
	const rows = d.closure.map((c) => item(c, c.ok ? "et-green" : "et-red")).join("");
	return `${STYLE}<div class="et-panel">
			<div class="et-group-title">${__("Mandatory to close a {0} shipment", [currency])}</div>
			${rows}
		</div>`;
}

function render_country_note(frm) {
	const field = frm.get_field("country_requirement_html");
	if (!field) return;
	if (!frm.doc.country_profile) {
		field.$wrapper.html(
			`${STYLE}<div class="et-blank">${__(
				"No country profile for this destination. Add one under Export Country Profile to drive its checklist and compliance flags."
			)}</div>`
		);
		return;
	}
	frappe.db.get_doc("Export Country Profile", frm.doc.country_profile).then((p) => {
		const bits = [];
		if (p.special_requirement) bits.push(frappe.utils.escape_html(p.special_requirement));
		if (p.inspection_required)
			bits.push(__("Inspection: {0}", [frappe.utils.escape_html(p.inspection_agency || "TBD")]));
		if (p.form_m_required) bits.push(__("Form M and BA needed before dispatch."));
		if (p.haulage_required) bits.push(__("Inland haulage after the discharge port."));
		field.$wrapper.html(`${STYLE}<div class="et-note">${bits.join("<br>")}</div>`);
	});
}

// ---------------------------------------------------------------------------
// freight comparison -- SOP section 13
// ---------------------------------------------------------------------------
function compare_quotes(frm) {
	const quotes = frm.doc.cha_quotes || [];
	if (!quotes.length) {
		frappe.msgprint(__("Add the forwarder quotes first, then compare them here."));
		return;
	}

	const money = (v, c) => format_currency(flt(v), c || frm.doc.currency);
	const cheapest = Math.min(...quotes.map((q) => flt(q.total_amount) || Infinity));
	const fastest = Math.min(...quotes.map((q) => cint(q.transit_days) || Infinity));

	const rows = quotes
		.map((q) => {
			const best = flt(q.total_amount) === cheapest ? ' <span class="et-tag">cheapest</span>' : "";
			const quick = cint(q.transit_days) === fastest ? ' <span class="et-tag">fastest</span>' : "";
			return `<tr>
				<td><b>${frappe.utils.escape_html(q.cha || "-")}</b>${best}${quick}</td>
				<td class="text-right">${money(q.freight_amount, q.currency)}</td>
				<td class="text-right">${money(flt(q.local_charges) + flt(q.thc), q.currency)}</td>
				<td class="text-right">${money(flt(q.documentation_charges) + flt(q.haulage_charges) + flt(q.other_charges), q.currency)}</td>
				<td class="text-right"><b>${money(q.total_amount, q.currency)}</b></td>
				<td class="text-right">${cint(q.transit_days) || "-"}</td>
				<td class="text-right">${cint(q.free_days) || "-"}</td>
				<td>${q.etd ? frappe.datetime.str_to_user(q.etd) : "-"}</td>
				<td><button class="btn btn-xs btn-default et-pick" data-row="${q.name}">${
					q.is_selected ? __("Selected") : __("Select")
				}</button></td>
			</tr>`;
		})
		.join("");

	const dialog = new frappe.ui.Dialog({
		title: __("Freight Comparison"),
		size: "extra-large",
		fields: [{ fieldtype: "HTML", fieldname: "grid" }],
	});

	dialog.fields_dict.grid.$wrapper.html(`${STYLE}
		<table class="table table-bordered et-compare">
			<thead><tr>
				<th>${__("Forwarder")}</th>
				<th class="text-right">${__("Freight")}</th>
				<th class="text-right">${__("Local + THC")}</th>
				<th class="text-right">${__("Doc + Haulage + Other")}</th>
				<th class="text-right">${__("Landed Total")}</th>
				<th class="text-right">${__("Transit")}</th>
				<th class="text-right">${__("Free Days")}</th>
				<th>${__("ETD")}</th>
				<th></th>
			</tr></thead>
			<tbody>${rows}</tbody>
		</table>`);

	dialog.$wrapper.find(".et-pick").on("click", function () {
		const picked = $(this).attr("data-row");
		(frm.doc.cha_quotes || []).forEach((r) => {
			frappe.model.set_value(r.doctype, r.name, "is_selected", r.name === picked ? 1 : 0);
		});
		dialog.hide();
		frm.refresh_field("cha_quotes");
		frappe.show_alert({ message: __("Forwarder selected. Save to finalise freight."), indicator: "green" });
	});

	dialog.show();
}

// ---------------------------------------------------------------------------
// weekly production update -- SOP section 12
// ---------------------------------------------------------------------------
function production_update(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Weekly Production Update"),
		fields: [
			{ fieldtype: "Date", fieldname: "week_ending", label: __("Week Ending"), reqd: 1,
			  default: frappe.datetime.get_today() },
			{ fieldtype: "Select", fieldname: "production_status", label: __("Production Status"), reqd: 1,
			  options: ["Not Started", "In Production", "Partially Ready", "Ready", "Dispatch Planning"],
			  default: frm.doc.production_status || "In Production" },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Select", fieldname: "packing_status", label: __("Packing Status"),
			  options: ["", "Not Started", "In Progress", "Completed"], default: frm.doc.packing_status },
			{ fieldtype: "Date", fieldname: "expected_completion_date", label: __("Expected Completion"),
			  default: frm.doc.expected_completion_date },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Float", fieldname: "qty_completed", label: __("Qty Completed"),
			  default: frm.doc.qty_completed },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Float", fieldname: "qty_pending", label: __("Qty Pending"),
			  default: frm.doc.qty_pending },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Small Text", fieldname: "remarks", label: __("Remarks") },
		],
		primary_action_label: __("Add Update"),
		primary_action(values) {
			frm.add_child("production_updates", values);
			frm.refresh_field("production_updates");
			dialog.hide();
			frm.save().then(() =>
				frappe.show_alert({ message: __("Production update recorded."), indicator: "green" })
			);
		},
	});
	dialog.show();
}

// ---------------------------------------------------------------------------
// document pack -- SOP section 33
// ---------------------------------------------------------------------------
function document_pack(frm) {
	frm.call({
		doc: frm.doc,
		method: "build_document_pack",
		freeze: true,
		freeze_message: __("Packing the shipment documents..."),
	}).then((r) => {
		if (!r || !r.message) return;
		const { file_url, packed, skipped } = r.message;
		frappe.show_alert(
			{ message: __("{0} document(s) packed.", [packed]), indicator: "green" },
			7
		);
		if (skipped && skipped.length) {
			frappe.msgprint({
				title: __("Some files could not be read"),
				message: skipped.map((s) => "&bull; " + frappe.utils.escape_html(s)).join("<br>"),
				indicator: "orange",
			});
		}
		window.open(file_url, "_blank");
	});
}

// ---------------------------------------------------------------------------
// checklist + child table behaviour
// ---------------------------------------------------------------------------
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
});

["freight_amount", "local_charges", "thc", "documentation_charges", "haulage_charges", "other_charges"].forEach(
	(fieldname) => {
		frappe.ui.form.on("Export CHA Quote", {
			[fieldname]: (frm, cdt, cdn) => recalc_quote(cdt, cdn),
		});
	}
);

function recalc_quote(cdt, cdn) {
	const row = locals[cdt][cdn];
	const total = ["freight_amount", "local_charges", "thc", "documentation_charges",
		"haulage_charges", "other_charges"].reduce((sum, f) => sum + flt(row[f]), 0);
	frappe.model.set_value(cdt, cdn, "total_amount", total);
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
	for (const [label, value] of [
		[__("SI cut-off"), frm.doc.si_cutoff],
		[__("VGM cut-off"), frm.doc.vgm_cutoff],
		[__("Doc cut-off"), frm.doc.doc_cutoff],
	]) {
		if (!value || frm.doc.stage_index >= 6) continue;
		const days = frappe.datetime.get_day_diff(value.split(" ")[0], frappe.datetime.get_today());
		if (days >= 0 && days <= 3) {
			frm.dashboard.add_indicator(
				__("{0} in {1} day(s)", [label, days]),
				days <= 1 ? "red" : "orange"
			);
		}
	}
}

// Desk colour variables, so the panel follows the user's theme.
const STYLE = `<style>
.et-panel { border: 1px solid var(--border-color); border-radius: var(--border-radius-md, 6px);
	padding: 12px 14px; background: var(--fg-color, #fff); }
.et-head { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.et-stage { font-size: var(--text-lg, 15px); font-weight: 600; color: var(--text-color); }
.et-count { font-size: var(--text-sm, 12px); color: var(--text-muted); white-space: nowrap; }
.et-steps { display: flex; gap: 3px; margin: 10px 0 12px; }
.et-step { flex: 1; height: 5px; border-radius: 3px; background: var(--gray-200, #e2e2e2); }
.et-done { background: var(--green-400, #48bb74); }
.et-current { background: var(--blue-500, #2490ef); }
.et-next { font-size: var(--text-md, 13px); margin-bottom: 8px; color: var(--text-color); }
.et-group { margin-top: 8px; }
.et-group-title { font-size: var(--text-sm, 12px); font-weight: 600; text-transform: uppercase;
	letter-spacing: .4px; color: var(--text-muted); margin-bottom: 4px; }
.et-item { display: flex; align-items: baseline; gap: 8px; padding: 3px 0;
	font-size: var(--text-md, 13px); color: var(--text-color); }
.et-dot { width: 7px; height: 7px; border-radius: 50%; flex: 0 0 7px; }
.et-label { flex: 1; }
.et-hint { display: block; font-size: var(--text-sm, 12px); color: var(--text-muted); }
.et-goto { font-size: var(--text-sm, 12px); cursor: pointer; color: var(--text-muted);
	text-decoration: underline; }
.et-red { background: var(--red-500, #e24c4c); color: var(--red-600, #c53030); }
.et-amber { background: var(--orange-500, #ed8936); color: var(--orange-600, #dd6b20); }
.et-green { background: var(--green-500, #38a169); color: var(--green-600, #2f855a); }
.et-group-title.et-red, .et-group-title.et-amber, .et-group-title.et-green { background: none; }
.et-note { font-size: var(--text-sm, 12px); color: var(--text-color);
	background: var(--bg-blue, #f0f7ff); border-radius: 4px; padding: 6px 9px; margin-bottom: 8px; }
.et-blank, .et-done-msg { font-size: var(--text-md, 13px); color: var(--text-muted); }
.et-tag { font-size: 10px; text-transform: uppercase; letter-spacing: .4px;
	background: var(--bg-green, #e8f5e9); color: var(--green-600, #2f855a);
	border-radius: 3px; padding: 1px 5px; margin-left: 4px; }
.et-compare th { font-size: var(--text-sm, 12px); color: var(--text-muted); font-weight: 600; }
</style>`;
