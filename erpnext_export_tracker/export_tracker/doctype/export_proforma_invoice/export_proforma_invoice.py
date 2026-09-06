import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

# What the proforma settles and the order has to agree with. The proforma is the
# earlier document, so it is the source: these flow PI -> Sales Order, never back.
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


class ExportProformaInvoice(Document):
	def validate(self):
		self.set_totals()
		self.sync_buyer()

	def on_update_after_submit(self):
		# validate() does not run on a submitted document, so the mirror the
		# checkbox does has to be repeated here before the order is updated
		self.sync_buyer()
		self.push_to_sales_order()

	def set_totals(self):
		self.total_qty = sum(flt(row.qty) for row in self.items)
		for row in self.items:
			row.amount = flt(row.qty) * flt(row.rate)
			row.currency = self.currency
		self.net_total = sum(flt(row.amount) for row in self.items)
		self.grand_total = (
			flt(self.net_total)
			+ flt(self.freight_charges)
			+ flt(self.insurance_charges)
			+ flt(self.other_charges)
		)
		if not self.fob_value:
			self.fob_value = self.net_total

	def sync_buyer(self):
		if self.buyer_same_as_consignee:
			self.buyer_name = self.consignee_name
			self.buyer_address = self.consignee_address

	def push_to_sales_order(self):
		"""Keep the linked order's export block in step with the proforma.

		Only while the order is still a draft. Once it is submitted its fields are
		the order's own record of what was agreed, and a proforma edited afterwards
		must not rewrite it silently -- the user is told to amend the order instead.
		"""
		if not self.sales_order:
			return

		docstatus = frappe.db.get_value("Sales Order", self.sales_order, "docstatus")
		if docstatus != 0:
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
	"""The order the proforma turned into -- SOP section 13.

	Returned unsaved so the user can set delivery date and warehouse, which the
	proforma has no opinion about. The link back is written on the order's insert
	hook, not here, because the order has no name yet.
	"""

	def postprocess(source, target):
		target.custom_is_export = 1
		target.custom_proforma_invoice = source.name
		target.currency = source.currency
		target.conversion_rate = source.conversion_rate or 1
		target.incoterm = source.incoterm
		target.named_place = source.named_place
		for field, custom in EXPORT_FIELDS.items():
			target.set(custom, source.get(field))
		target.run_method("set_missing_values")

	return get_mapped_doc(
		"Export Proforma Invoice",
		source_name,
		{
			"Export Proforma Invoice": {
				"doctype": "Sales Order",
				"field_map": {"customer": "customer", "company": "company"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Export Indent Item": {
				"doctype": "Sales Order Item",
				"field_map": {"item_code": "item_code", "qty": "qty", "rate": "rate",
				              "uom": "uom", "description": "description"},
			},
		},
		target_doc,
		postprocess,
	)
