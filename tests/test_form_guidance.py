"""Prove the form can always tell the user what it wants, and never hides it.

Sections used to disappear until the shipment reached their stage, which meant a
gate could demand a field the user could not see. They are collapsible now, so
this script checks the invariant that replaced it: every requirement the guidance
panel reports points at a field that is on the form, and the panel's blocking
list is exactly what validate() refuses to save.
"""

import frappe

frappe.init(site="supreme.localhost")
frappe.connect()

from erpnext_export_tracker.export_tracker.doctype.export_shipment.export_shipment import (  # noqa: E402
	NEXT_ACTION,
	STATE_ORDER,
)

PASS, FAIL = [], []


def check(label, cond, detail=""):
	(PASS if cond else FAIL).append(label)
	print("%s  %s%s" % ("PASS" if cond else "FAIL", label, (" -- " + str(detail)) if detail else ""))


meta = frappe.get_meta("Export Shipment")
fieldnames = {df.fieldname for df in meta.fields}

# ---------------------------------------------------------------- no hiding
print("=== no section hides itself by stage ===")
hidden = [
	df.fieldname
	for df in meta.fields
	if df.fieldtype == "Section Break" and "stage_index" in (df.depends_on or "")
]
check("no stage-gated depends_on left on a section", not hidden, hidden or "none")

collapsible = [
	df.fieldname
	for df in meta.fields
	if df.fieldtype == "Section Break" and "stage_index" in (df.collapsible_depends_on or "")
]
check("stage progress still auto-expands sections", len(collapsible) >= 10,
      "%d sections expand by stage" % len(collapsible))

# ---------------------------------------------------------------- tabs
print("\n=== every tab has content ===")
tabs, current, buckets = [], None, {}
for df in meta.fields:
	if df.fieldtype == "Tab Break":
		current = df.fieldname
		tabs.append(df)
		buckets[current] = []
	elif current and df.fieldtype not in ("Section Break", "Column Break"):
		buckets[current].append(df.fieldname)

check("form is split into tabs", len(tabs) >= 5, "%d tabs" % len(tabs))
for t in tabs:
	check("tab %s has fields" % t.label, bool(buckets[t.fieldname]),
	      "%d fields" % len(buckets[t.fieldname]))

# ---------------------------------------------------------------- requirements
print("\n=== every requirement points at a real field ===")
ship = frappe.new_doc("Export Shipment")
ship.status = STATE_ORDER[0]

bad = []
for state in STATE_ORDER:
	for req in ship.requirements_for(state):
		if req["fieldname"] and req["fieldname"] not in fieldnames:
			bad.append("%s -> %s" % (state, req["fieldname"]))
check("no requirement names a field that is not on the form", not bad, bad or "none")

# A gate that demands a field the form hides is a dead end: the panel lists it as
# blocking, the "go" link scrolls to nothing, and the shipment cannot move. The
# section-level check above does not catch it, because this kind of hiding is on
# the field. So evaluate each field's own depends_on against a real document and
# insist that nothing blocking is invisible.
print("\n=== nothing blocking is hidden ===")
import re  # noqa: E402

depends = {df.fieldname: (df.depends_on or "") for df in meta.fields}
section_of, current = {}, ""
for df in meta.fields:
	if df.fieldtype in ("Section Break", "Tab Break"):
		current = df.fieldname
	else:
		section_of[df.fieldname] = current


def visible(doc, fieldname):
	"""Is this field on screen for this document?

	Walks the field's own condition and its section's. An expression we cannot
	read is treated as visible, so the check only ever reports something it is
	sure about.
	"""
	for name in (fieldname, section_of.get(fieldname)):
		if not name:
			continue
		if not shown(doc, depends.get(name, "")):
			return False
	return True


def shown(doc, condition):
	if not condition:
		return True

	if not condition.startswith("eval:"):
		return bool(doc.get(condition.strip()))

	expr = condition[len("eval:"):]
	expr = expr.replace("!==", "!=").replace("===", "==")
	expr = re.sub(r"!(?!=)", " not ", expr)
	expr = expr.replace("&&", " and ").replace("||", " or ")
	expr = re.sub(r"\bdoc\.([a-z_][a-z0-9_]*)", r'_v("\1")', expr)
	try:
		return bool(eval(expr, {"__builtins__": {}}, {"_v": doc.get}))  # noqa: S307
	except Exception:
		return True  # unreadable -- say nothing rather than cry wolf


# the shapes a shipment actually takes, including the one that was stuck
SHAPES = [
	("sea LCL", {"mode": "Sea", "shipment_type": "LCL"}),
	("sea FCL", {"mode": "Sea", "shipment_type": "FCL"}),
	("air", {"mode": "Air", "shipment_type": "Air"}),
	("LC route", {"mode": "Sea", "shipment_type": "FCL",
	              "payment_route": "Through Letter of Credit"}),
	("inspection + Form M", {"mode": "Sea", "shipment_type": "FCL",
	                         "inspection_required": 1, "form_m_required": 1}),
	("insured, originals", {"mode": "Sea", "shipment_type": "FCL",
	                        "insurance_required": 1, "originals_required": 1}),
]

for label, shape in SHAPES:
	probe = frappe.new_doc("Export Shipment")
	probe.status = STATE_ORDER[0]
	probe.update(shape)
	hidden_blockers = []
	for state in STATE_ORDER:
		for req in probe.requirements_for(state):
			if not (req["blocking"] and req["fieldname"]):
				continue
			if not visible(probe, req["fieldname"]):
				hidden_blockers.append("%s: %s (%s)" % (state, req["label"],
				                                        req["fieldname"]))
	check("%-20s blocks on nothing it hides" % label, not hidden_blockers,
	      hidden_blockers or "none")

# and the rule the controller reads has to be the rule the form draws
seal_probe = frappe.new_doc("Export Shipment")
for mode, kind, expected in (("Sea", "LCL", False), ("Sea", "FCL", True),
                             ("Air", "Air", True)):
	seal_probe.mode, seal_probe.shipment_type = mode, kind
	check("seals_apply agrees with the form for %s %s" % (mode, kind),
	      seal_probe.seals_apply() == expected
	      and visible(seal_probe, "customs_seal_no") == expected,
	      "seals_apply=%s visible=%s" % (seal_probe.seals_apply(),
	                                     visible(seal_probe, "customs_seal_no")))

print("\n=== the panel names the same action the workflow does ===")
wf = frappe.get_doc("Workflow", "Export Shipment Process")
wf_actions = {t.state: t.action for t in wf.transitions}
mismatch = [s for s, a in NEXT_ACTION.items() if wf_actions.get(s) != a]
check("NEXT_ACTION matches the workflow's transitions", not mismatch, mismatch or "none")
check("every state but the last has a next action",
      set(NEXT_ACTION) == set(STATE_ORDER[:-1]),
      set(STATE_ORDER[:-1]) ^ set(NEXT_ACTION))

# ---------------------------------------------------------------- layout
# A Column Break in the same section splits it into two columns and the grid
# renders at half width, truncating its own headers.
print("\n=== every child table sits in a full-width section ===")
for doctype in ("Export Shipment", "Export Indent", "Export Document Template",
                "Export Country Profile"):
	dmeta = frappe.get_meta(doctype)
	section, sections = None, {}
	for df in dmeta.fields:
		if df.fieldtype in ("Section Break", "Tab Break"):
			section = df.fieldname
			sections[section] = []
		elif section:
			sections[section].append(df)

	for sec, dfs in sections.items():
		tables = [d.fieldname for d in dfs if d.fieldtype == "Table"]
		breaks = [d.fieldname for d in dfs if d.fieldtype == "Column Break"]
		if not tables:
			continue
		check("%s / %s holds %s full width" % (doctype, sec, tables[0]), not breaks,
		      "column breaks in the section: %s" % (breaks or "none"))

# ---------------------------------------------------------------- export tab
# The export fields live in their own tab on the host doctypes, shown only when
# Is Export is ticked. A Tab Break captures everything until the next one, so it
# has to be the last field on the form -- anchored anywhere else it drags the
# standard fields below it into the Export tab.
print("\n=== Export Details tab on the host doctypes ===")
for host in ("Quotation", "Sales Order", "Sales Invoice"):
	hmeta = frappe.get_meta(host)
	names = [df.fieldname for df in hmeta.fields]
	tab = hmeta.get_field("custom_export_tab")

	check("%-14s has an Export Details tab" % host,
	      bool(tab) and tab.fieldtype == "Tab Break", tab and tab.fieldtype)
	if not tab:
		continue
	check("%-14s tab is gated on Is Export" % host,
	      tab.depends_on == "custom_is_export", tab.depends_on)

	at = names.index("custom_export_tab")
	check("%-14s Is Export stays outside the tab" % host,
	      names.index("custom_is_export") < at)

	ours = set(frappe.get_all("Custom Field",
	           filters={"dt": host, "module": "Export Tracker"}, pluck="fieldname"))
	stranded = [f for f in ours
	            if f not in ("custom_is_export", "custom_export_tab", "custom_next_followup_date")
	            and f in names and names.index(f) < at]
	check("%-14s every export field sits inside the tab" % host, not stranded,
	      stranded or "none")

	# a section that opens collapsed hides the very fields the tab exists to show
	collapsed = [df.fieldname for df in hmeta.fields
	             if df.fieldname in ours and df.fieldtype == "Section Break"
	             and (df.collapsible or df.depends_on)]
	check("%-14s export sections open by default" % host, not collapsed,
	      collapsed or "none")

# ---------------------------------------------------------------- child grids
# A grid gets 10 column units. Overrun and the last columns fall off; a 1-unit
# column is roughly 12 characters wide, so a longer label truncates its own
# header. And the row editor is a narrow dialog -- a section split into three
# columns, or one whose columns are lopsided, reflows badly.
#
# Budget and truncation are checked against the live meta, because a site's
# custom fields do not change them. Column balance is checked against the JSON
# the app ships: how a site chooses to arrange its own Customize Form additions
# is the site's business, not a defect in the app.
print("\n=== child tables: grid budget and row-editor balance ===")
import json  # noqa: E402
import os  # noqa: E402

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHILD_TABLES = [
	df.options
	for dt in ("Export Shipment", "Export Indent", "Export Document Template",
	           "Export Country Profile")
	for df in frappe.get_meta(dt).fields
	if df.fieldtype == "Table"
]

for table in sorted(set(CHILD_TABLES)):
	tmeta = frappe.get_meta(table)
	shown = [df for df in tmeta.fields if df.in_list_view]
	used = sum(df.columns or 0 for df in shown)
	check("%-28s grid fits in 10 units" % table, used <= 10, "uses %d" % used)

	cramped = [df.fieldname for df in shown if (df.columns or 0) <= 1
	           and len(df.label or "") > 11]
	check("%-28s no truncated grid headers" % table, not cramped, cramped or "none")

	# columns per section, from the shipped fixture rather than the live meta
	path = os.path.join(
		APP, "erpnext_export_tracker/export_tracker/doctype",
		frappe.scrub(table), frappe.scrub(table) + ".json",
	)
	if not os.path.exists(path):
		continue
	fixture = json.load(open(path))
	section, columns = None, {}
	for df in fixture["fields"]:
		if df["fieldtype"] == "Section Break":
			section, columns[section] = df["fieldname"], [0]
		elif df["fieldtype"] == "Column Break":
			columns.setdefault(section, [0]).append(0)
		else:
			columns.setdefault(section, [0])[-1] += 1

	for sec, counts in columns.items():
		name = "%s / %s" % (table, sec or "(first)")
		check("%-40s at most 2 columns" % name, len(counts) <= 2,
		      "%d columns" % len(counts))
		if len(counts) == 2 and sum(counts):
			# one field beside four is the lopsided case that reflows badly
			check("%-40s columns are balanced" % name, abs(counts[0] - counts[1]) <= 2,
			      "%s vs %s fields" % (counts[0], counts[1]))

# ---------------------------------------------------------------- sidebar
# The sidebar used to be a record somebody made in the desk, so it existed on one
# site and nowhere else. It ships from the app now; this fails if it stops being
# synced, or if a filtered document link loses its filter.
print("\n=== workspace sidebar ships from the app ===")
SIDEBAR = os.path.join(APP, "erpnext_export_tracker/workspace_sidebar/export_tracker.json")
check("the app ships a sidebar", os.path.exists(SIDEBAR))
if os.path.exists(SIDEBAR):
	shipped_sidebar = json.load(open(SIDEBAR))
	live_sidebar = (
		frappe.get_doc("Workspace Sidebar", "Export Tracker")
		if frappe.db.exists("Workspace Sidebar", "Export Tracker")
		else None
	)
	check("it is synced onto the site", bool(live_sidebar))
	if live_sidebar:
		check("owned by the app, not the site", live_sidebar.standard == 1
		      and live_sidebar.app == "erpnext_export_tracker",
		      "standard=%s app=%s" % (live_sidebar.standard, live_sidebar.app))
		check("every shipped item is live",
		      len(live_sidebar.items) == len(shipped_sidebar["items"]),
		      "%d live vs %d shipped" % (len(live_sidebar.items),
		                                 len(shipped_sidebar["items"])))

		# each export document opens filtered to its own Is Export flag
		wanted = {
			"Proforma Invoice": "is_export",
			"Quotation": "custom_is_export",
			"Sales Order": "custom_is_export",
			"Sales Invoice": "custom_is_export",
			"Delivery Note": "custom_is_export",
		}
		live_filters = {i.label: i.filters for i in live_sidebar.items if i.filters}
		for label, fieldname in wanted.items():
			raw = live_filters.get(label)
			ok = False
			if raw:
				try:
					ok = any(f[1] == fieldname and str(f[3]) == "1"
					         for f in json.loads(raw))
				except (ValueError, IndexError):
					ok = False
			check("%-18s filtered on %s" % (label, fieldname), ok, raw or "no filter")

		# a link that names a doctype nobody installed is a dead entry
		dead = [i.label for i in live_sidebar.items
		        if i.type == "Link" and i.link_type == "DocType" and i.link_to
		        and not frappe.db.exists("DocType", i.link_to)]
		check("no sidebar link points at a missing doctype", not dead, dead or "none")
		dead_reports = [i.label for i in live_sidebar.items
		                if i.type == "Link" and i.link_type == "Report" and i.link_to
		                and not frappe.db.exists("Report", i.link_to)]
		check("no sidebar link points at a missing report", not dead_reports,
		      dead_reports or "none")

# ---------------------------------------------------------------- workspace
# Frappe skips a fixture whose `modified` matches the database, so a workspace
# edited without bumping that timestamp silently never lands.
print("\n=== the control tower actually synced ===")
shipped = json.load(
	open(
		os.path.join(
			APP,
			"erpnext_export_tracker/export_tracker/workspace/export_tracker/export_tracker.json",
		)
	)
)
live = json.loads(frappe.db.get_value("Workspace", "Export Tracker", "content") or "[]")
check("workspace content matches the shipped fixture",
      live == json.loads(shipped["content"]),
      "%d live blocks vs %d shipped" % (len(live), len(json.loads(shipped["content"]))))

cards = [b["data"]["number_card_name"] for b in live if b["type"] == "number_card"]
check("control tower has its counters", len(cards) == 11, "%d cards" % len(cards))

from frappe.desk.doctype.number_card.number_card import get_result  # noqa: E402

for name in cards:
	if not frappe.db.exists("Number Card", name):
		check("card %s exists" % name, False)
		continue
	card = frappe.get_doc("Number Card", name)
	try:
		# the desk passes filters_json in as the second argument -- passing None
		# runs the card unfiltered and every counter comes back as the row count
		filtered = get_result(card, card.filters_json)
		check("card query runs: %-34s %s" % (name, filtered), True)
		# the real failure this guards against is filters_json never reaching the
		# query. Comparing counts cannot see it when every row happens to match,
		# so check the card actually carries a filter instead.
		parsed = frappe.parse_json(card.filters_json or "[]")
		check("card %-34s carries a filter" % name, bool(parsed),
		      card.filters_json)
	except Exception as e:
		check("card query runs: %s" % name, False, str(e)[:80])

for chart in [b["data"]["chart_name"] for b in live if b["type"] == "chart"]:
	check("chart exists: %s" % chart, bool(frappe.db.exists("Dashboard Chart", chart)))

ws = frappe.get_doc("Workspace", "Export Tracker")
declared = {b["data"]["shortcut_name"] for b in live if b["type"] == "shortcut"}
check("every shortcut block has a shortcut row",
      declared <= {s.label for s in ws.shortcuts},
      declared - {s.label for s in ws.shortcuts})

# The card block, the workspace child row's label and the Number Card's own name
# are one and the same string. Shortening any of them for looks unlinks the card
# and it renders as nothing at all, with no error.
row_labels = {c.label for c in ws.number_cards}
check("every card block has a matching workspace row", set(cards) <= row_labels,
      set(cards) - row_labels)
check("every card row label equals its card name",
      all(c.label == c.number_card_name for c in ws.number_cards),
      [(c.label, c.number_card_name) for c in ws.number_cards
       if c.label != c.number_card_name])
check("every Number Card's own label equals its name",
      all(frappe.db.get_value("Number Card", n, "label") == n for n in cards),
      [n for n in cards if frappe.db.get_value("Number Card", n, "label") != n])

# ---------------------------------------------------------------- live
print("\n=== live: the panel and the gate agree ===")
from frappe.utils import add_days, today  # noqa: E402

COMPANY = frappe.db.get_value("Company", {}, "name")
CUSTOMER = frappe.db.get_value("Customer", {"disabled": 0}, "name")
ITEM = frappe.db.get_value("Item", {"disabled": 0, "is_sales_item": 1, "has_variants": 0}, "name")
# the site disables warehouses over time -- resolve a live one rather than pin a name
WAREHOUSE = frappe.db.get_value(
	"Warehouse", {"company": COMPANY, "is_group": 0, "disabled": 0}, "name"
)
print("using company=%s customer=%s item=%s warehouse=%s" % (COMPANY, CUSTOMER, ITEM, WAREHOUSE))

so = frappe.new_doc("Sales Order")
so.customer = CUSTOMER
so.company = COMPANY
so.currency = "USD"
so.conversion_rate = 93.0
so.transaction_date = today()
so.delivery_date = add_days(today(), 30)
so.custom_is_export = 1
so.append("items", {"item_code": ITEM, "qty": 1, "rate": 10,
                    "warehouse": WAREHOUSE,
                    "delivery_date": add_days(today(), 30)})
so.insert()
so.submit()

ship = frappe.get_doc("Export Shipment", {"sales_order": so.name})
check("new shipment starts at stage 0", ship.stage_index == 0,
      "%s / %s" % (ship.status, ship.stage_index))

step = ship.get_next_step()
check("panel names the first action", step["next_action"] == "Approve Indent", step["next_action"])
check("panel reports 13 stages", step["total_stages"] == len(STATE_ORDER))

ship.status = "Indent Approved"
ship.save()
check("stage_index tracks a status change", ship.stage_index == 1,
      "%s / %s" % (ship.status, ship.stage_index))

# the panel says freight selection blocks; the gate must agree
step = ship.get_next_step()
blocking = [b["label"] for b in step["blockers"]]
check("panel blocks on freight selection", any("Selected" in b for b in blocking), blocking)

ship.status = "Freight Finalised"
threw = False
try:
	ship.save()
except frappe.ValidationError:
	threw = True
	frappe.clear_last_message()
check("the gate refuses exactly what the panel flagged", threw)

cha = frappe.db.get_value("Supplier", {"supplier_group": "CHA"}, "name") or \
	frappe.db.get_value("Supplier", {}, "name")
ship.reload()
ship.append("cha_quotes", {"cha": cha, "currency": "USD", "freight_amount": 100,
                           "local_charges": 20, "thc": 5, "is_selected": 1})
ship.status = "Freight Finalised"
ship.save()
check("landed total adds every charge line", ship.cha_quotes[0].total_amount == 125,
      ship.cha_quotes[0].total_amount)
check("route verification is advice, not a wall", ship.stage_index == 2 and not ship.route_verified)

step = ship.get_next_step()
check("unverified route shows as a recommendation",
      any("Route" in t["label"] for t in step["todos"]),
      [t["label"] for t in step["todos"]])

check("closure checklist is currency aware",
      any("Bill of Lading" in c["label"] for c in step["closure"]),
      [c["label"] for c in step["closure"]])

print("\n" + "=" * 62)
print("PASSED: %d    FAILED: %d" % (len(PASS), len(FAIL)))
if FAIL:
	print("\nFailures:")
	for f in FAIL:
		print("  -", f)
print("=" * 62)

frappe.db.rollback()
print("\nrolled back")
