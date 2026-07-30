import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

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

ROUTE_DIRECT = "Direct through Client"
ROUTE_BANK = "Through Bank"
ROUTE_LC = "Through Letter of Credit"


class ExportShipment(Document):
	def validate(self):
		self.set_defaults_from_order()
		self.set_defaults_from_settings()
		self.sync_cha_quotes()
		self.update_payment_status()
		self.stamp_management_signature()
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
				"named_place",
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
		self.named_place = self.named_place or so.named_place

		if not self.company_currency and self.company:
			self.company_currency = frappe.db.get_value("Company", self.company, "default_currency")

		if not self.destination_country and self.customer:
			self.destination_country = get_customer_country(self.customer)

		if not self.consignee_name:
			self.consignee_name = so.customer_name

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
	# CHA freight comparison -- SOP G.c.i.1-2
	# ------------------------------------------------------------------
	def sync_cha_quotes(self):
		"""Total up each quote and mirror the selected one onto the parent."""
		selected = []
		for row in self.cha_quotes:
			row.total_amount = flt(row.freight_amount) + flt(row.other_charges)
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
		else:
			self.selected_cha = None
			self.selected_freight_amount = 0
			self.selected_transit_days = 0
			self.selected_free_days = 0

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

	def validate_state_requirements(self):
		"""Every gate is enforced in validate() so it holds no matter how the
		status changed -- workflow action, API write or bulk edit."""
		if self.reached("Indent Approved") and self.export_indent:
			approved = frappe.db.get_value("Export Indent", self.export_indent, "management_approved")
			if not approved:
				frappe.throw(
					_("Export Indent {0} is not approved by management yet.").format(
						frappe.utils.get_link_to_form("Export Indent", self.export_indent)
					)
				)

		if self.reached("Freight Finalised") and not self.selected_cha:
			frappe.throw(
				_("Mark one CHA quote as Selected before finalising freight. "
				  "Compare the quotes on price, transit time and free days first.")
			)

		if self.reached("Dispatch Planned") and not self.dispatch_plan_date:
			frappe.throw(_("Set Dispatch Planned On before moving past dispatch planning."))

		if self.reached("Customs Docs Prepared"):
			self.validate_documents_prepared("Pre-Shipment")

		if self.reached("Container Loaded"):
			missing = [
				label
				for label, value in (
					(_("Container Loaded On"), self.loading_date),
					(_("Container No(s)"), self.container_no),
					(_("Customs Seal No"), self.customs_seal_no),
					(_("Shipping Line Seal No"), self.shipping_line_seal_no),
				)
				if not value
			]
			if missing:
				frappe.throw(
					_("Container loading is incomplete. Missing: {0}").format(", ".join(missing))
				)

		if self.reached("Shipped"):
			if self.payment_route == ROUTE_LC and not self.lc_received_on:
				frappe.throw(
					_("Under a Letter of Credit the LC must be received before shipment. "
					  "Set LC Received On.")
				)
			if self.payment_route == ROUTE_LC and self.lc_last_shipment_date:
				if self.etd and getdate(self.etd) > getdate(self.lc_last_shipment_date):
					frappe.throw(
						_("ETD {0} is after the LC's Last Date of Shipment {1}.").format(
							frappe.utils.formatdate(self.etd),
							frappe.utils.formatdate(self.lc_last_shipment_date),
						)
					)
			missing = [
				label
				for label, value in (
					(_("Shipping Bill No"), self.shipping_bill_no),
					(_("Shipping Bill Date"), self.shipping_bill_date),
					(_("ETD"), self.etd),
				)
				if not value
			]
			if missing:
				frappe.throw(_("Cannot mark as Shipped. Missing: {0}").format(", ".join(missing)))

		if self.reached("Post-Shipment Docs Prepared"):
			self.validate_documents_prepared("Post-Shipment")
			if not self.bl_no:
				frappe.throw(_("BL / AWB No is required for post-shipment documents."))
			if self.coo_type != "Not Applicable" and not self.coo_no:
				frappe.throw(
					_("Certificate of Origin type is {0} but the COO No is not filled in.").format(
						self.coo_type
					)
				)
			if self.insurance_required and not self.insurance_policy_no:
				frappe.throw(
					_("Insurance is applicable but the Policy No has not been received yet.")
				)

		if self.reached("Docs Submitted"):
			if not self.management_signed:
				frappe.throw(
					_("Documents cannot be submitted without the management signature. "
					  "Tick Signed by Management.")
				)

		if self.reached("Payment Received") and self.payment_status != "Fully Paid":
			frappe.throw(
				_("Bank closure cannot start before the final payment is received. "
				  "Outstanding on this shipment is {0}.").format(
					frappe.utils.fmt_money(self.outstanding_amount, currency=self.currency)
				)
			)

		if self.reached("XAR Generated"):
			if not (self.xar_no and self.xar_date):
				frappe.throw(_("XAR No and XAR Date are required once the XAR is generated."))

		if self.reached("Bank Submission Done"):
			missing = [
				label
				for label, value in (
					(_("Shipping Bill No"), self.shipping_bill_no),
					(_("Port Code"), self.port_code),
				)
				if not value
			]
			if missing:
				frappe.throw(
					_("Bank submission is incomplete. Missing: {0}").format(", ".join(missing))
				)

		if self.reached("EBRC Generated"):
			if not (self.ebrc_no and self.ebrc_date):
				frappe.throw(_("EBRC No and EBRC Date are required to close the shipment."))

	def validate_documents_prepared(self, stage):
		table = (
			self.pre_shipment_documents if stage == "Pre-Shipment" else self.post_shipment_documents
		)
		if not table:
			frappe.throw(
				_("No {0} documents listed. Load a document checklist first.").format(_(stage))
			)

		pending = [row.document_name for row in table if row.is_required and not row.prepared]
		if pending:
			frappe.throw(
				_("These required {0} documents are not prepared yet:<br>{1}").format(
					_(stage), "<br>".join("- " + d for d in pending)
				)
			)

	# ------------------------------------------------------------------
	# document checklist
	# ------------------------------------------------------------------
	@frappe.whitelist()
	def load_document_checklist(self, overwrite=False):
		"""Populate both checklists from the matching Export Document Template."""
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

		added = 0
		for row in template.documents:
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


# ----------------------------------------------------------------------
# module level helpers
# ----------------------------------------------------------------------
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
	doc.named_place = so.named_place
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
