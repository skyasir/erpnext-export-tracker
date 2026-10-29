"""Register the Proforma Invoice as a document we sell on.

ERPNext and India Compliance both decide how to treat a document by matching its
name against lists of selling doctypes. Those lists govern which price list
applies, whether the company address and its GSTIN are fetched onto the
document, which party the tax belongs to, whether GST is worked out per row,
whether a mapping counts as crossing between sales and purchase, and whether an
item may be priced on the document at all.

A document missing from them is treated as a purchase, or refused outright. That
is why GST never computed on a proforma, why its taxes were wiped on the way to
the order, and why picking an item answered "Invalid doctype".

Registration runs from the before_request and before_job hooks, so the lists are
in place for whatever the worker handles next. It cannot rely on the controller
module being imported: pricing and item details are fetched through their own
whitelisted methods, which build no Proforma Invoice and so import no
controller. That is why this worked on a worker that had already saved one and
failed on a fresh one. The controller imports this module too, which covers
`bench console`, tests and anything else running outside a request.

The lists are process-wide, so on a bench where one site has this app and
another does not, both end up patched. That costs nothing: the other site has no
such doctype, so no document can name it and the permission check behind these
lists still refuses.
"""

DOCTYPE = "Proforma Invoice"

# module globals are per process; once patched they stay patched
_registered = False


def register():
	"""Idempotent, and quiet about anything that is not installed."""
	global _registered

	if _registered:
		return

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
		from erpnext.accounts.doctype.pricing_rule import pricing_rule

		# Who may call the pricing engine. It also gates get_item_details, so
		# without this a user cannot even pick an item -- they get a bare
		# "Invalid doctype". Unlike the others it is a frozenset, so it is
		# rebound rather than added to; nothing else imports the name, and
		# validate_pricing_context reads it off the module on each call, so the
		# new value is the one that counts. getattr because older erpnext
		# releases do not have the guard at all.
		allowed = getattr(pricing_rule, "PRICING_TRANSACTION_DOCTYPES", None)
		if allowed is not None and DOCTYPE not in allowed:
			pricing_rule.PRICING_TRANSACTION_DOCTYPES = allowed | {DOCTYPE}
	except ImportError:
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

	_registered = True
