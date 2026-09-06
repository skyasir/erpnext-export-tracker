from contextlib import contextmanager

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

from erpnext.controllers.selling_controller import SellingController

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

	@contextmanager
	def as_sales_order(self):
		"""Answer to "Sales Order" for the length of a call.

		ERPNext works out which item doctype to read by appending " Item" to the
		parent's name, ignoring the `child_doctype` it is already holding. This
		document uses Sales Order Item, so that lookup asks for a "Proforma
		Invoice Item" that does not exist, and every item you pick reports "not
		found".

		Borrowing the name is honest rather than a trick: the two documents have
		the same item table, the same tax table and the same totals, so every
		rate, pricing rule and item default that follows is the one an order
		would have got.
		"""
		actual = self.doctype
		self.doctype = "Sales Order"
		try:
			yield
		finally:
			self.doctype = actual

	def set_missing_item_details(self, for_validate=False):
		with self.as_sales_order():
			super().set_missing_item_details(for_validate=for_validate)

	def fetch_item_details(self, item):
		# what the form calls through process_item_selection when a row's item
		# code is chosen
		with self.as_sales_order():
			return super().fetch_item_details(item)

	def calculate_taxes_and_totals(self):
		"""Total up as a selling document.

		ERPNext decides whether a document is bought or sold by matching its name
		against a hard-coded list -- Quotation, Sales Order, Delivery Note, Sales
		Invoice, POS Invoice. Anything else falls to the purchase branch, which
		reads `category` off each tax row: a Purchase Taxes and Charges field that
		a Sales Taxes and Charges row does not have. The first tax you added blew
		up on it.
		"""
		with self.as_sales_order():
			super().calculate_taxes_and_totals()

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

	Both documents use Sales Order Item and Sales Taxes and Charges, so items,
	taxes, discount and totals copy across untouched. Returned unsaved: delivery
	date and warehouse are the order's business, not the proforma's.
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
			"Sales Order Item": {
				"doctype": "Sales Order Item",
				"field_no_map": ["delivery_date"],
			},
			"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges"},
		},
		target_doc,
		postprocess,
	)

	restore_taxes(frappe.get_doc("Proforma Invoice", source_name), target)
	return target


# what identifies a charge; the rest is recomputed from the order's own figures
TAX_FIELDS = (
	"charge_type", "account_head", "description", "rate", "cost_center",
	"included_in_print_rate", "row_id", "item_wise_tax_detail", "tax_amount",
	"account_currency",
)


def restore_taxes(source, target):
	"""Put back the tax table the mapper just copied.

	India Compliance resets a document's GST details when it decides the mapping
	crosses between a sales and a purchase document, and it decides that by
	matching both doctype names against its own list. A Proforma Invoice is not
	in that list, so a perfectly ordinary proforma-to-order copy looks like a
	crossing and the tax rows are wiped -- the order came out at the net total
	with the charges gone.

	Only ever runs when the target has lost them; an order that legitimately has
	its own taxes is left alone.
	"""
	if not source.get("taxes") or target.get("taxes"):
		return

	for row in source.taxes:
		target.append("taxes", {field: row.get(field) for field in TAX_FIELDS})

	target.run_method("calculate_taxes_and_totals")
