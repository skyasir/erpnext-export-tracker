"""Apply the shipment module revision to a site that already has the app.

Field definitions and form layout re-assert themselves on every migrate, so all
this has to do is the one-way data moves the doctype change cannot make on its
own: carry the shipment's FOB value onto its invoice before the field goes, and
seed the payments table from the XAR each shipment already holds.
"""

import frappe

from erpnext_export_tracker.install import make_custom_fields


def execute():
	# patches run before after_migrate, so the invoice's FOB field does not exist
	# yet unless this asks for it
	make_custom_fields()
	carry_fob_value_to_invoice()
	seed_payments_from_shipment_xar()
	frappe.db.commit()


def carry_fob_value_to_invoice():
	"""FOB value moved from the shipment to the invoice -- take the data with it."""
	if not (frappe.db.has_column("Export Shipment", "fob_value")
	        and frappe.db.has_column("Sales Invoice", "custom_fob_value")):
		return

	rows = frappe.db.sql(
		"""select name, sales_invoice, fob_value from `tabExport Shipment`
		   where ifnull(fob_value, 0) != 0 and ifnull(sales_invoice, '') != ''""",
		as_dict=True,
	)
	for row in rows:
		if not frappe.db.get_value("Sales Invoice", row.sales_invoice, "custom_fob_value"):
			frappe.db.set_value("Sales Invoice", row.sales_invoice, "custom_fob_value",
			                    row.fob_value, update_modified=False)


def seed_payments_from_shipment_xar():
	"""An XAR already recorded against a shipment becomes its first payment row,
	so nothing that was captured before the table existed is lost from view."""
	if not frappe.db.table_exists("Export Shipment Payment"):
		return

	shipments = frappe.db.sql(
		"""select name, xar_no, xar_date, currency, final_payment_date, total_received
		   from `tabExport Shipment` where ifnull(xar_no, '') != ''""",
		as_dict=True,
	)
	for row in shipments:
		if frappe.db.exists("Export Shipment Payment", {"parent": row.name}):
			continue

		# inserted straight into the child table rather than saved through the
		# parent: re-validating a historical shipment would run today's gates over
		# a document closed months ago, and one of them refuses a shipment whose
		# invoice has since been cancelled
		frappe.get_doc({
			"doctype": "Export Shipment Payment",
			"parent": row.name,
			"parenttype": "Export Shipment",
			"parentfield": "payments",
			"idx": 1,
			"payment_date": row.final_payment_date or row.xar_date,
			"amount": row.total_received,
			"currency": row.currency,
			"payment_type": "Against Invoice",
			"xar_no": row.xar_no,
			"xar_date": row.xar_date,
			"remarks": "Carried over from the shipment's own XAR",
		}).insert(ignore_permissions=True)
