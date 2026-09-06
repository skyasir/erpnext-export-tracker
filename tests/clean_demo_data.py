"""Remove everything the Export Tracker walkthrough created.

Only touches records tied to the three demo customers, in dependency order.
Nothing is matched by date, so real work on the same site is never at risk.
"""

import frappe

frappe.init(site="supreme.localhost")
frappe.connect()
frappe.set_user("Administrator")

LABELS = ["Demo Buyer Nigeria (Export Tracker)", "Demo Buyer Uganda (Export Tracker)",
          "Demo Buyer Malawi (Export Tracker)"]
customers = [frappe.db.get_value("Customer", {"customer_name": l}, "name") for l in LABELS]
customers = [c for c in customers if c]
print("demo customers:", customers)
if not customers:
	raise SystemExit("nothing to clean")


def drop(doctype, filters, label=None):
	names = frappe.get_all(doctype, filters=filters, pluck="name")
	for name in names:
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			try:
				doc.cancel()
			except Exception as e:
				print("   cancel failed %s %s: %s" % (doctype, name, str(e)[:70]))
		frappe.delete_doc(doctype, name, force=1, ignore_permissions=True,
		                  ignore_missing=True, delete_permanently=True)
	if names:
		print("  %-18s removed %d %s" % (doctype, len(names), names))
	return names


shipments = frappe.get_all("Export Shipment", filters={"customer": ["in", customers]},
                           pluck="name")
invoices = frappe.get_all("Sales Invoice", filters={"customer": ["in", customers]}, pluck="name")

drop("Payment Entry", {"party": ["in", customers], "party_type": "Customer"})
for si in invoices:
	drop("Sales Invoice", {"name": si})
drop("Delivery Note", {"customer": ["in", customers]})
drop("Export Shipment", {"customer": ["in", customers]})
drop("Export Indent", {"customer": ["in", customers]})
drop("Sales Order", {"customer": ["in", customers]})
drop("Address", {"address_title": ["in", LABELS]})
for c in customers:
	drop("Customer", {"name": c})

frappe.db.commit()
print("clean")
