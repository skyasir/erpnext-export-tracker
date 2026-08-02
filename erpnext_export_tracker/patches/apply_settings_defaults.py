"""Fill empty Export Tracker Settings fields from their doctype defaults.

A Single is created once. Any field added later keeps its default only for new
records -- of which there are none -- so the existing row stays blank and the
documents that read it print blank. This runs after every migrate-time model
sync, so a newly added default lands without hand-seeding.

Only empty fields are touched; a value a user has set is never overwritten.
"""

import frappe

SKIP = {"Section Break", "Column Break", "Tab Break", "HTML", "Table", "Button"}


def execute():
	settings = frappe.get_single("Export Tracker Settings")
	changed = []

	for df in frappe.get_meta("Export Tracker Settings").fields:
		if df.fieldtype in SKIP or df.default in (None, ""):
			continue
		if settings.get(df.fieldname) in (None, ""):
			settings.set(df.fieldname, df.default)
			changed.append(df.fieldname)

	if changed:
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.db.commit()
		print("Export Tracker Settings: filled %s" % ", ".join(changed))
