"""Give shipments that predate the FCL / LCL field a sensible value.

Only the ones that are already past customs-document preparation, where the
gate would otherwise fire on the next save of a shipment nobody can change any
more. Air shipments become Air; everything with a container becomes FCL.
"""

import frappe


def execute():
	if not frappe.db.has_column("Export Shipment", "shipment_type"):
		return

	rows = frappe.get_all(
		"Export Shipment",
		filters={"shipment_type": ["is", "not set"]},
		fields=["name", "mode", "container_no", "no_of_containers"],
	)
	for row in rows:
		if (row.mode or "").lower().startswith("air"):
			guess = "Air"
		elif row.container_no or row.no_of_containers:
			guess = "FCL"
		else:
			continue
		frappe.db.set_value("Export Shipment", row.name, "shipment_type", guess,
			update_modified=False)

	frappe.db.commit()
