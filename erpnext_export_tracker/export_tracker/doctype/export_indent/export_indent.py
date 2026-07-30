import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class ExportIndent(Document):
	def validate(self):
		self.set_defaults_from_order()
		self.calculate_totals()
		self.validate_approval_sequence()
		self.set_status()

	def set_defaults_from_order(self):
		if not self.sales_order:
			return

		so = frappe.db.get_value(
			"Sales Order",
			self.sales_order,
			["customer", "customer_name", "company", "currency"],
			as_dict=True,
		)
		if not so:
			return

		self.customer = self.customer or so.customer
		self.customer_name = self.customer_name or so.customer_name
		self.company = self.company or so.company
		self.currency = self.currency or so.currency

		for row in self.items:
			if not row.currency:
				row.currency = self.currency

	def calculate_totals(self):
		self.total_qty = sum(flt(r.qty) for r in self.items)
		for row in self.items:
			row.amount = flt(row.qty) * flt(row.rate)
		self.total_amount = sum(flt(r.amount) for r in self.items)

	def validate_approval_sequence(self):
		"""Management signs off only after production has confirmed the technical
		details -- SOP G.a."""
		if self.management_approved and not self.production_confirmed:
			frappe.throw(
				_("Production must confirm the technical details before management approval.")
			)

		if self.production_confirmed and not self.production_confirmed_by:
			self.production_confirmed_by = frappe.session.user
			self.production_confirmed_on = today()
		elif not self.production_confirmed:
			self.production_confirmed_by = None
			self.production_confirmed_on = None

		if self.management_approved and not self.management_approved_by:
			self.management_approved_by = frappe.session.user
			self.management_approved_on = today()
		elif not self.management_approved:
			self.management_approved_by = None
			self.management_approved_on = None

	def set_status(self):
		if self.management_approved:
			self.status = "Management Approved"
		elif self.production_confirmed:
			self.status = "Production Confirmed"
		else:
			self.status = "Draft"

	def on_update(self):
		self.link_to_shipment()

	def link_to_shipment(self):
		shipment = frappe.db.exists(
			"Export Shipment", {"sales_order": self.sales_order, "docstatus": ["<", 2]}
		)
		if shipment and not frappe.db.get_value("Export Shipment", shipment, "export_indent"):
			frappe.db.set_value("Export Shipment", shipment, "export_indent", self.name)


@frappe.whitelist()
def make_export_indent(sales_order):
	"""Build the indent from the Sales Order -- SOP G.a, replacing the Excel sheet."""
	if not frappe.has_permission("Export Indent", "create"):
		frappe.throw(_("Not permitted to create an Export Indent."), frappe.PermissionError)

	existing = frappe.db.exists(
		"Export Indent", {"sales_order": sales_order, "docstatus": ["<", 2]}
	)
	if existing:
		frappe.throw(
			_("Export Indent {0} already exists for this Sales Order.").format(
				frappe.utils.get_link_to_form("Export Indent", existing)
			)
		)

	so = frappe.get_doc("Sales Order", sales_order)

	doc = frappe.new_doc("Export Indent")
	doc.sales_order = so.name
	doc.customer = so.customer
	doc.customer_name = so.customer_name
	doc.company = so.company
	doc.currency = so.currency
	doc.indent_date = today()

	for item in so.items:
		doc.append(
			"items",
			{
				"item_code": item.item_code,
				"item_name": item.item_name,
				"description": item.description,
				"qty": item.qty,
				"uom": item.uom,
				"rate": item.rate,
				"currency": so.currency,
				"gst_hsn_code": item.get("gst_hsn_code"),
			},
		)

	doc.insert(ignore_permissions=True)
	return doc.name
