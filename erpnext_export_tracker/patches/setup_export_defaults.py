"""Idempotent re-run of the install setup.

Handles existing installs picking up new custom fields, new document templates
or the EXP invoice series without a reinstall.
"""

import frappe

from erpnext_export_tracker.install import (
	add_export_invoice_series,
	make_custom_fields,
	make_document_templates,
	make_workflow,
	make_workflow_masters,
)


def execute():
	make_custom_fields()
	add_export_invoice_series()
	make_workflow_masters()
	make_workflow()
	make_document_templates()
	frappe.db.commit()
