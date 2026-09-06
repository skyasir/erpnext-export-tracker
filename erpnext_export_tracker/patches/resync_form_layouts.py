"""Let the app's layout through on a site that has customised its forms.

Customize Form writes a `field_order` Property Setter, and frappe's meta gives
that property priority over the DocType's own order (see Meta.sort_fields).
On this site somebody had opened Customize Form on six of the app's doctypes --
Export Shipment and five of its child tables -- so every layout the app ships was
being overridden by a frozen list. Fields added by a release dropped to the
bottom, and on Export CHA Quote the section breaks ended up *after* the fields
they were supposed to introduce, which rendered the row editor as a jumble.

This rebuilds each property setter from the DocType's own order and splices the
site's custom fields back in after whatever they were anchored to, so the layout
lands without discarding anyone's customisation.
"""

import json

import frappe

MODULE = "Export Tracker"


def execute():
	for doctype in frappe.get_all("DocType", filters={"module": MODULE}, pluck="name"):
		resync(doctype)

	frappe.db.commit()


def resync(doctype):
	name = frappe.db.exists("Property Setter", {"doc_type": doctype, "property": "field_order"})
	if not name:
		return

	standard = frappe.get_all(
		"DocField",
		filters={"parent": doctype},
		fields=["fieldname"],
		order_by="idx asc",
		pluck="fieldname",
	)
	if not standard:
		return

	order = list(standard)
	for cf in frappe.get_all(
		"Custom Field",
		filters={"dt": doctype},
		fields=["fieldname", "insert_after"],
		order_by="idx asc",
	):
		if cf.fieldname in order:
			continue
		# an anchor we no longer have (or never had) puts the field at the end --
		# never at the front, where a stray break would split the first section
		at = order.index(cf.insert_after) + 1 if cf.insert_after in order else len(order)
		order.insert(at, cf.fieldname)

	frappe.db.set_value("Property Setter", name, "value", json.dumps(order))
	frappe.clear_cache(doctype=doctype)
