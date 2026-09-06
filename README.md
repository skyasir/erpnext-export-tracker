# Export Tracker

Exporter-side shipment tracking for ERPNext (India), built to Supreme Equipments'
*Export Quotations to Bank Closure* SOP.

Standard ERPNext already handles the sales cycle (Opportunity → Quotation → Sales
Order → Delivery Note → Sales Invoice → Payment Entry) and India Compliance
handles the GST/shipping-bill side. This app covers what neither does: the
**consignment process** from order confirmation to EBRC, and the **export
paperwork**.

## Architecture

Fields that belong to an order or an invoice live on **Sales Order / Sales
Invoice**, in an **Export Details tab** that appears only once *Is Export* is
ticked — so a domestic order looks exactly as it did before. The process lives on **Export Shipment**, one record per consignment,
linked to the order. That split matters because one order can ship in several
containers with separate shipping bills, BLs, XARs and EBRCs — and because the
process runs for months after the order is submitted.

```
Sales Order [Is Export ✓]
  └── on submit → Export Shipment  (EXP-SHP-2026-#####)
                    ├── CHA freight quotes (compare price / transit / free days)
                    ├── Pre-shipment document checklist
                    ├── Container, seals, e-sealing, VGM
                    ├── Post-shipment documents (route-dependent)
                    ├── Letter of Credit sub-flow
                    ├── XAR → bank submission → EBRC
                    └── Export incentive handoff
Sales Invoice EXP/### → the legal Export Invoice (own print format)
```

## DocTypes

| DocType | Purpose |
|---|---|
| **Export Shipment** | The spine. 13-state workflow, CHA comparison, document checklists, LC, bank closure, incentive. |
| **Export Indent** | SOP G.a — replaces the Excel indent. Production confirms technical details, then management approves. |
| **Export Document Template** | Country/route-driven checklists. Nigeria pulls SONCAP + CCVO, Uganda SGS, Nepal/Bhutan LUT, Sri Lanka ISFTA. |
| **Export Proforma Invoice** | The commercial offer, and the earlier document: a submitted proforma raises the Sales Order, which raises the shipment. Export details edited on it flow to the linked order. |
| **Export Country Profile** | Per-destination compliance rules — inspection agency, Form M / BA, inland haulage, COO type, extra documents. Nothing about a destination is hard-coded; add a profile and shipments to it pick the rules up. |
| **Export Tracker Settings** | IEC code, End Use Code, PAN, banker details, exporter block, reminder thresholds. |

## Workflow

`Order Confirmed → Indent Approved → Freight Finalised → Dispatch Planned →
Customs Docs Prepared → Container Loaded → Shipped → Post-Shipment Docs Prepared
→ Docs Submitted → Payment Received → XAR Generated → Bank Submission Done →
EBRC Generated`

Gates are enforced in `validate()` (not `before_workflow_action`, which is a
client-side event and would not hold on API writes):

- freight can't be finalised without exactly one **selected** CHA quote
- customs docs stage requires every *required* pre-shipment document prepared
- shipping requires a shipping bill number and date; under an LC it also requires
  the LC to be received, and blocks an ETD after the LC's last shipment date
- document submission requires the **management signature** (SOP G.c.ii.2.f.v)
- **bank closure cannot start until the invoice is fully paid** (SOP I)
- EBRC requires the XAR and the completed bank submission

Each gate is declared once, in `requirements_for(state)`, and that same list
feeds both `validate()` and the panel on the form — so the form can never
promise something the gate will refuse.

## The form

Thirteen states and ~290 fields only work if the desk can see where it is, so the
shipment form is built around two things.

**The next-step panel** sits at the top of every shipment: the current stage, a
progress bar, the name of the workflow button to press next, and exactly what is
still missing for it. Blocking items are what `validate()` will refuse; the
recommended ones are what the SOP asks for but is not worth losing your work
over — an unverified route, a missing e-way bill, a draft BL the client has not
signed off. Each line has a **go** link that jumps to the field, and skipped
recommendations follow the shipment forward instead of disappearing.

**Eight tabs** — Overview, Compliance, Production, Payment, Freight & Booking,
Documents, Post-Shipment, Closure. The next-step panel is not one of their fields:
it is drawn between the tab bar and the tab content, so it stays on screen
whichever tab you are on. Sections used to *hide* until the shipment
reached their stage, which meant a gate could demand a field the user could not
see; they are collapsible now and simply open themselves as the stage arrives.

Three buttons do the work that used to be manual:

- **Compare Freight Quotes** — the SOP's three-forwarder table side by side, with
  the cheapest and fastest tagged, and one click to pick the winner.
- **Add Weekly Update** — the production readiness update as a small dialog
  rather than a child-table row.
- **Fetch Payments** — pulls every submitted receipt booked against the order or
  the invoice into the payments table. XAR number and date are captured against
  the payment they belong to, so an invoice settled in parts carries an XAR for
  each, and an advance XAR can be reused on a later one. Only shown for a
  non-INR receipt.
- **Download Document Pack** — zips every file attached to the shipment, foldered
  pre-shipment / post-shipment / shipment.

## Print formats

| Format | On |
|---|---|
| Export Invoice | Sales Invoice |
| Export Packing List | Sales Invoice |
| Export Proforma Invoice | Sales Order |
| Bill of Exchange, Dispatch Declaration, Letter of Undertaking, Request Letter to Bank, Export Value Declaration, SCOMET Letter, Insurance Declaration | Export Shipment |

The Export Invoice is a replica of the department's existing sheet: exporter block
with IEC / GSTIN / End Use Code / PAN, consignee and buyer, the carriage grid,
banker block, HSN heading, marks & container column, the Ex-Works → freight → SGS
→ insurance → CIF build-up, weights, packages, amount in words and the
declaration. The charge lines come from Sales Taxes and Charges rows, so the
printed total always equals ERPNext's grand total.

## Reports

- **Export Shipment Status** — the board
- **Pending Export Documents** — what's missing, by responsibility, against ETD
- **Export Outstanding Payment Statement** — SOP G.h.2
- **Export Bank Closure Ageing** — XAR/bank/EBRC stage plus the realisation clock
- **Export Incentive Master Details** — the consultant handoff sheet (SOP J), exportable to Excel
- **Export Quotation Follow-up** — SOP D/E

## Export Control Tower

The workspace opens on eleven live counters grouped the way the SOP groups them —
commercial, payment, production, logistics, compliance, documentation, closure —
over a bar chart of shipments by stage. Quotations pending, indents awaiting
approval, production not ready, outstanding value, freight not selected, booking
not made, Form M pending, inspection open, shipping bill pending, draft BLs
awaiting the client, and shipments waiting to close.

## Reminders

A daily scheduler job emails the sales role (quotation follow-ups, documents not
ready before ETD, **vessel / SI / VGM / documentation cut-offs within three
days**, **Form M and inspection still open**, **draft BLs the client has not
approved**, **weekly production updates gone stale**, LC deadlines) and the
accounts role (XAR pending after payment, EBRC pending after XAR, realisation
window closing). Every alert is also a report, so a missing SMTP account costs
you the email, never the information.

## Documentation

**[docs/EXPORT_PROCESS_GUIDE.md](docs/EXPORT_PROCESS_GUIDE.md)** — step-by-step
operating guide for the whole flow: one-time setup, enquiry, quotation,
finalisation, indent, CHA comparison, container and sealing, both document sets,
the LC sub-flow, payment, bank closure and the incentive handoff. Includes every
validation message, the workflow/role matrix, a field-to-print map and
troubleshooting.

## Setup after install

1. **Export Tracker Settings** — fill in IEC code, End Use Code, PAN, authorised
   signatory, exporter address/tel/email, banker block (name, address, A/C, IFSC,
   SWIFT), default goods description, default port of loading.
2. **Naming series** — the install adds `EXP/.###` to the Sales Invoice series.
   Set its current value in *Setup → Naming Series* so the next export invoice
   continues your existing number.
3. **Charge heads** — create Sales Taxes and Charges rows of type *Actual* for
   local transportation & freight, SGS/SONCAP charges and insurance.
4. **CHA suppliers** — the `CHA` supplier group exists; add your clearing agents to it.
5. **Document templates** — the install seeds one per route plus country templates
   for Nigeria, Uganda, Nepal, Bhutan and Sri Lanka. Adjust to taste.
6. **Country profiles** — the install seeds Nigeria, Uganda, Malawi, Nepal, Bhutan
   and Sri Lanka. Add one for any new destination: tick what it needs (inspection,
   Form M / BA, inland haulage), name the agency, list its extra documents. New
   shipments to that country pick the rules up; shipments already in flight keep
   the flags they started with, so a rule added today cannot strand them.

## Scope note

Government and bank portals (ICEGATE e-sealing, the bank's XAR portal, DGFT
EBRC, MACCIA COO) have no usable API. This app captures the reference numbers,
dates, owners and attachments and chases the overdue steps; the portal data entry
itself stays manual.

## Compatibility

Frappe/ERPNext v15 and v16. Only `validate()` + `frappe.throw`, `db_set` and
standard doc events are used; no version-specific APIs.

If the site has ever had **Customize Form** opened on Export Shipment, frappe
stores a `field_order` property setter that outranks the app's own layout and
would pin the old single-column form. `patches/resync_form_layout.py` rebuilds
that list from the app's order, splicing any site custom fields back in after
whatever they were anchored to.

## Licence

MIT
