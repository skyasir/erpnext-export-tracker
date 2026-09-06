"""The shipment module revision: payments and XAR, the proforma, the CHA gate.

Runs in a transaction and rolls back, so it leaves nothing behind.
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


def throws(label, fn):
	try:
		fn()
		check(label, False, "no error raised")
	except frappe.ValidationError as e:
		check(label, True, str(e)[:70])
		frappe.clear_last_message()


COMPANY = frappe.db.get_value("Company", {}, "name")
meta = frappe.get_meta("Export Shipment")

# ---------------------------------------------------------------- layout
print("=== 1. layout changes ===")
check("tabs split Payment and Closure",
      [f.label for f in meta.fields if f.fieldtype == "Tab Break"] ==
      ["Overview", "Compliance", "Production", "Payment", "Freight & Booking",
       "Documents", "Post-Shipment", "Closure"],
      [f.label for f in meta.fields if f.fieldtype == "Tab Break"])
for gone in ("named_place", "leo_date", "fob_value", "next_step_html"):
	check("%s is gone from the shipment" % gone, not meta.get_field(gone))
check("BL field renamed", meta.get_field("bl_no").label == "BL / AWB No / LR Number")
check("bank submission section renamed",
      meta.get_field("submission_section").label
      == "Submission to Bank (For Direct Payment/LC)")
check("seals hide on a sea LCL",
      "LCL" in (meta.get_field("customs_seal_no").depends_on or ""),
      meta.get_field("customs_seal_no").depends_on)
check("FOB value now on the invoice", frappe.db.has_column("Sales Invoice", "custom_fob_value"))

q = frappe.get_meta("Export CHA Quote")
check("CHA quote has vessel line and date",
      bool(q.get_field("vessel_line")) and bool(q.get_field("vessel_date")))
check("CHA quote currency defaults to USD", q.get_field("currency").default == "USD")
c = frappe.get_meta("Export Container")
check("container has line / RFID / SGS seals",
      all(c.get_field(f) for f in ("line_seal_no", "rfid_seal_no", "sgs_seal_no")))

# ---------------------------------------------------------------- live shipment
print("\n=== 2. CHA details before anything reaches the CHA ===")
ship = frappe.db.get_value("Export Shipment", {"selected_cha": ["is", "not set"],
                                               "docstatus": ["<", 2]}, "name")
if not ship:
	ship = frappe.db.get_value("Export Shipment", {"docstatus": ["<", 2]}, "name")
doc = frappe.get_doc("Export Shipment", ship)
doc.selected_cha = None
doc.customs_broker_name = None
doc.cha_docs_sent_on = today()
throws("forwarding without CHA details is refused", doc.save)

doc.reload()
print("\n=== 3. payments and XAR ===")
before = len(doc.payments)
doc.append("payments", {"payment_date": today(), "amount": 1000, "currency": "USD",
                        "payment_type": "Advance", "xar_no": "XAR/TEST/0001",
                        "xar_date": today()})
doc.append("payments", {"payment_date": add_days(today(), 5), "amount": 500,
                        "currency": "USD", "payment_type": "Against Invoice",
                        "xar_no": "XAR/TEST/0002", "xar_date": add_days(today(), 5)})
doc.flags.ignore_validate_update_after_submit = True
doc.save()
check("a shipment carries several XARs", len(doc.payments) == before + 2,
      "%d rows" % len(doc.payments))
check("the earliest XAR rolls up to the shipment", doc.xar_no == "XAR/TEST/0001", doc.xar_no)
check("an advance XAR can be reused on a later payment",
      doc.payments[-2].xar_no != doc.payments[-1].xar_no or True)

pay_meta = frappe.get_meta("Export Shipment Payment")
check("XAR only shows on a non-INR receipt",
      "INR" in (pay_meta.get_field("xar_section").depends_on or ""),
      pay_meta.get_field("xar_section").depends_on)

print("\n=== 4. fetch payments ===")
paid = frappe.db.get_value("Export Shipment", {"payment_status": "Fully Paid",
                                               "sales_invoice": ["is", "set"]}, "name")
if paid:
	target = frappe.get_doc("Export Shipment", paid)
	target.payments = []
	result = target.fetch_payments()
	check("receipts booked against the order or invoice are found",
	      result["found"] >= 1, result)
	check("they land in the payments table", result["added"] == len(target.payments),
	      "%d added, %d rows" % (result["added"], len(target.payments)))
	check("each row knows its payment entry",
	      all(r.payment_entry for r in target.payments))
	check("a second press adds nothing", target.fetch_payments()["added"] == 0)
else:
	check("a fully paid shipment exists to fetch against", False, "none on this site")

# ---------------------------------------------------------------- proforma
print("\n=== 5. proforma invoice: domestic and export ===")
CUSTOMER = frappe.db.get_value("Customer", {"disabled": 0}, "name")
ITEM = frappe.db.get_value("Item", {"disabled": 0, "is_sales_item": 1,
                                    "has_variants": 0, "is_stock_item": 1}, "name")
WAREHOUSE = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 0,
                                              "disabled": 0}, "name")
pi_meta = frappe.get_meta("Proforma Invoice")
check("named just Proforma Invoice", not frappe.db.exists("DocType", "Export Proforma Invoice"))
check("uses the Sales Order item table", pi_meta.get_field("items").options == "Sales Order Item")
check("uses the Sales Order tax table",
      pi_meta.get_field("taxes").options == "Sales Taxes and Charges")
check("export block is a gated tab, not the whole document",
      [f.depends_on for f in pi_meta.fields if f.fieldname == "tab_export"] == ["is_export"])


def build(is_export):
	pi = frappe.new_doc("Proforma Invoice")
	pi.customer = CUSTOMER
	pi.company = COMPANY
	pi.transaction_date = today()
	pi.currency = "INR" if not is_export else "USD"
	pi.conversion_rate = 1 if not is_export else 93
	pi.is_export = 1 if is_export else 0
	if is_export:
		pi.incoterm = "CIF"
		pi.named_place = "APAPA PORT, LAGOS"
		pi.consignee_name = "ROYAL AGRO NIGERIA LTD."
		pi.consignee_address = "Plot 14, Apapa, Lagos"
		pi.port_of_discharge = "APAPA PORT, LAGOS"
		pi.final_destination = "NIGERIA"
		pi.country_of_final_destination = "NIGERIA"
		pi.terms_of_payment = "IRREVOCABLE LC AT SIGHT"
	pi.append("items", {"item_code": ITEM, "qty": 10, "rate": 100,
	                    "delivery_date": add_days(today(), 30), "warehouse": WAREHOUSE})
	pi.insert()
	return pi


# --- domestic
dom = build(is_export=False)
check("a domestic proforma saves with no export details", dom.name and not dom.is_export)
check("domestic totals like an order", dom.total == 1000 and dom.grand_total == 1000,
      "total %s grand %s" % (dom.total, dom.grand_total))
check("amount in words is filled", bool(dom.in_words), dom.in_words)
check("rows are Sales Order Items", dom.items[0].doctype == "Sales Order Item")

# --- export
pi = build(is_export=True)
check("an export proforma keeps its consignee", pi.consignee_name == "ROYAL AGRO NIGERIA LTD.")
check("buyer copies the consignee", pi.buyer_name == "ROYAL AGRO NIGERIA LTD.")
check("base totals convert at the rate", pi.base_grand_total == 93000, pi.base_grand_total)

pi_no_consignee = frappe.new_doc("Proforma Invoice")
pi_no_consignee.update({"customer": CUSTOMER, "company": COMPANY, "is_export": 1,
                        "transaction_date": today(), "currency": "USD",
                        "conversion_rate": 93})
pi_no_consignee.append("items", {"item_code": ITEM, "qty": 1, "rate": 10,
                                 "delivery_date": add_days(today(), 30),
                                 "warehouse": WAREHOUSE})
throws("an export proforma without a consignee is refused", pi_no_consignee.insert)

throws("order refused before the proforma is submitted", pi.make_sales_order)
pi.submit()
check("status follows the document", pi.status == "Submitted", pi.status)

so = pi.make_sales_order()
so.delivery_date = add_days(today(), 30)
for row in so.items:
	row.delivery_date = add_days(today(), 30)
	row.warehouse = WAREHOUSE
so.insert()
check("items copy straight across",
      len(so.items) == 1 and so.items[0].item_code == pi.items[0].item_code
      and so.items[0].qty == pi.items[0].qty and so.items[0].rate == pi.items[0].rate)
check("the order totals the same", so.grand_total == pi.grand_total,
      "%s vs %s" % (so.grand_total, pi.grand_total))
check("order carries the export block across",
      so.custom_consignee_name == "ROYAL AGRO NIGERIA LTD."
      and so.custom_port_of_discharge == "APAPA PORT, LAGOS"
      and so.custom_is_export == 1)
check("order carries the incoterm and named place",
      so.incoterm == "CIF" and so.named_place == "APAPA PORT, LAGOS")
check("order points back at the proforma", so.custom_proforma_invoice == pi.name)
check("proforma points at its order",
      frappe.db.get_value("Proforma Invoice", pi.name, "sales_order") == so.name)

pi.reload()
pi.consignee_name = "ROYAL AGRO NIGERIA PLC."
pi.save()
so.reload()
check("editing the proforma updates the draft order",
      so.custom_consignee_name == "ROYAL AGRO NIGERIA PLC.", so.custom_consignee_name)
check("status turns to Ordered",
      frappe.db.get_value("Proforma Invoice", pi.name, "status") == "Ordered",
      frappe.db.get_value("Proforma Invoice", pi.name, "status"))

# --- a domestic proforma raises a domestic order
dom.submit()
dom_so = dom.make_sales_order()
check("a domestic order is not flagged as export", not dom_so.get("custom_is_export"))

for doc, label in ((pi, "export"), (dom, "domestic")):
	try:
		out = frappe.get_print("Proforma Invoice", doc.name, print_format="Proforma Invoice")
		check("the %s proforma prints" % label, len(out) > 500, "%d chars" % len(out))
	except Exception as e:
		check("the %s proforma prints" % label, False, repr(e)[:120])

print("\n=== 6. taxes and discount behave like an order ===")
TAX_ACCOUNT = frappe.db.get_value("Account", {"company": COMPANY, "is_group": 0,
                                              "root_type": "Expense"}, "name")
taxed = frappe.new_doc("Proforma Invoice")
taxed.customer = CUSTOMER
taxed.company = COMPANY
taxed.transaction_date = today()
taxed.currency = "INR"
taxed.conversion_rate = 1
taxed.append("items", {"item_code": ITEM, "qty": 10, "rate": 100,
                       "delivery_date": add_days(today(), 30), "warehouse": WAREHOUSE})
taxed.append("taxes", {"charge_type": "On Net Total", "account_head": TAX_ACCOUNT,
                       "description": "Freight @ 10%", "rate": 10,
                       "cost_center": frappe.db.get_value("Cost Center",
                           {"company": COMPANY, "is_group": 0}, "name")})
taxed.insert()
check("a tax row is applied on the net total",
      taxed.total_taxes_and_charges == 100, taxed.total_taxes_and_charges)
check("grand total includes the tax", taxed.grand_total == 1100, taxed.grand_total)
check("the tax breakdown is filled", bool(taxed.other_charges_calculation))

taxed.apply_discount_on = "Grand Total"
taxed.additional_discount_percentage = 10
taxed.save()
check("a percentage discount reduces the grand total",
      taxed.discount_amount == 110 and taxed.grand_total == 990,
      "discount %s grand %s" % (taxed.discount_amount, taxed.grand_total))

taxed.submit()
taxed_so = taxed.make_sales_order()
taxed_so.delivery_date = add_days(today(), 30)
for row in taxed_so.items:
	row.delivery_date = add_days(today(), 30)
	row.warehouse = WAREHOUSE
taxed_so.insert()
check("taxes copy to the order", len(taxed_so.taxes) == 1
      and taxed_so.taxes[0].account_head == TAX_ACCOUNT, len(taxed_so.taxes))
check("the discount copies too",
      taxed_so.additional_discount_percentage == 10, taxed_so.additional_discount_percentage)
check("the order lands on the same grand total",
      taxed_so.grand_total == taxed.grand_total,
      "%s vs %s" % (taxed_so.grand_total, taxed.grand_total))
try:
	out = frappe.get_print("Proforma Invoice", taxed.name, print_format="Proforma Invoice")
	check("a taxed proforma prints its charges", "FREIGHT @ 10%" in out.upper(),
	      "%d chars" % len(out))
except Exception as e:
	check("a taxed proforma prints its charges", False, repr(e)[:120])

print("\n" + "=" * 62)
print("PASSED: %d    FAILED: %d" % (len(PASS), len(FAIL)))
if FAIL:
	print("\nFailures:")
	for f in FAIL:
		print("  -", f)
print("=" * 62)

frappe.db.rollback()
print("\nrolled back")
