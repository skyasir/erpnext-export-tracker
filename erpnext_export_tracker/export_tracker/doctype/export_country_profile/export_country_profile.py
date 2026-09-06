import frappe
from frappe.model.document import Document


class ExportCountryProfile(Document):
	pass


def get_profile(country):
	"""The compliance rules for a destination, or None when nobody has set any up.

	Callers treat a missing profile as "no special requirements" -- a destination
	the export desk has not configured must never block a shipment.
	"""
	if not country:
		return None

	name = frappe.db.get_value("Export Country Profile", {"country": country, "disabled": 0})
	if not name:
		return None

	return frappe.get_cached_doc("Export Country Profile", name)
