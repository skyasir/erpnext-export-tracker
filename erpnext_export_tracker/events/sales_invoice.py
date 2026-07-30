import frappe


def on_submit(doc, method=None):
	"""Link the export invoice back to its shipment and carry the shipping
	bill / carriage details onto it."""
	if not doc.get("custom_is_export"):
		return

	shipment_name = doc.get("custom_export_shipment") or find_shipment_from_orders(doc)
	if not shipment_name:
		return

	if not doc.get("custom_export_shipment"):
		doc.db_set("custom_export_shipment", shipment_name, update_modified=False)

	shipment = frappe.get_doc("Export Shipment", shipment_name)

	updates = {
		"sales_invoice": doc.name,
		"currency": doc.currency,
		"invoice_amount": doc.grand_total,
		"outstanding_amount": doc.outstanding_amount,
		"total_received": (doc.grand_total or 0) - (doc.outstanding_amount or 0),
	}

	# india_compliance / standard fields on the invoice win, they are the filed values
	for source, target in (
		("shipping_bill_number", "shipping_bill_no"),
		("shipping_bill_date", "shipping_bill_date"),
		("port_code", "port_code"),
		("custom_pre_carriage_by", "pre_carriage_by"),
		("custom_place_of_receipt", "place_of_receipt"),
		("custom_port_of_loading", "port_of_loading"),
		("custom_vessel_flight_no", "vessel_flight_no"),
		("custom_port_of_discharge", "port_of_discharge"),
		("custom_final_destination", "final_destination"),
		("custom_country_of_origin", "country_of_origin"),
		("custom_country_of_final_destination", "country_of_final_destination"),
		("custom_container_no", "container_no"),
		("custom_net_weight", "net_weight"),
		("custom_gross_weight", "gross_weight"),
		("custom_no_of_packages", "no_of_packages"),
		("custom_terms_of_payment", "terms_of_payment"),
	):
		value = doc.get(source)
		if value and not shipment.get(target):
			updates[target] = value

	shipment.db_set(updates, update_modified=False)
	shipment.reload()
	shipment.update_payment_status()
	shipment.db_set(
		{
			"payment_status": shipment.payment_status,
			"final_payment_date": shipment.final_payment_date,
		},
		update_modified=False,
	)


def on_cancel(doc, method=None):
	if not doc.get("custom_is_export"):
		return

	for name in frappe.get_all(
		"Export Shipment", filters={"sales_invoice": doc.name}, pluck="name"
	):
		frappe.db.set_value("Export Shipment", name, "sales_invoice", None, update_modified=False)


def find_shipment_from_orders(doc):
	"""Fall back to the shipment of the order(s) this invoice bills."""
	orders = {row.sales_order for row in doc.items if row.get("sales_order")}
	for order in orders:
		name = frappe.db.get_value(
			"Export Shipment",
			{"sales_order": order, "docstatus": ["<", 2], "sales_invoice": ["in", ["", None]]},
			"name",
		)
		if name:
			return name
	return None
