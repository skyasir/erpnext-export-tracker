"""Register the Proforma Invoice as a document we sell on.

ERPNext and India Compliance both decide how to treat a document by matching its
name against lists of selling doctypes. Those lists govern which price list
applies, whether the company address and its GSTIN are fetched onto the
document, which party the tax belongs to, whether GST is worked out per row, and
whether a mapping counts as crossing between sales and purchase.

A document missing from them is treated as a purchase. That is why GST never
computed on a proforma, and why its taxes were wiped on the way to the order.

Every list is a mutable container shared by everyone who imported it, so adding
to the object itself takes effect whatever the import order was.

Called when the Proforma Invoice controller module is imported, which is the one
moment that is guaranteed: frappe loads the controller to build the document, so
anything that goes on to read these lists has already triggered it. An app-load
hook would be tidier but does not exist -- frappe serves hooks from cache and
may never import the app package at all.
"""

DOCTYPE = "Proforma Invoice"


def register():
	"""Idempotent, and quiet about anything that is not installed."""
	try:
		from erpnext.stock.get_item_details import sales_doctypes

		if DOCTYPE not in sales_doctypes:
			sales_doctypes.append(DOCTYPE)
	except ImportError:
		pass

	try:
		from erpnext.accounts import party

		# TRANSACTION_TYPES is a union built at import, so it is its own set and
		# has to be told separately
		party.SALES_TRANSACTION_TYPES.add(DOCTYPE)
		party.TRANSACTION_TYPES.add(DOCTYPE)
	except (ImportError, AttributeError):
		pass

	try:
		from india_compliance.gst_india.constants import SALES_DOCTYPES
		from india_compliance.gst_india.overrides import transaction

		SALES_DOCTYPES.add(DOCTYPE)
		# the second list is what decides whether each row gets its taxable value
		# and its CGST/SGST/IGST rate worked out, which the GST reports read
		transaction.DOCTYPES_WITH_GST_DETAIL.add(DOCTYPE)
	except ImportError:
		# a site without India Compliance simply has no GST to apply
		pass
