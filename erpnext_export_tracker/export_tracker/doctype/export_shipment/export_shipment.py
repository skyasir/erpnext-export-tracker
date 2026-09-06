import io
import os
import zipfile

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, today

from erpnext_export_tracker.export_tracker.doctype.export_country_profile.export_country_profile import (
	get_profile,
)

# Order of the workflow states. Gates are expressed as "not before state X",
# so the index of the current status is what matters.
STATE_ORDER = [
	"Order Confirmed",
	"Indent Approved",
	"Freight Finalised",
	"Dispatch Planned",
	"Customs Docs Prepared",
	"Container Loaded",
	"Shipped",
	"Post-Shipment Docs Prepared",
	"Docs Submitted",
	"Payment Received",
	"XAR Generated",
	"Bank Submission Done",
	"EBRC Generated",
]

# The workflow action that moves you from one state to the next, so the guidance
# panel can name the button the user is about to press.
NEXT_ACTION = {
	"Order Confirmed": "Approve Indent",
	"Indent Approved": "Finalise Freight",
	"Freight Finalised": "Plan Dispatch",
	"Dispatch Planned": "Prepare Customs Docs",
	"Customs Docs Prepared": "Confirm Loading",
	"Container Loaded": "Mark Shipped",
	"Shipped": "Prepare Post-Shipment Docs",
	"Post-Shipment Docs Prepared": "Submit Documents",
	"Docs Submitted": "Confirm Payment Received",
	"Payment Received": "Generate XAR",
	"XAR Generated": "Complete Bank Submission",
	"Bank Submission Done": "Generate EBRC",
}

ROUTE_DIRECT = "Direct through Client"
ROUTE_BANK = "Through Bank"
ROUTE_LC = "Through Letter of Credit"


class ExportShipment(Document):
	def onload(self):
		"""Recompute the stage index when the form is opened.

		The guidance panel and the collapsed-section defaults key off stage_index,
		so a stored value that has drifted from status -- stale worker code, a
		direct db_set, a restored row -- would describe the wrong stage with no way
		out. This is display-only; validate() persists the correct value on the
		next save.
		"""
		current = self.state_index()
		if self.stage_index != current:
			self.stage_index = current

	def validate(self):
		self.set_defaults_from_order()
		self.apply_country_profile()
		self.set_defaults_from_settings()
		self.sync_cha_quotes()
		self.sync_containers()
		self.number_packages()
		self.roll_up_production()
		self.roll_up_xar()
		self.update_payment_status()
		self.stamp_management_signature()
		self.stamp_cha_checklist()
		self.validate_cha_details()
		self.stage_index = self.state_index()
		self.stamp_stage_dates()
		self.validate_state_requirements()

	# ------------------------------------------------------------------
	# defaults
	# ------------------------------------------------------------------
	def set_defaults_from_order(self):
		if not self.sales_order:
			return

		so = frappe.db.get_value(
			"Sales Order",
			self.sales_order,
			[
				"customer",
				"customer_name",
				"company",
				"currency",
				"incoterm",
				"grand_total",
			],
			as_dict=True,
		)
		if not so:
			return

		self.customer = self.customer or so.customer
		self.customer_name = self.customer_name or so.customer_name
		self.company = self.company or so.company
		self.currency = self.currency or so.currency
		self.incoterm = self.incoterm or so.incoterm

		if not self.company_currency and self.company:
			self.company_currency = frappe.db.get_value("Company", self.company, "default_currency")

		if not self.destination_country and self.customer:
			self.destination_country = get_customer_country(self.customer)

		if not self.consignee_name:
			self.consignee_name = so.customer_name

	def apply_country_profile(self):
		"""Pull the destination's compliance rules -- SOP section 2C.

		Only on a new shipment or when the destination actually changes. Turning
		a compliance flag on retroactively would make an in-flight shipment
		unsaveable against a gate its stage is already past, so a shipment that
		is already moving keeps whatever flags it was started with; a user can
		always tick them by hand.
		"""
		if not (self.is_new() or self.has_value_changed("destination_country")):
			self.country_profile = self.country_profile or profile_name(self.destination_country)
			return

		profile = get_profile(self.destination_country)
		self.country_profile = profile.name if profile else None
		if not profile:
			return

		self.inspection_required = cint(profile.inspection_required)
		self.form_m_required = cint(profile.form_m_required)
		self.haulage_required = cint(profile.haulage_required)

		if profile.inspection_agency and not self.inspection_agency:
			self.inspection_agency = profile.inspection_agency
		if profile.default_port_of_discharge and not self.port_of_discharge:
			self.port_of_discharge = profile.default_port_of_discharge
		if profile.coo_type and not self.coo_no:
			self.coo_type = profile.coo_type

	def set_defaults_from_settings(self):
		settings = get_settings()
		if not settings:
			return

		self.pre_carriage_by = self.pre_carriage_by or settings.default_pre_carriage_by
		self.place_of_receipt = self.place_of_receipt or settings.default_place_of_receipt
		self.port_of_loading = self.port_of_loading or settings.default_port_of_loading
		self.country_of_origin = self.country_of_origin or settings.default_country_of_origin
		self.incentive_consultant = self.incentive_consultant or settings.incentive_consultant

		if self.insurance_required and not self.insurance_company:
			self.insurance_company = settings.default_insurance_company

		if not self.country_of_final_destination and self.destination_country:
			self.country_of_final_destination = self.destination_country.upper()

	# ------------------------------------------------------------------
	# freight comparison -- SOP section 13
	# ------------------------------------------------------------------
	def sync_cha_quotes(self):
		"""Total up each quote and mirror the selected one onto the parent."""
		selected = []
		for row in self.cha_quotes:
			row.total_amount = quote_total(row)
			if not row.currency:
				row.currency = self.freight_currency or self.currency
			if row.is_selected:
				selected.append(row)

		if len(selected) > 1:
			frappe.throw(
				_("Only one CHA quote can be marked as Selected. Rows {0} are all selected.").format(
					", ".join(str(r.idx) for r in selected)
				)
			)

		if selected:
			row = selected[0]
			self.selected_cha = row.cha
			self.selected_freight_amount = row.total_amount
			self.freight_currency = row.currency or self.freight_currency
			self.selected_transit_days = row.transit_days
			self.selected_free_days = row.free_days
			self.eta = self.eta or row.eta
			if row.vessel and not self.vessel_flight_no:
				self.vessel_flight_no = row.vessel
		else:
			self.selected_cha = None
			self.selected_freight_amount = 0
			self.selected_transit_days = 0
			self.selected_free_days = 0

	# ------------------------------------------------------------------
	# containers and packing -- one source of truth for four documents
	# ------------------------------------------------------------------
	def sync_containers(self):
		"""The containers table is authoritative once it has rows; the older
		single container_no field and the weight totals become derived from it,
		so the invoice print and the loading gate keep working unchanged."""
		if not self.containers:
			return

		self.container_no = "\n".join(c.container_no for c in self.containers if c.container_no)
		self.no_of_containers = len(self.containers)
		self.net_weight = sum(flt(c.net_weight) for c in self.containers)
		self.gross_weight = sum(flt(c.gross_weight) for c in self.containers)
		self.no_of_packages = sum(int(c.no_of_packages or 0) for c in self.containers)

		known = {c.container_no for c in self.containers if c.container_no}
		for row in self.packing_items:
			if row.container_no and row.container_no not in known:
				frappe.throw(
					_("Packing row {0} names container {1}, which is not in the Containers "
					  "table.").format(row.idx, row.container_no)
				)

	def number_packages(self):
		"""Package numbers run consecutively across the whole packing list, in
		row order -- 1 TO 4, then 5 TO 129, and so on."""
		counter = 0
		for row in self.packing_items:
			row.total_qty = flt(row.qty_per_bundle) * (row.no_of_packages or 0)
			row.total_weight = flt(row.weight_per_package) * (row.no_of_packages or 0)
			count = int(row.no_of_packages or 0)
			if count > 0:
				row.package_from = counter + 1
				row.package_to = counter + count
				counter += count
			else:
				row.package_from = None
				row.package_to = None

	# ------------------------------------------------------------------
	# production readiness -- SOP section 12
	# ------------------------------------------------------------------
	def roll_up_production(self):
		"""The newest weekly update is the shipment's production status, so the
		dashboard and the readiness report never have to read the child table."""
		if not self.production_updates:
			return

		for row in self.production_updates:
			if not row.updated_by:
				row.updated_by = frappe.session.user

		latest = max(self.production_updates, key=lambda r: (getdate(r.week_ending), r.idx))
		self.production_status = latest.production_status
		self.qty_completed = latest.qty_completed
		self.qty_pending = latest.qty_pending
		self.packing_status = latest.packing_status
		self.expected_completion_date = latest.expected_completion_date
		self.last_production_update = latest.week_ending

	def roll_up_xar(self):
		"""The payments table owns the XAR numbers; the shipment keeps the first
		one as a read-only summary.

		An invoice settled in parts carries an XAR per receipt, so there is no
		single shipment XAR any more. Keeping the earliest on the parent is what
		lets the XAR Generated workflow state, its gate and the Bank Closure
		Ageing report go on working, including for shipments that predate the
		table and still hold their own value.
		"""
		dated = [r for r in self.payments if r.xar_no]
		if not dated:
			return

		first = min(dated, key=lambda r: (getdate(r.xar_date) if r.xar_date else getdate(today()), r.idx))
		self.xar_no = first.xar_no
		self.xar_date = first.xar_date

	@frappe.whitelist()
	def fetch_payments(self):
		"""Pull every submitted receipt booked against this shipment's order or
		invoice into the payments table -- SOP section 12's Fetch Payments.

		Rows already listed are left alone, so pressing it twice adds nothing and
		never overwrites an XAR somebody has typed. The row currency defaults to
		the shipment's, because that is the currency the proceeds are realised in
		and what decides whether an XAR is owed -- the payment entry itself is
		often booked against an INR debtors account even for a dollar invoice.
		"""
		targets = [t for t in (self.sales_order, self.sales_invoice) if t]
		if not targets:
			frappe.throw(_("Link a Sales Order or an Export Invoice first."))

		rows = frappe.db.sql(
			"""
			select pe.name as payment_entry, pe.posting_date, pe.reference_no,
			       ref.reference_doctype, ref.reference_name, ref.allocated_amount
			from `tabPayment Entry` pe
			inner join `tabPayment Entry Reference` ref on ref.parent = pe.name
			where pe.docstatus = 1
			  and pe.payment_type = 'Receive'
			  and ref.reference_doctype in ('Sales Order', 'Sales Invoice')
			  and ref.reference_name in %(targets)s
			order by pe.posting_date, pe.name
			""",
			{"targets": targets},
			as_dict=True,
		)

		known = {r.payment_entry for r in self.payments if r.payment_entry}
		added = 0
		for row in rows:
			if row.payment_entry in known:
				continue
			self.append(
				"payments",
				{
					"payment_entry": row.payment_entry,
					"payment_date": row.posting_date,
					"amount": row.allocated_amount,
					"currency": self.currency,
					"bank_reference": row.reference_no,
					"payment_type": "Advance"
					if row.reference_doctype == "Sales Order"
					else "Against Invoice",
					"sales_invoice": row.reference_name
					if row.reference_doctype == "Sales Invoice"
					else None,
				},
			)
			known.add(row.payment_entry)
			added += 1

		return {"added": added, "found": len(rows)}

	# ------------------------------------------------------------------
	# payment -- drives the bank closure gate
	# ------------------------------------------------------------------
	def update_payment_status(self):
		if self.sales_invoice:
			si = frappe.db.get_value(
				"Sales Invoice",
				self.sales_invoice,
				["grand_total", "outstanding_amount", "currency", "docstatus"],
				as_dict=True,
			)
			if si and si.docstatus == 1:
				self.invoice_amount = si.grand_total
				self.outstanding_amount = si.outstanding_amount
				self.total_received = flt(si.grand_total) - flt(si.outstanding_amount)
				self.currency = si.currency or self.currency
		elif self.sales_order:
			so = frappe.db.get_value(
				"Sales Order", self.sales_order, ["grand_total", "advance_paid"], as_dict=True
			)
			if so:
				self.invoice_amount = so.grand_total
				self.total_received = flt(so.advance_paid)
				self.outstanding_amount = flt(so.grand_total) - flt(so.advance_paid)

		received = flt(self.total_received)
		invoiced = flt(self.invoice_amount)

		if invoiced and received >= invoiced - 0.01:
			self.payment_status = "Fully Paid"
			if not self.final_payment_date:
				self.final_payment_date = today()
		elif received > 0:
			self.payment_status = "Partly Paid"
			self.final_payment_date = None
		else:
			self.payment_status = "Unpaid"
			self.final_payment_date = None

	def stamp_management_signature(self):
		if self.management_signed and not self.management_signed_by:
			self.management_signed_by = frappe.session.user
			self.management_signed_on = today()
		elif not self.management_signed:
			self.management_signed_by = None
			self.management_signed_on = None

	def validate_cha_details(self):
		"""Nothing goes to the CHA until we know which CHA -- SOP section 1.

		The trigger is the act of forwarding, not a workflow stage: the moment a
		sent-on date or a checklist status past "Not Sent" is recorded, the CHA
		and the broker who will file must already be named.
		"""
		forwarded = bool(self.cha_docs_sent_on) or self.cha_checklist_status not in (
			None, "", "Not Sent",
		)
		if not forwarded:
			return

		missing = [
			label
			for label, value in (
				(_("Selected CHA"), self.selected_cha),
				(_("Customs Broker / Courier"), self.customs_broker_name),
			)
			if not value
		]
		if missing:
			frappe.throw(
				_("Enter the CHA details before forwarding documents to the CHA. "
				  "Missing: {0}").format(", ".join(missing)),
				title=_("CHA details required"),
			)

	def stamp_cha_checklist(self):
		"""Who approved the CHA checklist, and when -- SOP section 24."""
		if self.cha_checklist_status == "Approved":
			if not self.cha_checklist_approved_by:
				self.cha_checklist_approved_by = frappe.session.user
				self.cha_checklist_approved_on = today()
		else:
			self.cha_checklist_approved_by = None
			self.cha_checklist_approved_on = None

	def stamp_stage_dates(self):
		"""Dates that simply record "when did we do this" default to today the
		first time the shipment reaches that stage. Still editable afterwards."""
		if self.reached("Docs Submitted") and not self.docs_submitted_on:
			self.docs_submitted_on = today()

		if self.reached("Bank Submission Done") and not self.bank_submission_date:
			self.bank_submission_date = today()

	# ------------------------------------------------------------------
	# gates
	# ------------------------------------------------------------------
	def state_index(self):
		try:
			return STATE_ORDER.index(self.status)
		except ValueError:
			return 0

	def reached(self, state):
		return self.state_index() >= STATE_ORDER.index(state)

	def requirements_for(self, state):
		"""What this shipment still owes before it may sit in `state`.

		One list feeds both the gate in validate() and the "what's next" panel on
		the form, so the panel can never promise something the gate will refuse.

		blocking=False marks an item the SOP asks for but which is not worth
		refusing a save over -- it shows up as a to-do on the form and in the
		pending reports instead.
		"""
		R = requirement
		out = []

		if state == "Indent Approved":
			approved = (
				frappe.db.get_value("Export Indent", self.export_indent, "management_approved")
				if self.export_indent
				else 1
			)
			out.append(
				R(_("Export Indent approved by management"), approved, "export_indent")
			)

		elif state == "Freight Finalised":
			out.append(
				R(
					_("One CHA / forwarder quote marked as Selected"),
					self.selected_cha,
					"cha_quotes",
					hint=_("Compare the quotes on landed cost, transit time and free days."),
				)
			)
			out.append(
				R(
					_("Route, transshipment and additional charges verified"),
					self.route_verified,
					"route_verified",
					blocking=False,
				)
			)

		elif state == "Dispatch Planned":
			out.append(R(_("Dispatch Planned On"), self.dispatch_plan_date, "dispatch_plan_date"))
			if self.form_m_required:
				out.append(R(_("Form M No"), self.form_m_no, "form_m_no"))
				out.append(R(_("BA No"), self.ba_no, "ba_no"))

		elif state == "Customs Docs Prepared":
			out.append(R(_("Shipment Type (FCL / LCL)"), self.shipment_type, "shipment_type"))
			out += self.document_requirements("Pre-Shipment")
			if self.inspection_required:
				out.append(
					R(
						_("Inspection closed out"),
						self.inspection_status == "Final Report" or self.inspection_report_no,
						"inspection_status",
						hint=_("Agency: {0}. Untick 'Pre-Shipment Inspection Required' if this "
						       "destination no longer needs one.").format(
							self.inspection_agency or _("not set")
						),
					)
				)

		elif state == "Container Loaded":
			out += [
				R(_("Container Loaded On"), self.loading_date, "loading_date"),
				R(_("Container No(s)"), self.container_no, "containers"),
				R(_("Customs Seal No"), self.customs_seal_no, "customs_seal_no"),
				R(_("Shipping Line Seal No"), self.shipping_line_seal_no, "shipping_line_seal_no"),
			]

		elif state == "Shipped":
			out += [
				R(_("Shipping Bill No"), self.shipping_bill_no, "shipping_bill_no"),
				R(_("Shipping Bill Date"), self.shipping_bill_date, "shipping_bill_date"),
				R(_("ETD"), self.etd, "etd"),
			]
			if self.payment_route == ROUTE_LC:
				out.append(
					R(
						_("LC received from the customer"),
						self.lc_received_on,
						"lc_received_on",
						hint=_("Under a Letter of Credit the LC must be in hand before shipment."),
					)
				)
			out.append(
				R(
					_("CHA checklist approved"),
					self.cha_checklist_status == "Approved",
					"cha_checklist_status",
					blocking=False,
				)
			)
			if self.shipment_type == "FCL":
				out.append(R(_("E-Seal / RFID No"), self.e_seal_no, "e_seal_no", blocking=False))
			out.append(R(_("E-Way Bill No"), self.eway_bill_no, "eway_bill_no", blocking=False))

		elif state == "Post-Shipment Docs Prepared":
			out += self.document_requirements("Post-Shipment")
			out.append(R(_("BL / AWB No"), self.bl_no, "bl_no"))
			if self.coo_type and self.coo_type != "Not Applicable":
				out.append(
					R(
						_("COO No ({0})").format(self.coo_type),
						self.coo_no,
						"coo_no",
					)
				)
			if self.insurance_required:
				out.append(R(_("Insurance Policy No"), self.insurance_policy_no, "insurance_policy_no"))
			out.append(
				R(
					_("Client approved the draft BL"),
					self.bl_client_approved_on,
					"bl_client_approved_on",
					blocking=False,
				)
			)

		elif state == "Docs Submitted":
			out.append(
				R(
					_("Signed by Management"),
					self.management_signed,
					"management_signed",
					hint=_("Documents cannot leave the building unsigned."),
				)
			)
			if self.originals_required:
				out.append(
					R(
						_("Courier address confirmed with the client"),
						self.originals_address_confirmed,
						"originals_address_confirmed",
						blocking=False,
					)
				)

		elif state == "Payment Received":
			out.append(
				R(
					_("Full payment received"),
					self.payment_status == "Fully Paid",
					"outstanding_amount",
					hint=_("Outstanding on this shipment is {0}.").format(
						frappe.utils.fmt_money(self.outstanding_amount, currency=self.currency)
					),
				)
			)

		elif state == "XAR Generated":
			out += [
				R(_("XAR No"), self.xar_no, "xar_no"),
				R(_("XAR Date"), self.xar_date, "xar_date"),
			]

		elif state == "Bank Submission Done":
			out += [
				R(_("Shipping Bill No"), self.shipping_bill_no, "shipping_bill_no"),
				R(_("Port Code"), self.port_code, "port_code"),
			]

		elif state == "EBRC Generated":
			out += [
				R(_("EBRC No"), self.ebrc_no, "ebrc_no"),
				R(_("EBRC Date"), self.ebrc_date, "ebrc_date"),
			]
			out += self.closure_requirements()

		return out

	def closure_requirements(self):
		"""SOP section 37 -- the closure pack differs by invoice currency."""
		R = requirement
		if (self.currency or "").upper() == "INR":
			return [
				R(_("Shipping Bill"), self.shipping_bill_no, "shipping_bill_no", blocking=False),
				R(_("Invoice"), self.sales_invoice, "sales_invoice", blocking=False),
				R(_("LR"), self.lr_no, "lr_no", blocking=False),
			]
		return [
			R(_("Invoice"), self.sales_invoice, "sales_invoice", blocking=False),
			R(_("Shipping Bill"), self.shipping_bill_no, "shipping_bill_no", blocking=False),
			R(_("Bill of Lading"), self.bl_no, "bl_no", blocking=False),
		]

	def document_requirements(self, stage):
		R = requirement
		table = (
			self.pre_shipment_documents if stage == "Pre-Shipment" else self.post_shipment_documents
		)
		if not table:
			return [
				R(
					_("{0} checklist loaded").format(_(stage)),
					False,
					"pre_shipment_documents"
					if stage == "Pre-Shipment"
					else "post_shipment_documents",
					hint=_("Use Documents > Load Document Checklist."),
				)
			]

		return [
			R(
				row.document_name,
				row.prepared,
				"pre_shipment_documents"
				if stage == "Pre-Shipment"
				else "post_shipment_documents",
				hint=_("Responsibility: {0}").format(row.responsibility or _("Export Dept")),
				blocking=bool(row.is_required),
			)
			for row in table
		]

	def validate_state_requirements(self):
		"""Every gate is enforced in validate() so it holds no matter how the
		status changed -- workflow action, API write or bulk edit."""
		for state in STATE_ORDER:
			if not self.reached(state):
				continue

			pending = [r for r in self.requirements_for(state) if r["blocking"] and not r["ok"]]
			if pending:
				frappe.throw(
					_("{0} is not complete. Still needed:<br>{1}").format(
						frappe.bold(state),
						"<br>".join("&bull; " + r["label"] for r in pending),
					),
					# the incomplete stage is not always the one being entered -- a
					# gap left behind earlier surfaces here too, so name the stage
					# rather than the move
					title=_("{0} is incomplete").format(state),
				)

		# comparisons rather than "is this filled in", so they stay separate
		if self.reached("Shipped") and self.payment_route == ROUTE_LC and self.lc_last_shipment_date:
			if self.etd and getdate(self.etd) > getdate(self.lc_last_shipment_date):
				frappe.throw(
					_("ETD {0} is after the LC's Last Date of Shipment {1}.").format(
						frappe.utils.formatdate(self.etd),
						frappe.utils.formatdate(self.lc_last_shipment_date),
					)
				)

	# ------------------------------------------------------------------
	# what the form shows the user
	# ------------------------------------------------------------------
	@frappe.whitelist()
	def get_next_step(self):
		"""Everything the guidance panel draws: where the shipment is, what the
		next workflow action is called, and exactly what is still missing."""
		index = self.state_index()
		next_state = STATE_ORDER[index + 1] if index + 1 < len(STATE_ORDER) else None

		pending = []
		if next_state:
			pending = [r for r in self.requirements_for(next_state) if not r["ok"]]

		# advice the desk skipped on the way here is still advice -- carry the
		# unmet non-blocking items of the current stage forward rather than
		# letting them disappear the moment the shipment moves on
		carried = [r for r in self.requirements_for(STATE_ORDER[index]) if not r["ok"]]
		seen = {r["label"] for r in pending}
		pending += [r for r in carried if not r["blocking"] and r["label"] not in seen]

		return {
			"stages": [
				{"state": state, "done": i < index, "current": i == index}
				for i, state in enumerate(STATE_ORDER)
			],
			"current_state": STATE_ORDER[index],
			"current_index": index,
			"total_stages": len(STATE_ORDER),
			"next_state": next_state,
			"next_action": NEXT_ACTION.get(STATE_ORDER[index]),
			"blockers": [r for r in pending if r["blocking"]],
			"todos": [r for r in pending if not r["blocking"]],
			"closure": self.closure_requirements(),
			"country_note": self.country_note(),
		}

	def country_note(self):
		"""The destination's rules in one sentence.

		The profile's own wording leads; a derived line is only added when the
		wording does not already cover it, so Malawi does not get told twice that
		it is landlocked.
		"""
		profile = get_profile(self.destination_country)
		if not profile:
			return None

		written = (profile.special_requirement or "").lower()
		bits = [profile.special_requirement] if profile.special_requirement else []

		if profile.inspection_required and (profile.inspection_agency or "").lower() not in written:
			bits.append(
				_("Inspection required ({0}).").format(profile.inspection_agency or _("agency TBD"))
			)
		if profile.form_m_required and "form m" not in written:
			bits.append(_("Form M and BA number required before dispatch."))
		if profile.haulage_required and "haulage" not in written:
			bits.append(_("Landlocked -- inland haulage after the discharge port."))

		return " ".join(bits) or None

	# ------------------------------------------------------------------
	# document checklist
	# ------------------------------------------------------------------
	@frappe.whitelist()
	def load_document_checklist(self, overwrite=False):
		"""Populate both checklists from the matching Export Document Template,
		plus anything the destination's country profile adds on top."""
		template_name = self.document_template or resolve_document_template(
			self.destination_country, self.payment_route
		)
		if not template_name:
			frappe.throw(
				_("No Export Document Template matches destination {0} and route {1}. "
				  "Create one, or set the template manually.").format(
					self.destination_country or _("(not set)"), self.payment_route
				)
			)

		self.document_template = template_name
		template = frappe.get_doc("Export Document Template", template_name)

		if overwrite in (True, 1, "1", "true"):
			self.pre_shipment_documents = []
			self.post_shipment_documents = []

		existing = {
			"Pre-Shipment": {r.document_name for r in self.pre_shipment_documents},
			"Post-Shipment": {r.document_name for r in self.post_shipment_documents},
		}

		rows = list(template.documents)
		profile = get_profile(self.destination_country)
		if profile:
			rows += list(profile.documents)

		added = 0
		for row in rows:
			stage = row.stage or "Pre-Shipment"
			if row.document_name in existing[stage]:
				continue
			target = (
				"pre_shipment_documents" if stage == "Pre-Shipment" else "post_shipment_documents"
			)
			self.append(
				target,
				{
					"document_name": row.document_name,
					"stage": stage,
					"is_required": row.is_required,
					"responsibility": row.responsibility,
					"remarks": row.remarks,
				},
			)
			existing[stage].add(row.document_name)
			added += 1

		return {"template": template_name, "added": added}

	# ------------------------------------------------------------------
	# shipment document pack -- SOP section 33
	# ------------------------------------------------------------------
	@frappe.whitelist()
	def build_document_pack(self):
		"""Zip up every file attached to this shipment -- both checklists and the
		shipment's own copies -- so the desk sends one file, not fourteen."""
		sources = []
		for table, folder in (
			("pre_shipment_documents", "1 Pre-Shipment"),
			("post_shipment_documents", "2 Post-Shipment"),
		):
			for row in self.get(table) or []:
				if row.attachment:
					sources.append((folder, row.document_name, row.attachment))

		for label, url in (
			("Shipping Bill", self.shipping_bill_attachment),
			("Examination Report", self.examination_report),
			("Bill of Lading", self.bl_attachment),
			("Certificate of Origin", self.coo_attachment),
			("E-Way Bill", self.eway_attachment),
			("E-Seal Confirmation", self.e_seal_attachment),
			("Inspection Report", self.inspection_report),
			("Form M", self.form_m_attachment),
			("BA", self.ba_attachment),
			("CHA Checklist", self.cha_checklist),
			("EBRC", self.ebrc_attachment),
		):
			if url:
				sources.append(("3 Shipment", label, url))

		if not sources:
			frappe.throw(
				_("Nothing to pack yet. Attach the prepared documents to the checklist rows first.")
			)

		buf = io.BytesIO()
		packed, skipped = 0, []
		with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
			seen = set()
			for folder, label, url in sources:
				content, ext = read_attachment(url)
				if content is None:
					skipped.append(label)
					continue
				name = f"{folder}/{safe_name(label)}{ext}"
				suffix = 2
				while name in seen:
					name = f"{folder}/{safe_name(label)} ({suffix}){ext}"
					suffix += 1
				seen.add(name)
				zf.writestr(name, content)
				packed += 1

		if not packed:
			frappe.throw(_("None of the attached files could be read."))

		pack = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{self.name}-document-pack.zip",
				"attached_to_doctype": self.doctype,
				"attached_to_name": self.name,
				"is_private": 1,
				"content": buf.getvalue(),
			}
		).insert(ignore_permissions=True)

		return {"file_url": pack.file_url, "packed": packed, "skipped": skipped}


# ----------------------------------------------------------------------
# module level helpers
# ----------------------------------------------------------------------
def requirement(label, ok, fieldname=None, hint=None, blocking=True):
	return {
		"label": label,
		"ok": bool(ok),
		"fieldname": fieldname,
		"hint": hint,
		"blocking": bool(blocking),
	}


def quote_total(row):
	"""Landed cost of one forwarder quote -- SOP section 13's comparison table."""
	return sum(
		flt(row.get(f))
		for f in (
			"freight_amount",
			"local_charges",
			"thc",
			"documentation_charges",
			"haulage_charges",
			"other_charges",
		)
	)


def safe_name(label):
	return "".join(c if (c.isalnum() or c in " -_") else "-" for c in label).strip() or "document"


def read_attachment(file_url):
	"""File content plus its extension, or (None, None) when the row points at a
	file that has since been deleted."""
	try:
		name = frappe.db.get_value("File", {"file_url": file_url}, "name")
		if not name:
			return None, None
		doc = frappe.get_doc("File", name)
		return doc.get_content(), os.path.splitext(doc.file_name or file_url)[1] or ""
	except Exception:
		frappe.log_error(title="Export document pack", message=frappe.get_traceback())
		return None, None


def profile_name(country):
	if not country:
		return None
	return frappe.db.get_value("Export Country Profile", {"country": country, "disabled": 0})


def get_settings():
	try:
		return frappe.get_cached_doc("Export Tracker Settings")
	except Exception:
		return None


def get_customer_country(customer):
	"""Country from the customer's primary address, falling back to the territory."""
	address = frappe.db.sql(
		"""
		select addr.country
		from `tabAddress` addr
		inner join `tabDynamic Link` dl on dl.parent = addr.name
		where dl.link_doctype = 'Customer' and dl.link_name = %s and ifnull(addr.country, '') != ''
		order by addr.is_primary_address desc, addr.modified desc
		limit 1
		""",
		customer,
	)
	if address:
		return address[0][0]

	territory = frappe.db.get_value("Customer", customer, "territory")
	if territory and frappe.db.exists("Country", territory):
		return territory
	return None


def resolve_document_template(destination_country, payment_route):
	"""Most specific template wins: country+route, then country, then route, then fallback."""
	# NOT ["in", ["", None]] -- that compiles to SQL `IN ('', NULL)` and NULL never
	# matches, which made every country-blank route template unreachable.
	blank = ["is", "not set"]
	candidates = []
	if destination_country:
		candidates.append(
			{"destination_country": destination_country, "payment_route": payment_route}
		)
		candidates.append({"destination_country": destination_country, "payment_route": "Any"})
	candidates.append({"destination_country": blank, "payment_route": payment_route})
	candidates.append({"destination_country": blank, "payment_route": "Any"})

	for filters in candidates:
		filters["disabled"] = 0
		name = frappe.db.get_value("Export Document Template", filters, "name")
		if name:
			return name

	return frappe.db.get_value(
		"Export Document Template", {"is_default": 1, "disabled": 0}, "name"
	)


def create_export_shipment(sales_order, guard_duplicates=False):
	"""Shared by the Sales Order hook and the Create button.

	An order legitimately gets more than one shipment when it part-ships, so an
	existing shipment is not by itself a reason to refuse. What we do refuse is a
	second shipment while an earlier one is still untouched at the first state --
	that is the accidental double-click, not a part-shipment.
	"""
	if not sales_order:
		return None

	so = frappe.get_doc("Sales Order", sales_order)

	if guard_duplicates:
		unused = frappe.db.get_value(
			"Export Shipment",
			{"sales_order": so.name, "docstatus": ["<", 2], "status": STATE_ORDER[0]},
			"name",
		)
		if unused:
			frappe.throw(
				_("Export Shipment {0} already exists for this Sales Order and has not been "
				  "started yet. Use it, or move it forward before opening another shipment for "
				  "a part-shipment.").format(
					frappe.utils.get_link_to_form("Export Shipment", unused)
				)
			)

	doc = frappe.new_doc("Export Shipment")
	doc.sales_order = so.name
	doc.customer = so.customer
	doc.customer_name = so.customer_name
	doc.company = so.company
	doc.currency = so.currency
	doc.incoterm = so.incoterm
	doc.status = STATE_ORDER[0]

	# CIF / CIP put the insurance obligation on us
	doc.insurance_required = 1 if (so.incoterm or "").upper() in ("CIF", "CIP") else 0

	doc.insert(ignore_permissions=True)
	return doc


@frappe.whitelist()
def make_export_shipment(sales_order):
	"""Called from the Create button on a submitted export Sales Order.

	Creating an additional shipment for the same order is how a part-shipment is
	recorded -- each one carries its own shipping bill, BL, XAR and EBRC.
	"""
	if not frappe.has_permission("Export Shipment", "create"):
		frappe.throw(_("Not permitted to create an Export Shipment."), frappe.PermissionError)

	doc = create_export_shipment(sales_order, guard_duplicates=True)
	return doc.name if doc else None


@frappe.whitelist()
def count_shipments(sales_order):
	"""Lets the Create button warn before opening a second shipment."""
	return frappe.db.count("Export Shipment", {"sales_order": sales_order, "docstatus": ["<", 2]})
