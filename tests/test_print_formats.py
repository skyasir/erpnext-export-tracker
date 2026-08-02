"""Every Export Tracker print format must actually be printable.

Catches two failure modes that both surface in the UI as "No Preview Available"
and neither of which any other test noticed:

1. A stale Print Format record whose template file no longer exists -- e.g. after
   renaming a format, since the rename creates a new record and leaves the old.
2. A format whose doc_type in the database has drifted from the JSON. Frappe skips
   re-importing a standard fixture when its `modified` timestamp is unchanged, so
   editing the JSON alone does nothing; the timestamp must be bumped.
"""

import os

import frappe

PASS, FAIL = [], []


def check(label, cond, detail=""):
	(PASS if cond else FAIL).append(label)
	print("%s  %s%s" % ("PASS" if cond else "FAIL", label, (" -- " + str(detail)) if detail else ""))


frappe.init(site="supreme.localhost")
frappe.connect()
frappe.set_user("Administrator")

APP = frappe.get_app_path("erpnext_export_tracker")
BASE = os.path.join(APP, "export_tracker", "print_format")

formats = frappe.get_all(
	"Print Format", filters={"module": "Export Tracker"}, fields=["name", "doc_type", "standard"]
)
check("print formats are registered", len(formats) > 0, "%d found" % len(formats))

print("\n=== every format resolves to a template on disk ===")
for f in formats:
	slug = frappe.scrub(f.name)
	path = os.path.join(BASE, slug, slug + ".html")
	check("%-34s -> %s.html" % (f.name, slug), os.path.exists(path),
	      "" if os.path.exists(path) else "MISSING -- stale record or renamed format")

print("\n=== every template on disk is registered ===")
on_disk = {
	d for d in os.listdir(BASE)
	if os.path.isdir(os.path.join(BASE, d)) and os.path.exists(os.path.join(BASE, d, d + ".html"))
}
registered = {frappe.scrub(f.name) for f in formats}
for slug in sorted(on_disk - registered):
	check("template %s is registered" % slug, False, "no Print Format record points at it")
if not (on_disk - registered):
	check("no orphan templates", True, "%d templates, all registered" % len(on_disk))

print("\n=== doc_type in the database matches the JSON fixture ===")
for f in formats:
	slug = frappe.scrub(f.name)
	import json
	jpath = os.path.join(BASE, slug, slug + ".json")
	if not os.path.exists(jpath):
		continue
	declared = json.load(open(jpath))["doc_type"]
	check("%-34s doc_type %s" % (f.name, f.doc_type), f.doc_type == declared,
	      "" if f.doc_type == declared else "JSON says %s -- bump `modified` in the fixture" % declared)

print("\n=== each format renders against its own doc_type ===")
for f in formats:
	sample = frappe.db.get_value(f.doc_type, {}, "name")
	if not sample:
		check("renders: %s" % f.name, True, "no %s on this site to sample" % f.doc_type)
		continue
	try:
		html = frappe.get_print(f.doc_type, sample, print_format=f.name)
		check("renders: %s" % f.name, len(html) > 200, "%d chars on %s" % (len(html), sample))
	except Exception as e:
		check("renders: %s" % f.name, False, repr(e)[:150])

print("\n" + "=" * 62)
print("PASSED: %d    FAILED: %d" % (len(PASS), len(FAIL)))
for x in FAIL:
	print("  -", x)
print("=" * 62)
frappe.db.rollback()
