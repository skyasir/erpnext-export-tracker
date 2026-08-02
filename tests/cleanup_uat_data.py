"""Remove the UAT data that ERPNext's internal commits kept alive.

Deliberately conservative: an explicit allow-list of names, nothing date-swept,
and the June / 2026-07-16 baseline records are never referenced.
"""

import frappe

frappe.init(site="supreme.localhost")
frappe.connect()
frappe.set_user("Administrator")
frappe.flags.ignore_links = True

KEEP_SO = {"SAL-ORD-2026-00003", "SAL-ORD-2026-00004"}
KEEP_SI = {"SINV-26-00002", "SINV-26-00003"}
KEEP_SE = {"MAT-STE-00001"}
KEEP_PE = {
	"ACC-PAY-2026-00001", "ACC-PAY-2026-00002", "ACC-PAY-2026-00003",
	"ACC-PAY-2026-00004", "ACC-PAY-2026-00005",
}

TEST_OWNER = "Administrator"   # the tests run as Administrator; nobody else's rows

log = []


def scrub(doctype, names):
	for name in names:
		try:
			doc = frappe.get_doc(doctype, name)
			if doc.docstatus == 1:
				doc.flags.ignore_links = True
				doc.cancel()
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True,
			                  ignore_on_trash=True, delete_permanently=True)
			log.append("deleted  %-18s %s" % (doctype, name))
		except Exception as e:
			log.append("FAILED   %-18s %s -- %s" % (doctype, name, repr(e)[:110]))


# ---------------------------------------------------------------- links first
for dt in ("Sales Order", "Sales Invoice", "Delivery Note"):
	if not frappe.get_meta(dt).get_field("custom_export_shipment"):
		continue
	for name in frappe.get_all(dt, filters={"custom_export_shipment": ["is", "set"]}, pluck="name"):
		frappe.db.set_value(dt, name, "custom_export_shipment", None, update_modified=False)
		log.append("unlinked %-18s %s" % (dt, name))

for name in frappe.get_all("Export Shipment", filters={"export_indent": ["is", "set"]}, pluck="name"):
	frappe.db.set_value("Export Shipment", name, "export_indent", None, update_modified=False)

# ---------------------------------------------------------------- documents
def mine(doctype, keep=()):
	return [
		r.name
		for r in frappe.get_all(doctype, filters={"owner": TEST_OWNER}, fields=["name"])
		if r.name not in keep
	]


scrub("Payment Entry", mine("Payment Entry", KEEP_PE))
scrub("Sales Invoice", mine("Sales Invoice", KEEP_SI))
scrub("Delivery Note", mine("Delivery Note"))
scrub("Stock Entry", mine("Stock Entry", KEEP_SE))
# Only ever remove records the tests themselves created. Real users try the app
# on the same site, and their drafts are not residue -- checking `owner` is the
# difference between cleaning up and destroying someone's work.
scrub("Export Indent",
      frappe.get_all("Export Indent", filters={"owner": TEST_OWNER}, pluck="name"))
scrub("Export Shipment",
      frappe.get_all("Export Shipment", filters={"owner": TEST_OWNER}, pluck="name"))
scrub("Sales Order", mine("Sales Order", KEEP_SO))

# ---------------------------------------------------------------- orphan ledgers
for table, field in (("GL Entry", "voucher_no"), ("Stock Ledger Entry", "voucher_no")):
	rows = frappe.db.sql(
		"select name, voucher_type, {0} as vno from `tab{1}` where creation > '2026-07-30 14:00:00'".format(
			field, table
		),
		as_dict=True,
	)
	for r in rows:
		if not frappe.db.exists(r.voucher_type, r.vno):
			frappe.db.sql("delete from `tab{0}` where name = %s".format(table), r.name)
			log.append("deleted orphan %-12s %s (%s)" % (table, r.name, r.vno))

# ---------------------------------------------------------------- naming series
SERIES_DOCTYPE = {
	"SAL-ORD-2026-": "Sales Order",
	"DN-26-": "Delivery Note",
	"MAT-STE-": "Stock Entry",
	"ACC-PAY-2026-": "Payment Entry",
	"EXP/": "Sales Invoice",
	"EXP-SHP-2026-": "Export Shipment",
	"EXP-IND-2026-": "Export Indent",
}

BASELINE = {
	"SAL-ORD-2026-": 4,
	"DN-26-": 0,
	"MAT-STE-": 1,
	"ACC-PAY-2026-": 5,
	"EXP/": 0,
	"EXP-SHP-2026-": 0,
	"EXP-IND-2026-": 0,
}
def highest_existing(prefix, doctype):
	"""Never rewind a counter below a document that still exists -- a survivor at
	00001 plus a counter at 0 means the next insert collides on the name."""
	rows = frappe.db.sql(
		"select name from `tab{0}` where name like %s".format(doctype), prefix + "%"
	)
	best = 0
	for (name,) in rows:
		tail = name[len(prefix):]
		if tail.isdigit():
			best = max(best, int(tail))
	return best


for prefix, value in BASELINE.items():
	# tabSeries has no `modified` column, so the ORM helpers cannot read it
	row = frappe.db.sql("select current from tabSeries where name = %s", prefix)
	if not row:
		continue
	doctype = SERIES_DOCTYPE.get(prefix)
	if doctype:
		value = max(value, highest_existing(prefix, doctype))
	frappe.db.sql("update tabSeries set current = %s where name = %s", (value, prefix))
	log.append("series   %-16s %s -> %s" % (prefix, row[0][0], value))

frappe.db.commit()

for line in log:
	print(" ", line)

print("\n=== state after cleanup ===")
for dt in ("Sales Order", "Sales Invoice", "Delivery Note", "Stock Entry", "Payment Entry",
           "Export Shipment", "Export Indent"):
	print("  %-18s %d" % (dt, frappe.db.count(dt)))
print("  GL Entry (today)   %d" % frappe.db.count("GL Entry", {"creation": [">", "2026-07-30 14:00:00"]}))
print("  Stock Ledger (today) %d" % frappe.db.count("Stock Ledger Entry", {"creation": [">", "2026-07-30 14:00:00"]}))
print("\n=== survivors (must be exactly the baseline) ===")
for dt in ("Sales Order", "Sales Invoice", "Stock Entry", "Payment Entry"):
	print("  %-16s %s" % (dt, frappe.get_all(dt, pluck="name")))
