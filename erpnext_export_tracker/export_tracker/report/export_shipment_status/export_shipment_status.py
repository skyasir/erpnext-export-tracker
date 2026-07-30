import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Shipment"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Export Shipment", "width": 150},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 160},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link",
		 "options": "Customer", "width": 180},
		{"label": _("Destination"), "fieldname": "destination_country", "fieldtype": "Data",
		 "width": 110},
		{"label": _("Route"), "fieldname": "payment_route", "fieldtype": "Data", "width": 140},
		{"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link",
		 "options": "Sales Order", "width": 140},
		{"label": _("Invoice"), "fieldname": "sales_invoice", "fieldtype": "Link",
		 "options": "Sales Invoice", "width": 120},
		{"label": _("CHA"), "fieldname": "selected_cha", "fieldtype": "Link",
		 "options": "Supplier", "width": 140},
		{"label": _("ETD"), "fieldname": "etd", "fieldtype": "Date", "width": 90},
		{"label": _("ETA"), "fieldname": "eta", "fieldtype": "Date", "width": 90},
		{"label": _("Shipping Bill"), "fieldname": "shipping_bill_no", "fieldtype": "Data",
		 "width": 120},
		{"label": _("BL / AWB"), "fieldname": "bl_no", "fieldtype": "Data", "width": 120},
		{"label": _("Invoice Amount"), "fieldname": "invoice_amount", "fieldtype": "Currency",
		 "options": "currency", "width": 120},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency",
		 "options": "currency", "width": 120},
		{"label": _("Payment"), "fieldname": "payment_status", "fieldtype": "Data", "width": 100},
		{"label": _("XAR No"), "fieldname": "xar_no", "fieldtype": "Data", "width": 110},
		{"label": _("EBRC No"), "fieldname": "ebrc_no", "fieldtype": "Data", "width": 110},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link",
		 "options": "Currency", "width": 80, "hidden": 1},
	]


def get_data(filters):
	conditions = {}
	for field in ("company", "customer", "status", "payment_route", "destination_country",
	              "payment_status"):
		if filters.get(field):
			conditions[field] = filters.get(field)

	if filters.get("from_date") and filters.get("to_date"):
		conditions["etd"] = ["between", [filters.get("from_date"), filters.get("to_date")]]

	if filters.get("hide_closed"):
		conditions["status"] = ["!=", "EBRC Generated"]

	return frappe.get_all(
		"Export Shipment",
		filters=conditions,
		fields=[
			"name", "status", "customer", "destination_country", "payment_route", "sales_order",
			"sales_invoice", "selected_cha", "etd", "eta", "shipping_bill_no", "bl_no",
			"invoice_amount", "outstanding_amount", "payment_status", "xar_no", "ebrc_no",
			"currency",
		],
		order_by="coalesce(etd, creation) desc",
	)
