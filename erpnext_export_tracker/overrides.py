"""Thin overrides of ERPNext entry points, kept to the minimum that is necessary.

Each one delegates to ERPNext immediately after a single adjustment, so there is
no forked behaviour to keep in step with an upgrade.
"""

import frappe

from erpnext.stock.get_item_details import get_item_details as erpnext_get_item_details

# Documents of ours that borrow another doctype's item table, and the doctype
# whose table they borrow.
BORROWED_ITEM_TABLE = {"Proforma Invoice": "Sales Order"}


@frappe.whitelist()
def get_item_details(ctx, doc=None, for_validate=False, overwrite_warehouse=True):
	"""Fetch item details for a document that shares another's item table.

	ERPNext works out which item doctype to read from by appending " Item" to the
	parent's name, ignoring the `child_doctype` it is already holding. A Proforma
	Invoice uses Sales Order Item, so that lookup asks for a "Proforma Invoice
	Item" that does not exist and the form reports "not found" on every item you
	pick.

	Swapping the name for the length of the call is enough: the two documents
	have the same item table, the same tax table and the same totals, so every
	rate, pricing rule and item default that follows is the one an order would
	have got.
	"""
	borrowed = BORROWED_ITEM_TABLE.get(
		ctx.get("doctype") if hasattr(ctx, "get") else None
	)
	if borrowed:
		ctx["doctype"] = borrowed

	return erpnext_get_item_details(
		ctx, doc, for_validate=for_validate, overwrite_warehouse=overwrite_warehouse
	)
