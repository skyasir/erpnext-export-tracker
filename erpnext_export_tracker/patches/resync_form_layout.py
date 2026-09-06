"""Let the app's new tab layout through a site that has customised the form.

Customize Form writes a `field_order` Property Setter, and frappe's meta gives
that property priority over the DocType's own order. On a site where somebody
had opened Customize Form once, that frozen list kept the old single-column
layout and pushed every field this release adds to the bottom -- the tabs came
out in the wrong order with the new sections dangling off the end.

This rebuilds the property setter from the app's order and splices the site's
own custom fields back in after whatever they were anchored to, so the layout
lands without throwing away anyone's customisation.
"""

import json

import frappe

DOCTYPE = "Export Shipment"


def execute():
	name = frappe.db.exists("Property Setter", {"doc_type": DOCTYPE, "property": "field_order"})
	if not name:
		return

	standard = frappe.get_all(
		"DocField",
		filters={"parent": DOCTYPE},
		fields=["fieldname"],
		order_by="idx asc",
		pluck="fieldname",
	)
	if not standard:
		return

	order = list(standard)
	for cf in frappe.get_all(
		"Custom Field",
		filters={"dt": DOCTYPE},
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
	frappe.clear_cache(doctype=DOCTYPE)
	frappe.db.commit()
