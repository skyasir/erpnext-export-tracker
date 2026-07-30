"""SOP I -- where every shipment stands in the XAR -> bank -> EBRC chain."""

import frappe
from frappe import _
from frappe.utils import add_months, date_diff, getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Shipment"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Export Shipment", "width": 150},
		{"label": _("Closure Stage"), "fieldname": "closure_stage", "fieldtype": "Data",
		 "width": 190},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link",
		 "options": "Customer", "width": 170},
		{"label": _("Shipping Bill"), "fieldname": "shipping_bill_no", "fieldtype": "Data",
		 "width": 120},
		{"label": _("SB Date"), "fieldname": "shipping_bill_date", "fieldtype": "Date",
		 "width": 95},
		{"label": _("Realisation Due By"), "fieldname": "realisation_due", "fieldtype": "Date",
		 "width": 130},
		{"label": _("Days Left"), "fieldname": "days_left", "fieldtype": "Int", "width": 90},
		{"label": _("Payment"), "fieldname": "payment_status", "fieldtype": "Data", "width": 100},
		{"label": _("Paid On"), "fieldname": "final_payment_date", "fieldtype": "Date",
		 "width": 95},
		{"label": _("XAR No"), "fieldname": "xar_no", "fieldtype": "Data", "width": 110},
		{"label": _("XAR Date"), "fieldname": "xar_date", "fieldtype": "Date", "width": 95},
		{"label": _("Bank Submitted"), "fieldname": "bank_submission_date", "fieldtype": "Date",
		 "width": 115},
		{"label": _("EBRC No"), "fieldname": "ebrc_no", "fieldtype": "Data", "width": 110},
		{"label": _("EBRC Date"), "fieldname": "ebrc_date", "fieldtype": "Date", "width": 95},
		{"label": _("Days in Stage"), "fieldname": "days_in_stage", "fieldtype": "Int",
		 "width": 105},
	]


def get_data(filters):
	conditions = {}
	if filters.get("company"):
		conditions["company"] = filters.get("company")
	if filters.get("customer"):
		conditions["customer"] = filters.get("customer")
	if not filters.get("include_closed"):
		conditions["ebrc_no"] = ["in", ["", None]]

	rows = frappe.get_all(
		"Export Shipment",
		filters=conditions,
		fields=[
			"name", "customer", "shipping_bill_no", "shipping_bill_date", "payment_status",
			"final_payment_date", "xar_no", "xar_date", "bank_submission_date", "ebrc_no",
			"ebrc_date", "etd", "status",
		],
		order_by="shipping_bill_date asc",
	)

	months = (
		frappe.db.get_single_value("Export Tracker Settings", "realisation_period_months") or 9
	)

	out = []
	for row in rows:
		row.closure_stage, anchor = classify(row)

		if row.shipping_bill_date:
			row.realisation_due = add_months(getdate(row.shipping_bill_date), months)
			row.days_left = date_diff(row.realisation_due, today())
		else:
			row.realisation_due = None
			row.days_left = None

		row.days_in_stage = date_diff(today(), anchor) if anchor else None

		if filters.get("stage") and row.closure_stage != filters.get("stage"):
			continue
		out.append(row)

	return out


def classify(row):
	"""Returns (stage label, date the shipment entered that stage)."""
	if row.ebrc_no:
		return _("Closed - EBRC Generated"), row.ebrc_date
	if row.bank_submission_date:
		return _("Pending EBRC (DGFT)"), row.bank_submission_date
	if row.xar_no:
		return _("Pending Bank Submission"), row.xar_date
	if row.payment_status == "Fully Paid":
		return _("Pending XAR"), row.final_payment_date
	return _("Awaiting Final Payment"), row.etd
