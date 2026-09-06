"""Drop the export-only proforma in favour of one that also serves domestic work.

The first cut shipped as "Export Proforma Invoice" with its own item table. A
proforma is a proforma whether the goods leave the country or not, so the
document is now "Proforma Invoice", export is a checkbox on it, and it uses the
Sales Order's own item and tax tables -- which is what makes raising the order a
straight copy.

Nothing had been recorded against the old doctype, so it is removed rather than
renamed; the guard makes sure of that before deleting anything. The Sales Order
print format of the same name goes too: it printed a proforma from an order,
which is the job this document now does.
"""

import frappe

OLD_DOCTYPE = "Export Proforma Invoice"
OLD_PRINT_FORMAT = "Export Proforma Invoice"


def execute():
	drop_old_print_format()
	drop_old_doctype()
	frappe.db.commit()


def drop_old_print_format():
	if frappe.db.exists("Print Format", OLD_PRINT_FORMAT):
		frappe.delete_doc("Print Format", OLD_PRINT_FORMAT, force=1,
		                  ignore_permissions=True, delete_permanently=True)


def drop_old_doctype():
	if not frappe.db.exists("DocType", OLD_DOCTYPE):
		return

	# a site that somehow recorded against it keeps the table; nothing is thrown
	# away silently
	if frappe.db.count(OLD_DOCTYPE):
		frappe.log_error(
			title="Export Proforma Invoice kept",
			message="Not removed: %d record(s) exist. Move them to Proforma Invoice by "
			        "hand, then delete the doctype." % frappe.db.count(OLD_DOCTYPE),
		)
		return

	frappe.delete_doc("DocType", OLD_DOCTYPE, force=1, ignore_permissions=True,
	                  delete_permanently=True)
