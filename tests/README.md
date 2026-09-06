# UAT scripts

Two end-to-end scripts that exercise the app against a real site. They run
inside a transaction and **`frappe.db.rollback()`** at the end, so they leave no
data behind — safe to run against a restored production copy.

```bash
cd <bench>/sites
../env/bin/python ../apps/erpnext_export_tracker/tests/uat_core.py
../env/bin/python ../apps/erpnext_export_tracker/tests/uat_routes_and_hooks.py
```

| Script | Covers |
|---|---|
| `uat_core.py` | auto-create on export SO submit, no-create for domestic, CHA comparison + selection gates, country-driven checklist, every stage gate, the EXP invoice series and charge build-up, the Export Invoice print content, payment → XAR → bank → EBRC chain, Export Indent approval sequence, all 10 print formats, all 6 reports, cancel protection, reminder job |
| `test_print_formats.py` | every print format resolves to a template on disk, every template is registered, each `doc_type` matches its JSON fixture, and each format actually renders — catches the two causes of "No Preview Available" |
| `test_form_guidance.py` | the form can always tell the user what it wants and never hides it: no section is stage-gated out of existence, every tab has content, every requirement the panel reports names a real field, the panel's next action matches the workflow's own transitions, and the panel's blocking list is exactly what `validate()` refuses |
| `test_export_documents.py` | rebuilds a real 3-container shipment and checks the five documents we issue, their arithmetic, package numbering, and that no print format exists for the three third-party documents |
| `uat_routes_and_hooks.py` | the LC route gates, the Through Bank document set, part-shipment, the Delivery Note hook, advance-against-order payment, Payment Entry / Sales Invoice cancel paths, the invoice→shipment fallback lookup, the remaining country templates, reports with rows actually in them, PDF generation |

## Site constants resolve themselves

The scripts prefer the documented names — `Sundry Debtors - Corporate - SEPL`,
`Sales Account - Cages - SEPL - SEPL`, `P1 - Central / Main Store - SEPL` and so
on — and fall back to any live record matching the same filters when the site has
moved on. Chart-of-accounts restructuring, a disabled warehouse or an item that
stopped being a stock item used to read as a test failure; now it does not.

```python
def pick(doctype, preferred, filters):
	for name in preferred:
		# the preference has to satisfy the same filters -- an account that has
		# since become a group account still "exists" but cannot be posted to
		if frappe.db.get_value(doctype, dict(filters, name=name), "name"):
			return name
	return frappe.db.get_value(doctype, filters, "name")
```

Each run prints what it resolved. Edit the preference lists if you want a
specific account rather than whichever one matches.

## `uat_routes_and_hooks.py` does NOT fully roll back

`uat_core.py` and `test_form_guidance.py` roll back cleanly. **`uat_routes_and_hooks.py`
does not** — it submits and cancels stock and accounting documents, and ERPNext
commits internally during those, so `frappe.db.rollback()` cannot undo them.

Run the cleanup afterwards:

```bash
../env/bin/python ../apps/erpnext_export_tracker/tests/cleanup_uat_data.py
```

`cleanup_uat_data.py` only deletes rows whose **`owner` is the test user**
(`Administrator`) and works from an explicit **allow-list of records to keep** —
nothing is date-swept. Real users try the app on the same site and their drafts
are not residue. It also floors each naming series at the highest *surviving*
document, so rewinding a counter can never collide with a record it kept. Edit `KEEP_SO` / `KEEP_SI` / `KEEP_SE` / `KEEP_PE` and the
`BASELINE` naming-series values to match your site before running it, or it will
delete documents you wanted. It also removes orphaned GL and Stock Ledger
entries; because that last step uses raw SQL and bypasses the `Bin` cache, run
`repost_stock(item, warehouse)` for any item the tests moved.

## Editing a fixture JSON? Bump `modified`

Frappe compares a standard fixture's `modified` timestamp against the database
and **skips the import when they match** — or when the database copy is newer,
which it will be on any site where someone has touched the record.

- **Print formats.** Editing `doc_type` (or anything else) does nothing on
  migrate until you bump `modified`. Renaming is worse: the new name imports as a
  *new* record and the old one is left behind pointing at a template that no
  longer exists, which the UI reports as **"No Preview Available"**.
  `test_print_formats.py` fails on both.
- **Workspaces.** The same trap, and it is silent — the dashboard simply keeps
  the old layout. `test_form_guidance.py` compares the live `content` against the
  shipped fixture and fails if they have drifted.

## Number Cards name themselves from `label`

Setting `name` on a new Number Card is ignored — it takes its name from `label`.
A workspace block referencing a name that does not exist renders an **empty
card**, with no error anywhere. `test_form_guidance.py` checks every card block
resolves, that its query runs, and that a `Count` card is not returning the
unfiltered row count (which is what you get if `filters_json` never reaches
`get_result`).

## Known environment dependencies

- **PDF checks need `wkhtmltopdf` on PATH.** Without it the four PDF checks in
  `uat_routes_and_hooks.py` fail with `OSError: No wkhtmltopdf executable found`
  — an environment gap, not an app defect.
- **The Delivery Note section receipts stock first** to avoid
  `NegativeStockError`. If your site forbids the Material Receipt used there,
  skip that section.
- Charge rows must use **non-GST account heads**, or India Compliance rejects the
  export invoice. See the setup guide.

## Three layers can override the layout this app ships

None of them is visible from the doctype JSON, and each one silently wins:

1. **`field_order` Property Setter** — written whenever anyone opens Customize
   Form. `Meta.sort_fields()` ranks it above the DocType's own order, so a
   release that moves a field changes nothing on that site. On a child table it
   is worse: section breaks drift *after* the fields they introduce and the grid
   row editor renders as a jumble. The app re-asserts its order on every migrate
   (`after_migrate` → `resync_form_layouts.resync_all`), splicing site custom
   fields back in after their anchors.
2. **`GridView` in `__UserSettings`** — saved per user when someone configures a
   child grid's columns. It overrides `in_list_view` and `columns` completely;
   the saved Export CHA Quote layout here asked for seven columns totalling
   fourteen units against a ten-unit grid. `clear_stale_grid_views` drops the
   entries for this app's child tables.
3. **Stray `custom_column_break_*` Custom Fields** — Customize Form leaves these
   behind. They are preserved, not deleted, so an unlabelled one can still open
   an empty extra column in a section.

Diagnose the first by comparing `frappe.get_meta(dt).fields` order with
`tabDocField` order — if they differ, a property setter is winning.

## What these scripts do not cover

- **Client-side JS** — the Create buttons, the Load Document Checklist button,
  the CHA single-select clearing, the Sales Invoice fetch-from-shipment. Needs a
  browser. The guidance panel, tab order, CHA grid columns, the row editor
  layout and the Compare Freight Quotes dialog were verified once by driving
  headless Chrome over CDP with a minted session, which is how the three
  override layers above were found — none of them is visible to a Python test.
- **Workflow transitions and role permissions** — the scripts set `status` and
  save, which exercises the `validate()` gates but not the Actions menu or the
  per-transition `allowed` role. Everything runs as Administrator.
- **Visual fidelity of the printed output** against the department's sheet.
- **v16** — the suites pass on frappe 16.30 / erpnext 16.31 as well as v15.
