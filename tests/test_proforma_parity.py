"""A Proforma Invoice is a Sales Order that has not been agreed yet.

Rather than assert figures by hand, this builds the same document both ways and
insists they come out the same -- items, taxes, GST, totals -- for an intra-state
sale, an inter-state one and an export. Parity by construction: if ERPNext or
India Compliance changes how an order behaves, the proforma has to follow or
this fails.

Runs in a transaction and rolls back.
"""

import frappe
from frappe.utils import add_days, today

frappe.init(site="supreme.localhost")
frappe.connect()
frappe.set_user("Administrator")

PASS, FAIL = [], []


def check(label, cond, detail=""):
	(PASS if cond else FAIL).append(label)
	print("%s  %s%s" % ("PASS" if cond else "FAIL", label, (" -- " + str(detail)) if detail else ""))


COMPANY = frappe.db.get_value("Company", {}, "name")
ITEM = frappe.db.get_value("Item", {"disabled": 0, "is_sales_item": 1,
                                    "has_variants": 0, "is_stock_item": 1}, "name")
WAREHOUSE = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 0,
                                              "disabled": 0}, "name")
company_state = (frappe.db.get_value("Address", {"is_your_company_address": 1}, "gst_state_number")
                 or "27")


def customer_in(where):
	"""A live customer whose address puts them in / out of our own state."""
	rows = frappe.db.sql("""
		select c.name, a.gst_state_number, a.gstin
		from `tabCustomer` c
		join `tabDynamic Link` dl on dl.link_name = c.name and dl.link_doctype = 'Customer'
		join `tabAddress` a on a.name = dl.parent
		where c.disabled = 0 and ifnull(a.gstin, '') != ''
		  and a.gst_state_number %s %%s
		limit 1""" % ("=" if where == "same" else "!="), company_state, as_dict=True)
	return rows[0].name if rows else None


def overseas_customer():
	rows = frappe.db.sql("""
		select c.name from `tabCustomer` c
		join `tabDynamic Link` dl on dl.link_name = c.name and dl.link_doctype = 'Customer'
		join `tabAddress` a on a.name = dl.parent
		where c.disabled = 0 and ifnull(a.country, '') not in ('', 'India')
		limit 1""", as_dict=True)
	return rows[0].name if rows else None


def party_currency(customer):
	"""An overseas buyer's receivable account is in their currency, and a
	document in any other is refused outright."""
	from erpnext.accounts.party import get_party_account_currency

	return (get_party_account_currency("Customer", customer, COMPANY)
	        or frappe.db.get_value("Company", COMPANY, "default_currency"))


def build(doctype, customer, export=False):
	d = frappe.new_doc(doctype)
	d.customer = customer
	d.company = COMPANY
	d.transaction_date = today()
	currency = party_currency(customer)
	if currency != frappe.db.get_value("Company", COMPANY, "default_currency"):
		d.currency = currency
		d.conversion_rate = 90
	if doctype == "Sales Order":
		d.delivery_date = add_days(today(), 30)
	else:
		d.is_export = 1 if export else 0
		if export:
			d.consignee_name = "DEMO CONSIGNEE"
	d.append("items", {"item_code": ITEM, "qty": 10, "rate": 100,
	                   "delivery_date": add_days(today(), 30), "warehouse": WAREHOUSE})
	d.insert()
	return d


SHAPE = lambda d: {
	"gst_category": d.get("gst_category"),
	"place_of_supply": d.get("place_of_supply"),
	"company_gstin": d.get("company_gstin"),
	"billing_address_gstin": d.get("billing_address_gstin"),
	"taxes_and_charges": d.get("taxes_and_charges"),
	"taxes": sorted((t.account_head, t.rate, t.tax_amount) for t in d.taxes),
	"net_total": d.net_total,
	"total_taxes_and_charges": d.total_taxes_and_charges,
	"grand_total": d.grand_total,
	"rounded_total": d.rounded_total,
	"items": [(i.item_code, i.qty, i.rate, i.amount, i.gst_hsn_code, i.gst_treatment,
	           i.igst_rate, i.cgst_rate, i.sgst_rate, i.taxable_value) for i in d.items],
}

print("=== 1. structure ===")
pi = frappe.get_meta("Proforma Invoice")
check("the proforma has its own item table",
      pi.get_field("items").options == "Proforma Invoice Item",
      pi.get_field("items").options)
check("no proforma row is left in the order's table",
      frappe.db.sql("select count(*) from `tabSales Order Item` "
                    "where parenttype = 'Proforma Invoice'")[0][0] == 0)

import json  # noqa: E402
import os  # noqa: E402

ERPNEXT_SOI = os.path.join(os.path.dirname(frappe.get_app_path("erpnext")), "erpnext",
                           "selling", "doctype", "sales_order_item",
                           "sales_order_item.json")
standard = {f["fieldname"] for f in json.load(open(ERPNEXT_SOI))["fields"]}
pii = {f.fieldname for f in frappe.get_meta("Proforma Invoice Item").fields}
missing = sorted(standard - pii)
check("every standard Sales Order Item field is on ours", not missing, missing[:8] or "none")

# anything else on the order's table came from another app or from Customize
# Form on this site; ours does not claim ownership of those
site_only = sorted({f.fieldname for f in frappe.get_meta("Sales Order Item").fields}
                   - standard - pii)
print("     note: site-specific fields on Sales Order Item, not mirrored: %s"
      % (site_only or "none"))

# ERPNext and India Compliance decide how to treat a document from lists of
# selling doctypes. Building a proforma is what puts ours in them -- frappe has
# to load the controller to make the document, and that is the registration.
from erpnext.accounts import party  # noqa: E402
from erpnext.stock.get_item_details import sales_doctypes  # noqa: E402

frappe.new_doc("Proforma Invoice")

check("registered as a selling doctype", "Proforma Invoice" in sales_doctypes)
check("registered as a sales transaction", "Proforma Invoice" in party.SALES_TRANSACTION_TYPES)
try:
	from india_compliance.gst_india.constants import SALES_DOCTYPES
	from india_compliance.gst_india.overrides import transaction

	check("registered with India Compliance", "Proforma Invoice" in SALES_DOCTYPES)
	check("registered for item-wise GST",
	      "Proforma Invoice" in transaction.DOCTYPES_WITH_GST_DETAIL)
except ImportError:
	check("India Compliance present", False, "not installed")

# India Compliance positions its GST fields with insert_after against the Sales
# Order's own sections. Hand-picking a layout left those anchors with nothing to
# attach to, so the fields scattered -- "Is Export With Payment of GST" ended up
# under Additional Info instead of beside the customer. The proforma carries the
# order's whole structure now; this fails if that drifts.
print("\n=== 1b. the form is laid out like an order ===")


def inside_of(tab_fieldname):
	"""Fields that render under a given tab."""
	out, seen = [], False
	for df in frappe.get_meta("Proforma Invoice").fields:
		if df.fieldtype == "Tab Break":
			if seen:
				break
			seen = df.fieldname == tab_fieldname
			continue
		if seen and df.fieldtype not in ("Column Break", "Section Break"):
			out.append(df.fieldname)
	return out


def layout(doctype):
	"""Which section each visible field sits in."""
	placement, section = {}, None
	for df in frappe.get_meta(doctype).fields:
		if df.fieldtype == "Tab Break":
			section = "TAB:" + (df.label or df.fieldname)
		elif df.fieldtype == "Section Break":
			section = "SEC:" + (df.label or df.fieldname)
		elif df.fieldtype != "Column Break" and not df.hidden:
			placement[df.fieldname] = section
	return placement


order_layout, proforma_layout = layout("Sales Order"), layout("Proforma Invoice")
shared = set(order_layout) & set(proforma_layout)
misplaced = sorted(fn for fn in shared if order_layout[fn] != proforma_layout[fn])
check("shares most of the order's fields", len(shared) > 90, "%d shared" % len(shared))
check("every shared field sits in the same section", not misplaced,
      [(fn, order_layout[fn], proforma_layout[fn]) for fn in misplaced[:5]] or "none")

for fieldname, where in (("place_of_supply", "SEC:Billing Address"),
                         ("billing_address_gstin", "SEC:Billing Address"),
                         ("company_gstin", "SEC:Company Address"),
                         ("tax_category", "SEC:Taxes"),
                         ("is_export_with_gst", "SEC:customer_section")):
	check("%-22s sits where the order puts it" % fieldname,
	      proforma_layout.get(fieldname) == where,
	      "%s (order: %s)" % (proforma_layout.get(fieldname), order_layout.get(fieldname)))

# a tab whose fields ended up outside it renders empty and the block looks lost
print()
for df in frappe.get_meta("Proforma Invoice").fields:
	if df.fieldtype != "Tab Break":
		continue
	inside, seen = [], False
	for other in frappe.get_meta("Proforma Invoice").fields:
		if other.fieldtype == "Tab Break":
			if seen:
				break
			seen = other.fieldname == df.fieldname
			continue
		if seen and other.fieldtype not in ("Column Break", "Section Break"):
			inside.append(other.fieldname)
	check("tab %-18s holds its fields" % (df.label or df.fieldname), bool(inside),
	      "%d fields" % len(inside))

check("the export block is all on the export tab",
      {"consignee_name", "shipment_type", "fob_value", "goods_description"}
      <= set(inside_of("tab_export")),
      sorted(inside_of("tab_export"))[:6])

# the order's tabs, plus ours
tabs = [df.label for df in frappe.get_meta("Proforma Invoice").fields
        if df.fieldtype == "Tab Break"]
check("keeps the order's tabs and adds Export Details",
      "Export Details" in tabs and "Address & Contact" in tabs and "Terms" in tabs, tabs)

print("\n=== 2. the same document, built both ways ===")
for label, customer, export in (
	("intra-state", customer_in("same"), False),
	("inter-state", customer_in("other"), False),
	("export", overseas_customer(), True),
):
	if not customer:
		check("%s: a customer exists to test with" % label, False, "none on this site")
		continue

	order = build("Sales Order", customer)
	proforma = build("Proforma Invoice", customer, export=export)
	a, b = SHAPE(order), SHAPE(proforma)

	for key in a:
		check("%-12s %-24s" % (label, key), a[key] == b[key],
		      "order=%r proforma=%r" % (a[key], b[key]) if a[key] != b[key] else a[key])

	# and the proforma turns into exactly that order
	if export:
		proforma.submit()
		from erpnext_export_tracker.export_tracker.doctype.proforma_invoice.proforma_invoice import (
			make_sales_order,
		)

		raised = make_sales_order(proforma.name)
		raised.delivery_date = add_days(today(), 30)
		for row in raised.items:
			row.delivery_date = add_days(today(), 30)
			row.warehouse = WAREHOUSE
		raised.insert()
		check("export: taxes survive the trip to the order",
		      len(raised.taxes) == len(proforma.taxes), "%d vs %d" % (len(raised.taxes),
		                                                              len(proforma.taxes)))
		check("export: the order lands on the same grand total",
		      raised.grand_total == proforma.grand_total,
		      "%s vs %s" % (raised.grand_total, proforma.grand_total))
		check("export: rows arrive as Sales Order Items",
		      raised.items[0].doctype == "Sales Order Item")
		check("export: the order is flagged for export", raised.custom_is_export == 1)

print("\n=== 7. quotation -> proforma -> order ===")
from erpnext_export_tracker.export_tracker.doctype.proforma_invoice.proforma_invoice import (  # noqa: E402
	make_proforma_invoice,
)

# this site refuses a quotation without payment terms and a contact, so pick a
# customer that can satisfy both
chain_customer = frappe.db.sql("""
	select c.name, ct.name from `tabCustomer` c
	join `tabDynamic Link` adl on adl.link_name = c.name and adl.link_doctype = 'Customer'
	join `tabAddress` a on a.name = adl.parent and ifnull(a.gstin, '') != ''
	join `tabDynamic Link` cdl on cdl.link_name = c.name and cdl.link_doctype = 'Customer'
	join `tabContact` ct on ct.name = cdl.parent
	where c.disabled = 0 limit 1""")

if not chain_customer:
	print("SKIP  chain -- no customer with both a GST address and a contact")
else:
	party, contact = chain_customer[0]
	quote = frappe.new_doc("Quotation")
	quote.quotation_to = "Customer"
	quote.party_name = party
	quote.company = COMPANY
	quote.transaction_date = today()
	quote.valid_till = add_days(today(), 30)
	quote.contact_person = contact
	quote.payment_terms_template = frappe.db.get_value("Payment Terms Template", {}, "name")
	quote.append("items", {"item_code": ITEM, "qty": 4, "rate": 250, "warehouse": WAREHOUSE})
	quote.insert()
	quote.submit()

	proforma = make_proforma_invoice(quote.name)
	proforma.insert()
	check("the proforma remembers its quotation", proforma.quotation == quote.name)
	check("quotation items arrive as proforma items",
	      proforma.items[0].doctype == "Proforma Invoice Item"
	      and len(proforma.items) == len(quote.items))
	check("the quotation's taxes come across", len(proforma.taxes) == len(quote.taxes),
	      "%d vs %d" % (len(proforma.taxes), len(quote.taxes)))
	check("quotation and proforma agree on the total",
	      proforma.grand_total == quote.grand_total,
	      "%s vs %s" % (proforma.grand_total, quote.grand_total))

	proforma.submit()
	raised = make_sales_order(proforma.name)
	raised.delivery_date = add_days(today(), 30)
	for row in raised.items:
		row.delivery_date = add_days(today(), 30)
		row.warehouse = WAREHOUSE
	raised.insert()
	check("the order remembers its proforma",
	      raised.custom_proforma_invoice == proforma.name)
	check("the total survives the whole chain",
	      quote.grand_total == proforma.grand_total == raised.grand_total,
	      "%s / %s / %s" % (quote.grand_total, proforma.grand_total, raised.grand_total))

	# each document shows the ones either side of it
	for doctype, expected in (("Quotation", "Proforma Invoice"),
	                          ("Sales Order", "Proforma Invoice"),
	                          ("Proforma Invoice", "Sales Order")):
		dash = frappe.get_meta(doctype).get_dashboard_data()
		shown = [i for g in dash.get("transactions", []) for i in g.get("items", [])]
		check("%-18s connects to %s" % (doctype, expected), expected in shown, shown[:6])

	# a quotation to a lead has no customer to put on the proforma
	lead_quote = frappe.db.get_value(
		"Quotation", {"quotation_to": "Lead", "docstatus": 1}, "name"
	)
	if lead_quote:
		try:
			make_proforma_invoice(lead_quote)
			check("a quotation to a lead is refused", False, "no error raised")
		except frappe.ValidationError:
			check("a quotation to a lead is refused", True)
			frappe.clear_last_message()
	else:
		print("SKIP  lead quotation -- none submitted on this site")

# Is Export is a flag, and flags belong together in the third column of a
# transaction's first section -- not beside the customer name on each one.
print("\n=== 8. Is Export sits in the third column everywhere ===")
for doctype, flag in (("Quotation", "custom_is_export"),
                      ("Sales Order", "custom_is_export"),
                      ("Sales Invoice", "custom_is_export"),
                      ("Delivery Note", "custom_is_export"),
                      ("Proforma Invoice", "is_export")):
	meta, section, flag_column = frappe.get_meta(doctype), None, None
	columns, current, column = {}, None, 1
	for df in meta.fields:
		if df.fieldtype in ("Section Break", "Tab Break"):
			current, column = df.fieldname, 1
			columns[current] = {1: []}
			continue
		if df.fieldtype == "Column Break":
			column += 1
			columns.setdefault(current, {})[column] = []
			continue
		columns.setdefault(current, {}).setdefault(column, []).append((df.fieldname, df.hidden))
		if df.fieldname == flag:
			section, flag_column = current, column

	visible = {c: [n for n, h in v if not h] for c, v in (columns.get(section) or {}).items()}
	rendered = [c for c in sorted(visible) if visible[c]]
	position = rendered.index(flag_column) + 1 if flag_column in rendered else None
	check("%-18s Is Export in column 3" % doctype, position == 3,
	      "column %s of %d" % (position, len(rendered)))

print("\n" + "=" * 62)
print("PASSED: %d    FAILED: %d" % (len(PASS), len(FAIL)))
if FAIL:
	print("\nFailures:")
	for f in FAIL:
		print("  -", f)
print("=" * 62)

frappe.db.rollback()
print("\nrolled back")
