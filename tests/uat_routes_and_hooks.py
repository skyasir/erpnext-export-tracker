"""Round 2 UAT: the gaps left by uat_export.py. Rolls everything back."""

import frappe
from frappe.utils import add_days, today

PASS, FAIL = [], []


def check(label, cond, detail=""):
	(PASS if cond else FAIL).append(label)
	print("%s  %s%s" % ("PASS" if cond else "FAIL", label, (" -- " + str(detail)) if detail else ""))


def expect_throw(label, fn):
	try:
		fn()
	except frappe.ValidationError as e:
		check(label, True, str(e)[:110].replace("\n", " "))
		return
	except Exception as e:
		check(label, False, "wrong exception: %r" % e)
		return
	check(label, False, "no exception raised")


frappe.init(site="supreme.localhost")
frappe.connect()
frappe.set_user("Administrator")

CUSTOMER = "A1 Poultry Farm"
ITEM = "SE-AO-FS-300011"
COMPANY = "Supreme Equipments Pvt Ltd"
WAREHOUSE = "P1 - Central / Main Store - SEPL"
INCOME = "Sales Account - Cages - SEPL - SEPL"
COST_CENTER = "Main - SEPL"
DEBIT_TO = "Sundry Debtors - Corporate - SEPL"
BANK = "KOTAK MAHINDRA BANK OD NO. - 6396 - SEPL"


def new_export_so(qty=100, rate=10):
	so = frappe.new_doc("Sales Order")
	so.customer = CUSTOMER
	so.company = COMPANY
	so.currency = "USD"
	so.conversion_rate = 93.0
	so.transaction_date = today()
	so.delivery_date = add_days(today(), 30)
	so.incoterm = "FOB"
	so.custom_is_export = 1
	so.custom_consignee_name = "M/S. ROYAL AGROVET LTD."
	so.append("items", {"item_code": ITEM, "qty": qty, "rate": rate, "uom": "Nos",
	                    "warehouse": WAREHOUSE, "delivery_date": add_days(today(), 30)})
	so.insert()
	so.submit()
	return so


# ======================================================================
print("\n=== A. Letter of Credit route (untested branch) ===")
so = new_export_so()
ship = frappe.get_doc("Export Shipment", {"sales_order": so.name})
ship.payment_route = "Through Letter of Credit"
ship.destination_country = "Sri Lanka"
ship.save()

res = ship.load_document_checklist()
ship.save()
ship.reload()
check("LC route resolves a template", bool(res["template"]), res)
post = [d.document_name for d in ship.post_shipment_documents]
pre = [d.document_name for d in ship.pre_shipment_documents]
check("ISFTA certificate pulled in for Sri Lanka",
      any("ISFTA" in d for d in pre + post), [d for d in pre + post if "ISFTA" in d])

# walk to the point of shipping
ship.status = "Indent Approved"
ship.save()
cha = frappe.db.get_value("Supplier", {"supplier_group": "CHA"}, "name") or \
	frappe.db.get_value("Supplier", {}, "name")
ship.append("cha_quotes", {"cha": cha, "currency": "USD", "freight_amount": 100,
                           "transit_days": 10, "free_days": 7, "is_selected": 1})
ship.status = "Freight Finalised"
ship.save()
ship.dispatch_plan_date = today()
ship.status = "Dispatch Planned"
ship.save()
for row in ship.pre_shipment_documents:
	row.prepared = 1
ship.status = "Customs Docs Prepared"
ship.save()
ship.loading_date = today()
ship.container_no = "TEST1234567"
ship.customs_seal_no = "C1"
ship.shipping_line_seal_no = "S1"
ship.status = "Container Loaded"
ship.save()
# persist the shipping bill data FIRST, while still at Container Loaded, so an
# expected throw + reload cannot silently discard it and fake a pass
ship.shipping_bill_no = "SB-LC-1"
ship.shipping_bill_date = today()
ship.port_code = "INNSA1"
ship.etd = today()
ship.save()
check("shipping bill data persisted at Container Loaded",
      frappe.db.get_value("Export Shipment", ship.name, "etd") is not None)

ship.status = "Shipped"
expect_throw("LC: blocked from shipping before the LC is received", ship.save)

# persist the LC fields, leaving last-shipment-date in the past on purpose
ship.reload()
ship.lc_no = "LC-9911"
ship.lc_issuing_bank = "Bank of Ceylon"
ship.lc_draft_received_on = add_days(today(), -20)
ship.lc_terms_reviewed = 1
ship.lc_management_confirmed = 1
ship.lc_acceptance_sent_on = add_days(today(), -15)
ship.lc_received_on = add_days(today(), -10)
ship.lc_expiry_date = add_days(today(), 20)
ship.lc_last_shipment_date = add_days(today(), -1)   # yesterday -- ETD is today
ship.save()
check("LC fields persisted, ETD still today, last shipment date yesterday",
      str(frappe.db.get_value("Export Shipment", ship.name, "lc_received_on")) ==
      str(add_days(today(), -10)))

ship.status = "Shipped"
try:
	ship.save()
	check("LC: blocked when ETD is after the last shipment date", False,
	      "no exception -- the ETD gate did NOT fire")
except frappe.ValidationError as e:
	msg = str(e)
	check("LC: blocked when ETD is after the last shipment date",
	      "Last Date of Shipment" in msg, msg[:130].replace("\n", " "))

ship.reload()
ship.lc_last_shipment_date = add_days(today(), 5)
ship.status = "Shipped"
ship.save()
check("LC: ships once the LC is received and the ETD is in window",
      ship.status == "Shipped")

html = frappe.get_print("Export Shipment", ship.name, print_format="Request Letter to Bank")
check("LC: bank letter switches to the negotiation heading",
      "NEGOTIATION OF EXPORT DOCUMENTS UNDER LETTER OF CREDIT" in html
      and "LC-9911" in html)
check("LC: bank letter flags pending enclosures", "(PENDING)" in html)

# ======================================================================
print("\n=== B. Through Bank route document set ===")
so_b = new_export_so()
ship_b = frappe.get_doc("Export Shipment", {"sales_order": so_b.name})
ship_b.payment_route = "Through Bank"
ship_b.save()
ship_b.load_document_checklist()
ship_b.save()
ship_b.reload()
post_b = [d.document_name for d in ship_b.post_shipment_documents]
for needed in ("Bill of Exchange", "Dispatch Declaration",
               "Request Letter to Bank for Export Bill on Collection",
               "Document Set for Our Bank", "Document Set for Consignee Bank"):
	check("bank route includes %r" % needed, needed in post_b)

html_b = frappe.get_print("Export Shipment", ship_b.name, print_format="Request Letter to Bank")
check("bank route letter uses the collection heading",
      "EXPORT BILL ON COLLECTION" in html_b
      and "NEGOTIATION OF EXPORT DOCUMENTS" not in html_b)

# ======================================================================
print("\n=== C. Part-shipment: two shipments on one Sales Order ===")
from erpnext_export_tracker.export_tracker.doctype.export_shipment.export_shipment import (
	make_export_shipment,
)
# an untouched first shipment must block a second (accidental double-click)
expect_throw("duplicate blocked while the first shipment is untouched",
             lambda: make_export_shipment(so_b.name))

# once the first shipment is genuinely in progress, a second is a part-shipment
ship_b.status = "Indent Approved"
ship_b.save()
second = make_export_shipment(so_b.name)
check("second shipment allowed once the first is in progress", bool(second), second)
check("order now has two shipments",
      frappe.db.count("Export Shipment", {"sales_order": so_b.name}) == 2)
s2 = frappe.get_doc("Export Shipment", second)
s2.shipping_bill_no = "SB-PART-2"
s2.xar_no = "XAR-PART-2"
s2.save()
check("the two shipments carry independent shipping bill / XAR",
      frappe.db.get_value("Export Shipment", ship_b.name, "shipping_bill_no") != s2.shipping_bill_no)

# ======================================================================
print("\n=== D. Delivery Note hook (never executed before) ===")
# give the item stock first -- the DN hook can't be reached through a
# NegativeStockError, which is an environment condition not an app defect
se = frappe.new_doc("Stock Entry")
se.stock_entry_type = "Material Receipt"
se.company = COMPANY
se.posting_date = today()
se.append("items", {"item_code": ITEM, "qty": 500, "t_warehouse": WAREHOUSE,
                    "basic_rate": 100, "uom": "Nos"})
se.insert()
se.submit()
check("stock receipted for the DN test", se.docstatus == 1, se.name)

from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
dn = frappe.get_doc(make_delivery_note(so.name))
dn.custom_is_export = 1
dn.custom_export_shipment = ship.name
dn.shipping_bill_number = "SB-LC-1"
dn.shipping_bill_date = today()
dn.port_code = "INNSA1"
for row in dn.items:
	row.warehouse = WAREHOUSE
try:
	dn.insert()
	dn.submit()
	ship.reload()
	check("DN on_submit links itself to the shipment", ship.delivery_note == dn.name,
	      ship.delivery_note)
	check("DN stamped the loading date", bool(ship.loading_date), ship.loading_date)
except Exception as e:
	check("Delivery Note submits and links", False, repr(e)[:160])

# ======================================================================
print("\n=== E. Advance payment against the Sales Order (untested path) ===")
so_c = new_export_so(qty=10, rate=100)          # 1000 USD
ship_c = frappe.get_doc("Export Shipment", {"sales_order": so_c.name})
check("no invoice yet -> status Unpaid", ship_c.payment_status == "Unpaid",
      ship_c.payment_status)

pe = frappe.new_doc("Payment Entry")
pe.payment_type = "Receive"
pe.company = COMPANY
pe.party_type = "Customer"
pe.party = CUSTOMER
pe.posting_date = today()
pe.reference_no = "ADV-1"
pe.reference_date = today()
pe.paid_from = DEBIT_TO
pe.paid_from_account_currency = "INR"
pe.paid_to = BANK
pe.source_exchange_rate = 1
pe.target_exchange_rate = 1
pe.paid_amount = 1000 * 93.0
pe.received_amount = 1000 * 93.0
pe.append("references", {"reference_doctype": "Sales Order", "reference_name": so_c.name,
                         "total_amount": 1000 * 93.0, "outstanding_amount": 1000 * 93.0,
                         "allocated_amount": 500 * 93.0})
pe.insert()
pe.submit()
ship_c.reload()
check("advance against the order moves the shipment off Unpaid",
      ship_c.payment_status in ("Partly Paid", "Fully Paid"),
      "%s / received %s of %s" % (ship_c.payment_status, ship_c.total_received,
                                  ship_c.invoice_amount))

print("\n=== F. Payment Entry cancel recalculates ===")
pe.cancel()
ship_c.reload()
check("cancelling the receipt puts it back to Unpaid",
      ship_c.payment_status == "Unpaid",
      "%s / received %s" % (ship_c.payment_status, ship_c.total_received))

# ======================================================================
print("\n=== G. Sales Invoice cancel unlinks (untested path) ===")
si = frappe.new_doc("Sales Invoice")
si.naming_series = "EXP/.###"
si.customer = CUSTOMER
si.company = COMPANY
si.currency = "USD"
si.conversion_rate = 93.0
si.posting_date = today()
si.debit_to = DEBIT_TO
si.custom_is_export = 1
si.custom_export_shipment = ship_c.name
si.append("items", {"item_code": ITEM, "qty": 10, "rate": 100, "uom": "Nos",
                    "income_account": INCOME, "cost_center": COST_CENTER,
                    "warehouse": WAREHOUSE, "sales_order": so_c.name})
si.set_missing_values()
si.insert()
si.submit()
ship_c.reload()
check("invoice links on submit", ship_c.sales_invoice == si.name)
si.cancel()
ship_c.reload()
check("invoice unlinks on cancel", not ship_c.sales_invoice, ship_c.sales_invoice)

# ======================================================================
print("\n=== H. Invoice found via the order when the link is not set ===")
si2 = frappe.new_doc("Sales Invoice")
si2.naming_series = "EXP/.###"
si2.customer = CUSTOMER
si2.company = COMPANY
si2.currency = "USD"
si2.conversion_rate = 93.0
si2.posting_date = today()
si2.debit_to = DEBIT_TO
si2.custom_is_export = 1
# deliberately NOT setting custom_export_shipment
si2.append("items", {"item_code": ITEM, "qty": 10, "rate": 100, "uom": "Nos",
                     "income_account": INCOME, "cost_center": COST_CENTER,
                     "warehouse": WAREHOUSE, "sales_order": so_c.name})
si2.set_missing_values()
si2.insert()
si2.submit()
check("shipment found via the Sales Order behind the invoice lines",
      frappe.db.get_value("Sales Invoice", si2.name, "custom_export_shipment") == ship_c.name,
      frappe.db.get_value("Sales Invoice", si2.name, "custom_export_shipment"))

# ======================================================================
print("\n=== I. Remaining country templates ===")
for country, needle in (("Nigeria", "SONCAP"), ("Nepal", "Letter of Undertaking"),
                        ("Bhutan", "Letter of Undertaking")):
	so_x = new_export_so()
	sx = frappe.get_doc("Export Shipment", {"sales_order": so_x.name})
	sx.destination_country = country
	sx.save()
	r = sx.load_document_checklist()
	sx.save()
	sx.reload()
	docs = [d.document_name for d in sx.pre_shipment_documents] + \
	       [d.document_name for d in sx.post_shipment_documents]
	check("%s template adds %s" % (country, needle),
	      r["template"] == "%s - Standard" % country and any(needle in d for d in docs),
	      r["template"])

# ======================================================================
print("\n=== J. Reports with actual rows in them ===")
from frappe.desk.query_report import run as run_report
for report, filters in (
	("Export Shipment Status", {"company": COMPANY, "hide_closed": 0}),
	("Pending Export Documents", {"company": COMPANY, "only_required": 1}),
	("Export Outstanding Payment Statement", {"company": COMPANY}),
	("Export Bank Closure Ageing", {"company": COMPANY}),
	("Export Incentive Master Details", {"company": COMPANY, "include_unclosed": 1}),
):
	try:
		res = run_report(report, filters=filters, ignore_prepared_report=True)
		rows = res.get("result") or []
		check("%s returns rows and formats them" % report, len(rows) > 0, "%d row(s)" % len(rows))
	except Exception as e:
		check("%s returns rows and formats them" % report, False, repr(e)[:160])

# ======================================================================
print("\n=== K. Reminder task with data that actually matches ===")
try:
	frappe.flags.mute_emails = True
	from erpnext_export_tracker import tasks
	settings = frappe.get_single("Export Tracker Settings")
	blocks = []
	blocks += tasks.documents_pending_before_etd(settings)
	blocks += tasks.lc_deadlines()
	blocks += tasks.closure_pending(settings)
	blocks += tasks.realisation_due(settings)
	check("reminder builders produce populated tables", len(blocks) > 0,
	      "%d block(s), %d chars" % (len(blocks), sum(len(b) for b in blocks)))
	tasks.send_export_reminders()
	check("full reminder job completes with live data", True)
except Exception as e:
	check("reminder builders produce populated tables", False, repr(e)[:200])

# ======================================================================
print("\n=== L. PDF generation (wkhtmltopdf) ===")
from frappe.utils.pdf import get_pdf
for pf, dt, name in (("Export Invoice", "Sales Invoice", si2.name),
                     ("Export Packing List", "Sales Invoice", si2.name),
                     ("Bill of Exchange", "Export Shipment", ship.name),
                     ("Request Letter to Bank", "Export Shipment", ship.name)):
	try:
		html = frappe.get_print(dt, name, print_format=pf)
		pdf = get_pdf(html)
		ok = pdf[:4] == b"%PDF"
		pages = pdf.count(b"/Type /Page") or pdf.count(b"/Type/Page")
		check("PDF renders: %s" % pf, ok, "%d KB, ~%d page marker(s)" % (len(pdf) // 1024, pages))
	except Exception as e:
		check("PDF renders: %s" % pf, False, repr(e)[:200])

print("\n" + "=" * 62)
print("ROUND 2 -- PASSED: %d    FAILED: %d" % (len(PASS), len(FAIL)))
if FAIL:
	print("\nFailures:")
	for f in FAIL:
		print("  -", f)
print("=" * 62)

frappe.db.rollback()
print("\nrolled back -- no test data persisted")
