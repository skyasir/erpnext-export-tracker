"""Bring an already-installed site up to the SOP revision: country profiles,
the control tower cards, and the stage chart.

Everything it calls is idempotent -- an existing profile or card is left alone,
so re-running the patch never overwrites what the export desk has edited.
"""

import frappe

from erpnext_export_tracker.install import make_country_profiles, make_dashboard


def execute():
	make_country_profiles()
	make_dashboard()
	frappe.db.commit()
