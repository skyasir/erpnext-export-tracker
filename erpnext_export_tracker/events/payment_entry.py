import frappe


def on_submit(doc, method=None):
	refresh_linked_shipments(doc)


def on_cancel(doc, method=None):
	refresh_linked_shipments(doc)


def refresh_linked_shipments(doc):
	"""Recompute payment status on any shipment this receipt touches -- the
	bank closure gate depends on it."""
	if doc.payment_type != "Receive" or doc.party_type != "Customer":
		return

	invoices = set()
	orders = set()
	for row in doc.references:
		if row.reference_doctype == "Sales Invoice":
			invoices.add(row.reference_name)
		elif row.reference_doctype == "Sales Order":
			orders.add(row.reference_name)

	names = set()
	for invoice in invoices:
		names.update(
			frappe.get_all("Export Shipment", filters={"sales_invoice": invoice}, pluck="name")
		)
	for order in orders:
		names.update(
			frappe.get_all(
				"Export Shipment",
				filters={"sales_order": order, "docstatus": ["<", 2]},
				pluck="name",
			)
		)

	for name in names:
		shipment = frappe.get_doc("Export Shipment", name)
		shipment.update_payment_status()
		shipment.db_set(
			{
				"invoice_amount": shipment.invoice_amount,
				"total_received": shipment.total_received,
				"outstanding_amount": shipment.outstanding_amount,
				"payment_status": shipment.payment_status,
				"final_payment_date": shipment.final_payment_date,
			},
			update_modified=False,
		)
