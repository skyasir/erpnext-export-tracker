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
Invoice**. The process lives on **Export Shipment**, one record per consignment,
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

## Reminders

A daily scheduler job emails the sales role (quotation follow-ups, documents not
ready before ETD, LC deadlines) and the accounts role (XAR pending after payment,
EBRC pending after XAR, realisation window closing). Every alert is also a
report, so a missing SMTP account costs you the email, never the information.

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

## Scope note

Government and bank portals (ICEGATE e-sealing, the bank's XAR portal, DGFT
EBRC, MACCIA COO) have no usable API. This app captures the reference numbers,
dates, owners and attachments and chases the overdue steps; the portal data entry
itself stays manual.

## Compatibility

Frappe/ERPNext v15 and v16. Only `validate()` + `frappe.throw`, `db_set` and
standard doc events are used; no version-specific APIs.

## Licence

MIT
