import frappe
from frappe.utils import flt


def on_submit(doc, method=None):
	"""Stamp the dispatch on the shipment when the export DN is submitted."""
	if not doc.get("custom_is_export"):
		return

	shipment_name = doc.get("custom_export_shipment") or find_shipment_from_orders(doc)
	if not shipment_name:
		return

	if not doc.get("custom_export_shipment"):
		doc.db_set("custom_export_shipment", shipment_name, update_modified=False)

	shipment = frappe.get_doc("Export Shipment", shipment_name)

	updates = {"delivery_note": doc.name}
	if not shipment.loading_date:
		updates["loading_date"] = doc.posting_date
	if not shipment.shipping_bill_no and doc.get("shipping_bill_number"):
		updates["shipping_bill_no"] = doc.get("shipping_bill_number")
		updates["shipping_bill_date"] = doc.get("shipping_bill_date")
		updates["port_code"] = doc.get("port_code")

	total_net = sum(flt(row.get("total_weight")) for row in doc.items)
	if total_net and not shipment.net_weight:
		updates["net_weight"] = total_net

	shipment.db_set(updates, update_modified=False)


def find_shipment_from_orders(doc):
	orders = {row.against_sales_order for row in doc.items if row.get("against_sales_order")}
	for order in orders:
		name = frappe.db.get_value(
			"Export Shipment",
			{"sales_order": order, "docstatus": ["<", 2], "delivery_note": ["in", ["", None]]},
			"name",
		)
		if name:
			return name
	return None
