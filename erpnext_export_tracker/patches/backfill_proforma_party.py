"""Fill proforma_to / party_name on proformas raised before the party fields.

Every existing Proforma Invoice was necessarily addressed to a Customer, since
that was the only party the document accepted. Point the new fields at it so
the records stay valid and the mandatory party_name is satisfied.
"""

import frappe


def execute():
	if not frappe.db.has_column("Proforma Invoice", "party_name"):
		return

	frappe.db.sql(
		"""
		update `tabProforma Invoice`
		set proforma_to = 'Customer',
		    party_name = customer
		where ifnull(party_name, '') = ''
		  and ifnull(customer, '') != ''
		"""
	)
