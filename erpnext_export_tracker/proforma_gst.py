"""Give the Proforma Invoice the GST handling India Compliance gives a Sales Order.

India Compliance hooks its GST handling onto doctypes by name, so a doctype it
has never heard of gets none. A Proforma Invoice is a Sales Order that has not
been agreed yet, so for each event below it runs whatever India Compliance has
registered for the Sales Order.

The handlers are looked up from India Compliance's own hooks at run time instead
of being named here. Its handler names change between releases (16.11.1 dropped
`transaction.onload` and `transaction.before_print` for a resolver hook), and a
hook naming a function that no longer exists fails every form load.

On a site without India Compliance nothing is registered for the Sales Order
under its name, so each event does nothing.
"""

import frappe

MIRRORED_DOCTYPE = "Sales Order"
IC_PREFIX = "india_compliance."


def _ic_handlers(event):
	handlers = frappe.get_doc_hooks().get(MIRRORED_DOCTYPE, {}).get(event, [])
	return [h for h in handlers if h.startswith(IC_PREFIX)]


def _run(event, doc, method, *args, **kwargs):
	for handler in _ic_handlers(event):
		frappe.get_attr(handler)(doc, method, *args, **kwargs)


def onload(doc, method=None, *args, **kwargs):
	_run("onload", doc, method, *args, **kwargs)


def before_print(doc, method=None, *args, **kwargs):
	_run("before_print", doc, method, *args, **kwargs)


def before_validate(doc, method=None, *args, **kwargs):
	_run("before_validate", doc, method, *args, **kwargs)


def validate(doc, method=None, *args, **kwargs):
	_run("validate", doc, method, *args, **kwargs)


def before_update_after_submit(doc, method=None, *args, **kwargs):
	_run("before_update_after_submit", doc, method, *args, **kwargs)


def after_mapping(doc, method=None, *args, **kwargs):
	_run("after_mapping", doc, method, *args, **kwargs)


def resolve_virtual_fields(doc):
	"""India Compliance 16.11.1+ fills its virtual fields (the GST breakup table,
	e-commerce supply type) through `ic_virtual_field_resolvers`, keyed by doctype.
	Run the Sales Order's resolvers for the proforma."""
	values = {}
	for resolver in frappe.get_hooks("ic_virtual_field_resolvers").get(MIRRORED_DOCTYPE, []):
		values.update(frappe.get_attr(resolver)(doc))
	return values
