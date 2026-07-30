import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Shipment"), "fieldname": "shipment", "fieldtype": "Link",
		 "options": "Export Shipment", "width": 150},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link",
		 "options": "Customer", "width": 170},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 150},
		{"label": _("ETD"), "fieldname": "etd", "fieldtype": "Date", "width": 90},
		{"label": _("Days to ETD"), "fieldname": "days_to_etd", "fieldtype": "Int", "width": 90},
		{"label": _("Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 110},
		{"label": _("Document"), "fieldname": "document_name", "fieldtype": "Data", "width": 260},
		{"label": _("Responsibility"), "fieldname": "responsibility", "fieldtype": "Data",
		 "width": 120},
		{"label": _("Required"), "fieldname": "is_required", "fieldtype": "Check", "width": 80},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 180},
	]


def get_data(filters):
	conditions = ["doc.prepared = 0"]
	values = {}

	if filters.get("only_required"):
		conditions.append("doc.is_required = 1")
	if filters.get("stage"):
		conditions.append("doc.stage = %(stage)s")
		values["stage"] = filters.get("stage")
	if filters.get("shipment"):
		conditions.append("s.name = %(shipment)s")
		values["shipment"] = filters.get("shipment")
	if filters.get("company"):
		conditions.append("s.company = %(company)s")
		values["company"] = filters.get("company")
	if filters.get("responsibility"):
		conditions.append("doc.responsibility = %(responsibility)s")
		values["responsibility"] = filters.get("responsibility")
	if not filters.get("include_closed"):
		conditions.append("s.status != 'EBRC Generated'")

	rows = frappe.db.sql(
		"""
		select
			s.name as shipment, s.customer, s.status, s.etd,
			datediff(s.etd, curdate()) as days_to_etd,
			doc.stage, doc.document_name, doc.responsibility, doc.is_required, doc.remarks
		from `tabExport Document Item` doc
		inner join `tabExport Shipment` s on s.name = doc.parent
		where doc.parenttype = 'Export Shipment' and {conditions}
		order by s.etd asc, s.name asc, doc.stage asc, doc.idx asc
		""".format(conditions=" and ".join(conditions)),
		values,
		as_dict=True,
	)
	return rows
