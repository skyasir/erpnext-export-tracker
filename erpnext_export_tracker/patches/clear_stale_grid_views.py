"""Let the app's grid column design take effect again.

Configuring a child-table grid in the desk saves a per-user `GridView` entry in
__UserSettings, and that entry completely overrides the doctype's `in_list_view`
and `columns`. On this site the saved layout for Export CHA Quote asked for seven
columns totalling fourteen units against a ten-unit grid, so every column was
squeezed and the headers truncated -- and no amount of editing the doctype could
change what the user saw.

Dropping the entry restores the shipped layout. It holds no data, only which
columns that user last had on screen, and anyone who wants their own arrangement
back can set it again from the grid's settings button.
"""

import json

import frappe

MODULE = "Export Tracker"


def execute():
	tables = set(
		frappe.get_all(
			"DocType", filters={"module": MODULE, "istable": 1}, pluck="name"
		)
	)
	if not tables:
		return

	for row in frappe.db.sql("select user, doctype, data from __UserSettings", as_dict=True):
		try:
			settings = json.loads(row.data or "{}")
		except (TypeError, ValueError):
			continue

		grid_view = settings.get("GridView") or {}
		stale = [name for name in grid_view if name in tables]
		if not stale:
			continue

		for name in stale:
			grid_view.pop(name)
		settings["GridView"] = grid_view

		frappe.db.sql(
			"update __UserSettings set data = %s where user = %s and doctype = %s",
			(json.dumps(settings), row.user, row.doctype),
		)

	frappe.cache.delete_keys("_user_settings")
	frappe.db.commit()
