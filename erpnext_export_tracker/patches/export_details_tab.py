"""Move the export fields out of a collapsible section and into their own tab.

They were a collapsible "Export Details" section wedged into the middle of the
Sales Order / Sales Invoice / Quotation form. Fifteen fields deep, that reads as
clutter on a domestic order and as a scavenger hunt on an export one. They are a
tab now, anchored at the end of the form and shown only once Is Export is ticked.
"""

import frappe

from erpnext_export_tracker.install import make_custom_fields


def execute():
	make_custom_fields()
	for doctype in ("Quotation", "Sales Order", "Sales Invoice"):
		frappe.clear_cache(doctype=doctype)
	frappe.db.commit()
