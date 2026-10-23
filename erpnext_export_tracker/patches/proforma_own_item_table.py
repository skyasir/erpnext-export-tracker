"""Give the proforma its own item table, and GST.

It borrowed Sales Order Item, which meant ERPNext's "parent name plus Item"
lookup had to be tricked and India Compliance never recognised the document at
all -- so GST did not compute. It has Proforma Invoice Item now, and the GST
block India Compliance gives a Sales Order.

Rows already captured are moved across; nothing is left behind.
"""

import frappe

from erpnext_export_tracker.install import make_gst_custom_fields

ROW_FIELDS_TO_SKIP = {"name", "creation", "modified", "owner", "modified_by",
                      "doctype", "parenttype"}


def execute():
	make_gst_custom_fields()
	move_rows()
	frappe.db.commit()


def move_rows():
	"""Carry any proforma rows still sitting in tabSales Order Item across."""
	if not (frappe.db.table_exists("Sales Order Item")
	        and frappe.db.table_exists("Proforma Invoice Item")):
		return

	rows = frappe.db.sql(
		"""select name from `tabSales Order Item` where parenttype = 'Proforma Invoice'""",
		as_dict=True,
	)
	for row in rows:
		source = frappe.db.sql(
			"""select * from `tabSales Order Item` where name = %s""",
			row.name, as_dict=True,
		)[0]
		if frappe.db.exists("Proforma Invoice Item", source["name"]):
			continue

		target = frappe.new_doc("Proforma Invoice Item")
		for field, value in source.items():
			if field in ROW_FIELDS_TO_SKIP or not target.meta.has_field(field):
				continue
			target.set(field, value)
		target.name = source["name"]
		target.parenttype = "Proforma Invoice"
		target.flags.name_set = True
		target.db_insert()

	if rows:
		frappe.db.sql(
			"""delete from `tabSales Order Item` where parenttype = 'Proforma Invoice'"""
		)
