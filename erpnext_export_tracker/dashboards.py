"""Show the proforma in the Connections of the documents either side of it.

Quotation -> Proforma Invoice -> Sales Order. Neither erpnext doctype knows the
proforma exists, and their `links` live in erpnext's own JSON, which a migrate
would overwrite. Extending the dashboard through this hook leaves erpnext alone.
"""

DOCTYPE = "Proforma Invoice"


def quotation_dashboard(data=None):
	"""Proformas raised from a quotation -- they carry its `quotation` field."""
	return add_link(data, fieldname="quotation", label="Selling")


def sales_order_dashboard(data=None):
	"""The proforma an order came from -- it carries the order in `sales_order`."""
	return add_link(data, fieldname="sales_order", label="Selling")


def add_link(data, fieldname, label):
	data = data or {}
	data.setdefault("transactions", [])
	data.setdefault("non_standard_fieldnames", {})

	# the proforma points at the other document, so the link is not on the
	# standard <doctype>_name field and has to be named
	data["non_standard_fieldnames"][DOCTYPE] = fieldname

	for group in data["transactions"]:
		if group.get("label") == label:
			if DOCTYPE not in group["items"]:
				group["items"].append(DOCTYPE)
			return data

	data["transactions"].append({"label": label, "items": [DOCTYPE]})
	return data
