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

It runs on every migrate, not once: a property setter written before a release
freezes *that* release's layout, so a one-time patch fixes the site it ran on and
then quietly breaks again the next time the app moves a field. The cost is that a
deliberate reordering done in Customize Form does not survive a migrate -- the
app owns the arrangement, the site owns the fields.
"""

import json

import frappe

MODULE = "Export Tracker"

# doctypes we only add custom fields to -- the form belongs to ERPNext, so only
# our own fields are repositioned there, never anybody else's
HOSTS = ("Quotation", "Sales Order", "Sales Invoice", "Delivery Note")


def execute():
	resync_all()


def resync_all():
	for doctype in frappe.get_all("DocType", filters={"module": MODULE}, pluck="name"):
		resync(doctype)

	for doctype in HOSTS:
		if frappe.db.exists("DocType", doctype):
			reposition(doctype)

	frappe.db.commit()


def reposition(doctype):
	"""Put our custom fields where their `insert_after` says, inside somebody
	else's field_order.

	Same property setter, different remedy: on a host doctype we have no business
	rewriting the whole order, so our fields are lifted out and threaded back in
	along their anchor chain. Everything else keeps the position it had.

	Without this an Export Details tab anchored at the end of the form arrives
	empty, because the frozen order still holds its sections halfway up the form.
	"""
	name = frappe.db.exists("Property Setter", {"doc_type": doctype, "property": "field_order"})
	if not name:
		return

	try:
		order = json.loads(frappe.db.get_value("Property Setter", name, "value") or "[]")
	except ValueError:
		return

	ours = {
		f.fieldname: f.insert_after
		for f in frappe.get_all("Custom Field", filters={"dt": doctype, "module": MODULE},
		                        fields=["fieldname", "insert_after"])
	}
	if not ours:
		return

	rest = [f for f in order if f not in ours]
	pending = dict(ours)

	# thread each field in after its anchor; an anchor that is itself one of ours
	# only becomes available once that one is placed, so loop until stuck
	placed = True
	while pending and placed:
		placed = False
		for fieldname, anchor in list(pending.items()):
			if anchor in rest:
				rest.insert(rest.index(anchor) + 1, fieldname)
				del pending[fieldname]
				placed = True

	rest += list(pending)   # an anchor that no longer exists -- park it at the end

	if rest != order:
		frappe.db.set_value("Property Setter", name, "value", json.dumps(rest))
		frappe.clear_cache(doctype=doctype)


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
