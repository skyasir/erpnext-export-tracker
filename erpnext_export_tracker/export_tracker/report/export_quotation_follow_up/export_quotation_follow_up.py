"""SOP D / E -- open export quotations and where the follow-up stands."""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Quotation"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Quotation", "width": 150},
		{"label": _("Customer / Lead"), "fieldname": "party_name", "fieldtype": "Data",
		 "width": 200},
		{"label": _("Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 95},
		{"label": _("Valid Till"), "fieldname": "valid_till", "fieldtype": "Date", "width": 95},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link",
		 "options": "Currency", "width": 80},
		{"label": _("Value"), "fieldname": "grand_total", "fieldtype": "Currency",
		 "options": "currency", "width": 130},
		{"label": _("Port of Discharge"), "fieldname": "custom_port_of_discharge",
		 "fieldtype": "Data", "width": 140},
		{"label": _("Destination"), "fieldname": "custom_country_of_final_destination",
		 "fieldtype": "Data", "width": 120},
		{"label": _("Next Follow-up"), "fieldname": "custom_next_followup_date",
		 "fieldtype": "Date", "width": 115},
		{"label": _("Days Since Activity"), "fieldname": "days_idle", "fieldtype": "Int",
		 "width": 130},
		{"label": _("Revision Of"), "fieldname": "amended_from", "fieldtype": "Link",
		 "options": "Quotation", "width": 140},
	]


def get_data(filters):
	conditions = ["q.docstatus = 1", "q.custom_is_export = 1"]
	values = {}

	if not filters.get("include_closed"):
		conditions.append("q.status not in ('Ordered', 'Lost', 'Closed', 'Expired')")
	if filters.get("company"):
		conditions.append("q.company = %(company)s")
		values["company"] = filters.get("company")
	if filters.get("customer"):
		conditions.append("q.party_name = %(customer)s")
		values["customer"] = filters.get("customer")
	if filters.get("overdue_only"):
		conditions.append(
			"(q.custom_next_followup_date is not null and q.custom_next_followup_date <= curdate())"
		)

	return frappe.db.sql(
		"""
		select
			q.name, q.party_name, q.transaction_date, q.valid_till, q.status, q.currency,
			q.grand_total, q.custom_port_of_discharge, q.custom_country_of_final_destination,
			q.custom_next_followup_date, q.amended_from,
			datediff(curdate(), q.modified) as days_idle
		from `tabQuotation` q
		where {conditions}
		order by q.custom_next_followup_date asc, days_idle desc
		""".format(conditions=" and ".join(conditions)),
		values,
		as_dict=True,
	)
