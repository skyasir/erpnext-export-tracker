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
| `test_section_visibility.py` | proves the progressive section-disclosure rules cannot deadlock the workflow: every field a gate demands sits in a section already visible at the stage the action is taken from |
| `uat_routes_and_hooks.py` | the LC route gates, the Through Bank document set, part-shipment, the Delivery Note hook, advance-against-order payment, Payment Entry / Sales Invoice cancel paths, the invoice→shipment fallback lookup, the remaining country templates, reports with rows actually in them, PDF generation |

## Before running: set the site constants

Both scripts have a block of constants near the top that are **specific to the
site** — customer, item, warehouse, income account, cost centre, debtors and bank
account. Change them to match your chart of accounts or the scripts will fail
with `LinkValidationError`.

```python
CUSTOMER = "..."
ITEM = "..."
COMPANY = "..."
WAREHOUSE = "..."
INCOME = "..."
COST_CENTER = "..."
DEBIT_TO = "..."
BANK = "..."
```

## `uat_routes_and_hooks.py` does NOT fully roll back

`uat_core.py` and `test_section_visibility.py` roll back cleanly. **`uat_routes_and_hooks.py`
does not** — it submits and cancels stock and accounting documents, and ERPNext
commits internally during those, so `frappe.db.rollback()` cannot undo them.

Run the cleanup afterwards:

```bash
../env/bin/python ../apps/erpnext_export_tracker/tests/cleanup_uat_data.py
```

`cleanup_uat_data.py` works from an explicit **allow-list of the records to keep**
— nothing is date-swept. Edit `KEEP_SO` / `KEEP_SI` / `KEEP_SE` / `KEEP_PE` and the
`BASELINE` naming-series values to match your site before running it, or it will
delete documents you wanted. It also removes orphaned GL and Stock Ledger
entries; because that last step uses raw SQL and bypasses the `Bin` cache, run
`repost_stock(item, warehouse)` for any item the tests moved.

## Known environment dependencies

- **PDF checks need `wkhtmltopdf` on PATH.** Without it the four PDF checks in
  `uat_routes_and_hooks.py` fail with `OSError: No wkhtmltopdf executable found`
  — an environment gap, not an app defect.
- **The Delivery Note section receipts stock first** to avoid
  `NegativeStockError`. If your site forbids the Material Receipt used there,
  skip that section.
- Charge rows must use **non-GST account heads**, or India Compliance rejects the
  export invoice. See the setup guide.

## What these scripts do not cover

- **Client-side JS** — the Create buttons, the Load Document Checklist button,
  the CHA single-select clearing, the Sales Invoice fetch-from-shipment. Needs a
  browser.
- **Workflow transitions and role permissions** — the scripts set `status` and
  save, which exercises the `validate()` gates but not the Actions menu or the
  per-transition `allowed` role. Everything runs as Administrator.
- **Visual fidelity of the printed output** against the department's sheet.
- **v16** — only run on v15 so far.
