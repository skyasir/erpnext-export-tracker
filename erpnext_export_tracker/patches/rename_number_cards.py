"""Give the control tower's cards the names the workspace references.

The first cut set `name` explicitly, but a Number Card names itself from its
label -- so the cards landed as "Quotations Pending" while the workspace asked
for "Export Quotations Pending", and every counter rendered empty. Renaming also
takes the generic labels out of a site-wide namespace another app may share.
"""

import frappe
from frappe.model.rename_doc import rename_doc

from erpnext_export_tracker.install import NUMBER_CARDS, make_dashboard


def execute():
	for full, *_rest in NUMBER_CARDS:
		short = full.replace("Export ", "")
		if full == short or frappe.db.exists("Number Card", full):
			continue
		if frappe.db.get_value("Number Card", short, "module") != "Export Tracker":
			continue

		# frappe.rename_doc is the whitelisted wrapper and takes a narrower signature
		rename_doc("Number Card", short, full, force=True, ignore_permissions=True,
			show_alert=False)
		frappe.db.set_value("Number Card", full, "label", full)

	# anything the rename could not account for is created fresh
	make_dashboard()
	frappe.db.commit()
