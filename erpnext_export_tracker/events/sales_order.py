import frappe
from frappe import _

from erpnext_export_tracker.export_tracker.doctype.export_shipment.export_shipment import (
	create_export_shipment,
)


def after_insert(doc, method=None):
	"""Write the order back onto the proforma it came from.

	The link is set here rather than in the mapper because the order has no name
	until it is saved, and both sides need to point at each other for the
	proforma's later edits to find their way across.
	"""
	pi = doc.get("custom_proforma_invoice")
	if not pi or frappe.db.get_value("Proforma Invoice", pi, "sales_order"):
		return

	# written straight to the row rather than through the document: the proforma
	# is submitted by now, and its status is derived from this link, so both move
	# together
	frappe.db.set_value(
		"Proforma Invoice", pi,
		{"sales_order": doc.name, "status": "Ordered"},
		update_modified=False,
	)


def on_submit(doc, method=None):
	"""Tick Is Export on a Sales Order and submitting it opens the shipment."""
	if not doc.get("custom_is_export"):
		return

	if frappe.db.exists("Export Shipment", {"sales_order": doc.name, "docstatus": ["<", 2]}):
		return

	shipment = create_export_shipment(doc.name)
	if not shipment:
		return

	# copy the order-level export attributes across
	for source, target in (
		("custom_consignee_name", "consignee_name"),
		("custom_consignee_address", "consignee_address"),
		("custom_buyer_name", "buyer_name"),
		("custom_buyer_address", "buyer_address"),
		("custom_port_of_discharge", "port_of_discharge"),
		("custom_final_destination", "final_destination"),
		("custom_country_of_final_destination", "country_of_final_destination"),
		("custom_terms_of_payment", "terms_of_payment"),
	):
		value = doc.get(source)
		if value:
			shipment.db_set(target, value, update_modified=False)

	if doc.get("custom_buyer_name"):
		shipment.db_set("buyer_same_as_consignee", 0, update_modified=False)

	doc.db_set("custom_export_shipment", shipment.name, update_modified=False)

	frappe.msgprint(
		_("Export Shipment {0} created.").format(
			frappe.utils.get_link_to_form("Export Shipment", shipment.name)
		),
		indicator="green",
		alert=True,
	)


def on_cancel(doc, method=None):
	"""Don't let a cancelled order strand an in-flight shipment."""
	if not doc.get("custom_is_export"):
		return

	shipments = frappe.get_all(
		"Export Shipment",
		filters={"sales_order": doc.name, "docstatus": ["<", 2]},
		fields=["name", "status"],
	)
	if not shipments:
		return

	live = [s for s in shipments if s.status != "Order Confirmed"]
	if live:
		frappe.throw(
			_("Export Shipment {0} is already at status {1}. Roll it back or delete it before "
			  "cancelling this Sales Order.").format(
				frappe.utils.get_link_to_form("Export Shipment", live[0].name), live[0].status
			)
		)

	for s in shipments:
		frappe.msgprint(
			_("Export Shipment {0} is still at Order Confirmed - delete it if this order is dead.").format(
				frappe.utils.get_link_to_form("Export Shipment", s.name)
			),
			indicator="orange",
		)
