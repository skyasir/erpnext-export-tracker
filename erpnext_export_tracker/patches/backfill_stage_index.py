"""Backfill stage_index on shipments created before it existed.

Section visibility is driven by this field, so a shipment left at 0 would hide
the sections its own status has already passed.
"""

import frappe

from erpnext_export_tracker.export_tracker.doctype.export_shipment.export_shipment import (
	STATE_ORDER,
)


def execute():
	for index, status in enumerate(STATE_ORDER):
		frappe.db.set_value(
			"Export Shipment",
			{"status": status},
			"stage_index",
			index,
			update_modified=False,
		)
