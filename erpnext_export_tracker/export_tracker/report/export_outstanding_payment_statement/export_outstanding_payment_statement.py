"""SOP G.h.2 -- Outstanding Payment Statement for management reporting."""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data, None, None, get_summary(data)


def get_columns():
	return [
		{"label": _("Shipment"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Export Shipment", "width": 150},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link",
		 "options": "Customer", "width": 180},
		{"label": _("Invoice"), "fieldname": "sales_invoice", "fieldtype": "Link",
		 "options": "Sales Invoice", "width": 120},
		{"label": _("Invoice Date"), "fieldname": "invoice_date", "fieldtype": "Date",
		 "width": 100},
		{"label": _("Terms"), "fieldname": "terms_of_payment", "fieldtype": "Data", "width": 140},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link",
		 "options": "Currency", "width": 80},
		{"label": _("Invoice Amount"), "fieldname": "invoice_amount", "fieldtype": "Currency",
		 "options": "currency", "width": 130},
		{"label": _("Received"), "fieldname": "total_received", "fieldtype": "Currency",
		 "options": "currency", "width": 130},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency",
		 "options": "currency", "width": 130},
		{"label": _("Age (Days)"), "fieldname": "age", "fieldtype": "Int", "width": 90},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 150},
		{"label": _("Route"), "fieldname": "payment_route", "fieldtype": "Data", "width": 140},
	]


def get_data(filters):
	conditions = ["1 = 1"]
	values = {}

	if not filters.get("include_paid"):
		conditions.append("s.payment_status != 'Fully Paid'")
	if filters.get("company"):
		conditions.append("s.company = %(company)s")
		values["company"] = filters.get("company")
	if filters.get("customer"):
		conditions.append("s.customer = %(customer)s")
		values["customer"] = filters.get("customer")
	if filters.get("from_date") and filters.get("to_date"):
		conditions.append("si.posting_date between %(from_date)s and %(to_date)s")
		values["from_date"] = filters.get("from_date")
		values["to_date"] = filters.get("to_date")

	return frappe.db.sql(
		"""
		select
			s.name, s.customer, s.sales_invoice, si.posting_date as invoice_date,
			s.terms_of_payment, s.currency, s.invoice_amount, s.total_received,
			s.outstanding_amount, s.status, s.payment_route,
			datediff(curdate(), coalesce(si.posting_date, s.etd)) as age
		from `tabExport Shipment` s
		left join `tabSales Invoice` si on si.name = s.sales_invoice
		where {conditions}
		order by age desc
		""".format(conditions=" and ".join(conditions)),
		values,
		as_dict=True,
	)


def get_summary(data):
	buckets = {}
	for row in data:
		buckets.setdefault(row.currency or "-", 0)
		buckets[row.currency or "-"] += row.outstanding_amount or 0

	return [
		{
			"value": amount,
			"label": _("Outstanding ({0})").format(currency),
			"datatype": "Currency",
			"currency": currency if currency != "-" else None,
			"indicator": "Red" if amount else "Green",
		}
		for currency, amount in buckets.items()
	]
