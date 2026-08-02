"""Create the Notify Party custom fields on existing installs.

setup_export_defaults already ran on those sites, and a patch only runs once, so
new custom fields need their own entry.
"""

import frappe

from erpnext_export_tracker.install import make_custom_fields


def execute():
	make_custom_fields()
	frappe.db.commit()
