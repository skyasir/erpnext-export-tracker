"""Keep a control tower card's label, its name and the workspace row in step.

A Number Card takes its name from its label at insert, and the workspace resolves
each card by that same string in its own child row. Shortening the label for
looks unlinks nothing on its own -- the workspace row is the key -- but it leaves
three names for one card, and the next person to touch it has to work out which
one matters. They are all "Export ..." again; the cards are laid out three to a
row instead, which is what stopped the titles truncating.
"""

import frappe

from erpnext_export_tracker.install import make_dashboard


def execute():
	make_dashboard()
	frappe.db.commit()
