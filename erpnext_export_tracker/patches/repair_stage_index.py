"""Re-align stage_index with status on every shipment.

Unlike backfill_stage_index (which ran once when the field was introduced), this
repairs drift -- most importantly rows saved by a worker running code from before
the field was set in validate(). A stale index hides the section a gate demands.
"""

import frappe

from erpnext_export_tracker.export_tracker.doctype.export_shipment.export_shipment import (
	STATE_ORDER,
)


def execute():
	fixed = 0
	for index, status in enumerate(STATE_ORDER):
		rows = frappe.get_all(
			"Export Shipment",
			filters={"status": status, "stage_index": ["!=", index]},
			pluck="name",
		)
		for name in rows:
			frappe.db.set_value("Export Shipment", name, "stage_index", index,
			                    update_modified=False)
			fixed += 1

	if fixed:
		frappe.db.commit()
		print("repair_stage_index: realigned %d shipment(s)" % fixed)
