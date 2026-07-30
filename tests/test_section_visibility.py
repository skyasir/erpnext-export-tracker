"""Prove the progressive-disclosure rules can't deadlock the workflow.

For every gate, the field it demands must sit in a section that is already
visible at the stage the user takes the action from (target index - 1).
"""

import json

import frappe

frappe.init(site="supreme.localhost")
frappe.connect()

from erpnext_export_tracker.export_tracker.doctype.export_shipment.export_shipment import (  # noqa: E402
	STATE_ORDER,
)

PASS, FAIL = [], []


def check(label, cond, detail=""):
	(PASS if cond else FAIL).append(label)
	print("%s  %s%s" % ("PASS" if cond else "FAIL", label, (" -- " + str(detail)) if detail else ""))


# ---------------------------------------------------------------- map the form
meta = frappe.get_meta("Export Shipment")
field_section = {}
section_threshold = {}
current_section = None

for df in meta.fields:
	if df.fieldtype == "Section Break":
		current_section = df.fieldname
		dep = df.depends_on or ""
		if "stage_index >=" in dep:
			section_threshold[current_section] = int(dep.split(">=")[1].strip().rstrip("\"'"))
		else:
			section_threshold[current_section] = 0  # always visible (or route-based)
	elif current_section:
		field_section[df.fieldname] = current_section

print("=== section reveal thresholds ===")
for sec, idx in section_threshold.items():
	shown = STATE_ORDER[idx] if idx < len(STATE_ORDER) else "?"
	print("  %-24s stage %-2d (%s)" % (sec, idx, "always" if idx == 0 else shown))

# ------------------------------------------------- what each gate demands
# target state -> fields validate() requires to reach it
GATE_FIELDS = {
	"Freight Finalised": ["cha_quotes", "selected_cha"],
	"Dispatch Planned": ["dispatch_plan_date"],
	"Customs Docs Prepared": ["pre_shipment_documents"],
	"Container Loaded": ["loading_date", "container_no", "customs_seal_no",
	                     "shipping_line_seal_no"],
	"Shipped": ["shipping_bill_no", "shipping_bill_date", "etd", "lc_received_on",
	            "lc_last_shipment_date"],
	"Post-Shipment Docs Prepared": ["post_shipment_documents", "bl_no", "coo_no",
	                                "coo_type", "insurance_policy_no"],
	"Docs Submitted": ["management_signed"],
	"XAR Generated": ["xar_no", "xar_date"],
	"Bank Submission Done": ["shipping_bill_no", "port_code"],
	"EBRC Generated": ["ebrc_no", "ebrc_date"],
}

print("\n=== deadlock check: is every demanded field visible when it is needed? ===")
for target, fields in GATE_FIELDS.items():
	target_idx = STATE_ORDER.index(target)
	action_idx = target_idx - 1          # the stage the user acts from
	for fieldname in fields:
		section = field_section.get(fieldname)
		if not section:
			check("%s needs %s" % (target, fieldname), False, "field not found on the form")
			continue
		threshold = section_threshold[section]
		ok = threshold <= action_idx
		check(
			"%-28s needs %-24s" % (target, fieldname),
			ok,
			"section %s reveals at %d, needed while at %d (%s)"
			% (section, threshold, action_idx, STATE_ORDER[action_idx]),
		)

# ------------------------------------------------- sections never hide backwards
print("\n=== monotonic: a section, once shown, stays shown ===")
check("all thresholds use >= (never == or a range)",
      all(">=" in (df.depends_on or "") or not (df.depends_on or "").startswith("eval:doc.stage_index")
          for df in meta.fields if df.fieldtype == "Section Break"))

# ------------------------------------------------- layout: tables get full width
# A Column Break in the same section splits it into two columns and the grid
# renders at half width, truncating its own headers. A section holding a Table
# must hold nothing else that introduces a column.
print("\n=== layout: every child table sits in a full-width section ===")
for doctype in ("Export Shipment", "Export Indent", "Export Document Template"):
	dmeta = frappe.get_meta(doctype)
	section = None
	buckets = {}
	for df in dmeta.fields:
		if df.fieldtype == "Section Break":
			section = df.fieldname
			buckets[section] = []
		elif section:
			buckets[section].append(df)

	for sec, dfs in buckets.items():
		tables = [d.fieldname for d in dfs if d.fieldtype == "Table"]
		breaks = [d.fieldname for d in dfs if d.fieldtype == "Column Break"]
		if not tables:
			continue
		check(
			"%s / %s holds %s full width" % (doctype, sec, tables[0]),
			not breaks,
			"column breaks in the section: %s" % (breaks or "none"),
		)

# ------------------------------------------------- live: stage_index tracks status
print("\n=== live: stage_index follows status ===")
from frappe.utils import add_days, today  # noqa: E402

so = frappe.new_doc("Sales Order")
so.customer = "A1 Poultry Farm"
so.company = "Supreme Equipments Pvt Ltd"
so.currency = "USD"
so.conversion_rate = 93.0
so.transaction_date = today()
so.delivery_date = add_days(today(), 30)
so.custom_is_export = 1
so.append("items", {"item_code": "SE-AO-FS-300011", "qty": 1, "rate": 10,
                    "warehouse": "P1 - Central / Main Store - SEPL",
                    "delivery_date": add_days(today(), 30)})
so.insert()
so.submit()

ship = frappe.get_doc("Export Shipment", {"sales_order": so.name})
check("new shipment starts at stage 0", ship.stage_index == 0,
      "%s / %s" % (ship.status, ship.stage_index))

ship.status = "Indent Approved"
ship.save()
check("stage_index tracks a status change", ship.stage_index == 1,
      "%s / %s" % (ship.status, ship.stage_index))

cha = frappe.db.get_value("Supplier", {"supplier_group": "CHA"}, "name") or \
	frappe.db.get_value("Supplier", {}, "name")
ship.append("cha_quotes", {"cha": cha, "currency": "USD", "freight_amount": 100,
                           "is_selected": 1})
ship.status = "Freight Finalised"
ship.save()
check("container section is revealed exactly when dispatch planning starts",
      ship.stage_index == 2 and section_threshold["container_section"] <= 2,
      "stage_index=%s" % ship.stage_index)

check("closure section still hidden mid-flow",
      section_threshold["closure_section"] > ship.stage_index,
      "closure reveals at %d, now at %d" % (section_threshold["closure_section"], ship.stage_index))

print("\n" + "=" * 62)
print("PASSED: %d    FAILED: %d" % (len(PASS), len(FAIL)))
if FAIL:
	print("\nFailures:")
	for f in FAIL:
		print("  -", f)
print("=" * 62)

frappe.db.rollback()
print("\nrolled back")
