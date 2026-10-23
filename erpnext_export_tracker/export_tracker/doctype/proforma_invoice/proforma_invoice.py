import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

from erpnext.controllers.selling_controller import SellingController

from erpnext_export_tracker.selling_doctype import register as register_selling_doctype

# harmless if app load already did it; this module is also imported on its own
# by scripts and tests that never go through the app's __init__
register_selling_doctype()


# The export block only. Items, taxes and totals reach the order through the
# mapper; these are the fields the proforma keeps agreeing with it afterwards.
EXPORT_FIELDS = {
	"consignee_name": "custom_consignee_name",
	"consignee_address": "custom_consignee_address",
	"buyer_name": "custom_buyer_name",
	"buyer_address": "custom_buyer_address",
	"notify_name": "custom_notify_name",
	"notify_address": "custom_notify_address",
	"port_of_discharge": "custom_port_of_discharge",
	"final_destination": "custom_final_destination",
	"country_of_final_destination": "custom_country_of_final_destination",
	"terms_of_payment": "custom_terms_of_payment",
}


class ProformaInvoice(SellingController):
	"""A proforma is a Sales Order that has not been agreed yet.

	It extends SellingController rather than reimplementing anything, so pricing
	rules, tax templates, discounts, rounding and the amount in words all behave
	exactly as they do on an order -- and it uses the Sales Order's own item and
	tax tables, which makes raising the order a straight copy.

	Export is a flag on it, not its purpose: a domestic proforma is the same
	document with the export block hidden.
	"""

	def calculate_taxes_and_totals(self):
		"""Total up as a selling document.

		ERPNext decides whether a document is bought or sold by matching its name
		against a list written into taxes_and_totals.py -- Quotation, Sales Order,
		Delivery Note, Sales Invoice, POS Invoice. That one is a literal, so
		registering the doctype elsewhere does not reach it, and anything else
		falls to the purchase branch which reads `category` off each tax row: a
		Purchase Taxes and Charges field a sales row does not have.
		"""
		actual = self.doctype
		self.doctype = "Sales Order"
		try:
			super().calculate_taxes_and_totals()
		finally:
			self.doctype = actual

	def validate(self):
		super().validate()
		self.set_status()
		self.sync_buyer()
		self.validate_export_details()

	def on_submit(self):
		self.set_status(update=True)

	def on_cancel(self):
		self.set_status(update=True)

	def on_update_after_submit(self):
		# validate() does not run on a submitted document, so the mirroring the
		# checkbox does has to be repeated before the order is updated
		self.sync_buyer()
		self.push_to_sales_order()

	def set_status(self, update=False):
		status = {0: "Draft", 1: "Submitted", 2: "Cancelled"}[self.docstatus]
		if self.docstatus == 1 and self.sales_order:
			status = "Ordered"

		self.status = status
		if update:
			self.db_set("status", status, update_modified=False)

	def sync_buyer(self):
		if self.is_export and self.buyer_same_as_consignee:
			self.buyer_name = self.consignee_name
			self.buyer_address = self.consignee_address

	def validate_export_details(self):
		if not self.is_export:
			return
		if not self.consignee_name:
			frappe.throw(_("An export proforma needs a consignee."))

	def push_to_sales_order(self):
		"""Keep the linked order's export block in step with the proforma.

		Only while the order is still a draft. Once it is submitted its fields are
		the order's own record of what was agreed, and a proforma corrected
		afterwards must not rewrite it silently.
		"""
		if not (self.sales_order and self.is_export):
			return

		if frappe.db.get_value("Sales Order", self.sales_order, "docstatus") != 0:
			frappe.msgprint(
				_("Sales Order {0} is already submitted, so its export details were left "
				  "as they are. Amend the order if they have to change.").format(
					frappe.utils.get_link_to_form("Sales Order", self.sales_order)
				),
				indicator="orange",
			)
			return

		so = frappe.get_doc("Sales Order", self.sales_order)
		for source, target in EXPORT_FIELDS.items():
			so.set(target, self.get(source))
		so.incoterm = self.incoterm
		so.named_place = self.named_place
		so.custom_is_export = 1
		so.save(ignore_permissions=True)

	@frappe.whitelist()
	def make_sales_order(self):
		if self.docstatus != 1:
			frappe.throw(_("Submit the proforma invoice before raising the order."))
		if self.sales_order and frappe.db.exists("Sales Order", self.sales_order):
			frappe.throw(
				_("Sales Order {0} already exists for this proforma.").format(
					frappe.utils.get_link_to_form("Sales Order", self.sales_order)
				)
			)
		return make_sales_order(self.name)


@frappe.whitelist()
def make_sales_order(source_name, target_doc=None):
	"""The order the proforma turned into.

	Proforma Invoice Item is a copy of Sales Order Item field for field, and both
	documents share Sales Taxes and Charges, so items, taxes, discount and totals
	copy across untouched. Returned unsaved: delivery date and warehouse are the
	order's business, not the proforma's.
	"""

	def postprocess(source, target):
		target.custom_proforma_invoice = source.name
		if source.is_export:
			target.custom_is_export = 1
			for field, custom in EXPORT_FIELDS.items():
				target.set(custom, source.get(field))
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	target = get_mapped_doc(
		"Proforma Invoice",
		source_name,
		{
			"Proforma Invoice": {
				"doctype": "Sales Order",
				"field_map": {"transaction_date": "transaction_date"},
				"field_no_map": ["naming_series", "status", "valid_till", "amended_from"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Proforma Invoice Item": {
				"doctype": "Sales Order Item",
				"field_no_map": ["delivery_date"],
			},
			"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges"},
		},
		target_doc,
		postprocess,
	)

	return target


@frappe.whitelist()
def make_proforma_invoice(source_name, target_doc=None):
	"""The proforma a quotation turned into.

	Quotation -> Proforma Invoice -> Sales Order is the whole selling chain here,
	and each step is a straight copy: the proforma carries the order's structure
	and the quotation's own item and tax tables map onto it field for field.

	A quotation raised to a Lead has no customer to put on the proforma, so it is
	refused rather than half-filled.
	"""
	quotation = frappe.db.get_value(
		"Quotation", source_name, ["quotation_to", "party_name"], as_dict=True
	)
	if quotation and quotation.quotation_to != "Customer":
		frappe.throw(
			_("Quotation {0} is addressed to a {1}. Convert it to a customer before "
			  "raising a proforma invoice.").format(source_name, quotation.quotation_to)
		)

	def postprocess(source, target):
		target.customer = source.party_name
		target.quotation = source.name
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	return get_mapped_doc(
		"Quotation",
		source_name,
		{
			"Quotation": {
				"doctype": "Proforma Invoice",
				"field_map": {"transaction_date": "transaction_date"},
				"field_no_map": ["naming_series", "status", "amended_from", "valid_till",
				                 "title"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Quotation Item": {
				"doctype": "Proforma Invoice Item",
				"field_no_map": ["delivery_date"],
			},
			"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges"},
		},
		target_doc,
		postprocess,
	)
