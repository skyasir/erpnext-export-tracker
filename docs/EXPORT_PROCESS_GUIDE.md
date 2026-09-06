# Export Process — Step-by-Step Operating Guide

How to run one export consignment end to end, from first contact to EBRC, in
ERPNext with the Export Tracker app.

Every step lists **who** does it, **where** it happens, **what to fill in**, and
**what the system will refuse to let you skip**. Section references in brackets
(e.g. *SOP G.c.i.5*) point back to the *Export Quotations to Bank Closure* SOP.

> Values specific to the company (IEC code, GSTIN, PAN, bank account, SWIFT) are
> **not written into this guide** — they live in **Export Tracker Settings** in
> the database. This file is version-controlled and may be public.

---

## Contents

- [Part 0 — One-time setup](#part-0--one-time-setup)
  - [0.7 How the form is laid out](#07-how-the-form-is-laid-out)
  - [0.8 The next-step panel](#08-the-next-step-panel--read-this-before-anything-else)
  - [0.9 Country profiles](#09-country-profiles--where-a-destinations-rules-live)
- [Part 1 — Enquiry and requirement gathering](#part-1--enquiry-and-requirement-gathering-sop-a-b)
- [Part 2 — Quotation](#part-2--quotation-sop-c)
- [Part 3 — Follow-up and revision](#part-3--follow-up-and-revision-sop-d-e)
- [Part 4 — Finalisation](#part-4--finalisation-sop-f)
- [Part 5 — Indent](#part-5--indent-sop-ga)
- [Part 5b — Production readiness](#part-5b--production-readiness-sop-section-12)
- [Part 6 — Freight and CHA comparison](#part-6--freight-and-cha-comparison-sop-gci1-2)
- [Part 7 — Dispatch planning and container booking](#part-7--dispatch-planning-and-container-booking-sop-gci3-4)
- [Part 8 — Pre-shipment documents](#part-8--pre-shipment-documents-sop-gci5)
- [Part 9 — Loading, sealing and e-sealing](#part-9--loading-sealing-and-e-sealing-sop-gci6-7)
- [Part 10 — Export invoice and packing list](#part-10--export-invoice-and-packing-list)
- [Part 11 — CHA checklist, shipping bill, e-seal, e-way bill](#part-11--cha-checklist-shipping-bill-e-seal-e-way-bill)
- [Part 12 — Post-shipment documents](#part-12--post-shipment-documents-sop-gcii)
- [Part 13 — Letter of Credit](#part-13--letter-of-credit-sop-gciii3g)
- [Part 14 — Document submission](#part-14--document-submission)
- [Part 15 — Payment follow-up](#part-15--payment-follow-up-sop-gh)
- [Part 16 — Bank closure: XAR → bank → EBRC](#part-16--bank-closure-xar--bank--ebrc-sop-i)
- [Part 17 — Export incentive](#part-17--export-incentive-sop-j)
- [Part 18 — Reports and daily reminders](#part-18--reports-and-daily-reminders)
- [Appendix A — Workflow actions and who can take them](#appendix-a--workflow-actions-and-who-can-take-them)
- [Appendix B — Every gate and its exact message](#appendix-b--every-gate-and-its-exact-message)
- [Appendix C — Field-to-document map](#appendix-c--field-to-document-map)
- [Appendix D — Troubleshooting](#appendix-d--troubleshooting)

---

## Part 0 — One-time setup

Do this once. Everything afterwards depends on it.

### 0.1 Export Tracker Settings

**Who:** System Manager or Accounts Manager
**Where:** *Export Tracker → Setup → Export Tracker Settings*

| Section | Field | What goes in it |
|---|---|---|
| Exporter Details | IEC Code | Your Importer-Exporter Code — prints on every export document |
| | End Use Code | The end-use code printed on the invoice |
| | PAN No | Company PAN |
| | Exporter Address | The address block exactly as it should print (use line breaks) |
| | Telephone / Email | Printed under the exporter block |
| | Authorised Signatory | Name printed above "Authorised Signature" |
| | Default Description of Goods | The heading printed above the item rows, e.g. *Poultry Keeping Equipments & parts in ckd condition* |
| | Invoice Declaration | The declaration sentence at the foot of the invoice |
| Banker Details | Bank Name / Address / A/C No / IFSC / SWIFT | Prints as the **OUR BANKERS** block on the export invoice and drives the bank letters |
| Shipment Defaults | Default Pre-Carriage By | e.g. *BY ROAD* |
| | Default Place of Receipt | e.g. your city |
| | Default Port of Loading | e.g. *NHAVA SHEVA SEA PORT, INDIA* |
| | Default Country of Origin | *INDIA* |
| | Default Insurance Company | Your marine insurer |
| | Export Incentive Consultant | The agency that files your incentives |
| Reminders | Enable Reminders | On by default |
| | Notify Users With Role | Who gets the sales-side nudges (default *Sales User*) |
| | Notify Accounts Role | Who gets the closure nudges (default *Accounts User*) |
| | Quotation Follow-up Reminder Days | Default 7 |
| | Document Alert Days Before ETD | Default 7 |
| | XAR Pending Days After Full Payment | Default 7 |
| | EBRC Pending Days After XAR | Default 15 |
| | Realisation Period (Months) | Default 9 — drives the realisation clock in the ageing report |

**Anything left blank here simply prints blank on the documents.** Fill the
exporter and banker blocks before issuing a real export invoice.

### 0.2 Invoice numbering

The install adds **`EXP/.###`** to the Sales Invoice naming series without
touching the existing `SINV-.YY.-` series.

**Where:** *Settings → Naming Series* → select **Sales Invoice** → set the
current value for the `EXP/` series so your next export invoice continues from
your existing number (e.g. set 420 to make the next one EXP/421).

### 0.3 Charge accounts — read this one carefully

The Ex-Works → freight → certification → insurance → CIF build-up on the invoice
comes from **Sales Taxes and Charges** rows of type **Actual**.

> **India Compliance will reject a GST account head on an export invoice** with
> *"Cannot charge GST in Row #1 since export is without payment of GST"*.
> Use ordinary expense heads instead — e.g. a *Clearing & Forwarding Charges –
> Export* account for freight and certification, and an *Insurance Charges*
> account for insurance. Never point these rows at Output Tax IGST/CGST/SGST.

Create one Sales Taxes and Charges Template per common shipment pattern, or add
the rows manually per invoice.

### 0.4 CHA suppliers

**Where:** *Buying → Supplier*
The `CHA` supplier group already exists. Create each clearing agent as a
**Supplier** in that group. You cannot compare freight quotes from agents who do
not exist as suppliers.

### 0.5 Document templates

**Where:** *Export Tracker → Setup → Export Document Template*

Installed out of the box:

| Template | Applies when |
|---|---|
| Standard – Direct through Client | fallback for any destination |
| Standard – Through Bank | route is Through Bank |
| Standard – Through Letter of Credit | route is LC |
| Nigeria – Standard | destination Nigeria (adds SONCAP + CCVO) |
| Uganda – Standard | destination Uganda (adds SGS) |
| Nepal – Standard / Bhutan – Standard | adds the Letter of Undertaking |
| Sri Lanka – Standard | adds the ISFTA certificate of origin |

Matching is **most-specific-first**: country + route → country → route →
fallback. Add your own template for any new destination that needs special
certification; set *Destination Country* and leave *Payment Route* as **Any** to
cover all routes for that country.

Each row carries: **Document**, **Stage** (Pre-Shipment / Post-Shipment),
**Required**, **Responsibility** (Export Dept / CHA / Accounts / Consultant /
Bank / Customer / Insurer) and **Remarks**. Only rows marked *Required* block the
workflow.

### 0.6 Roles

No new roles are created. The workflow uses the standard ones:

| Role | Does |
|---|---|
| Sales User | day-to-day export desk work |
| Sales Manager | indent approval, document submission |
| Accounts User | payment confirmation, XAR, bank submission |
| Accounts Manager | EBRC generation |

---

### 0.6b Where the export fields are on an order or invoice

Tick **Is Export** on a Quotation, Sales Order or Sales Invoice and an **Export
Details** tab appears at the end of the form. Leave it unticked and the tab is
not there at all, so a domestic order is untouched.

| Tab section | Holds |
|---|---|
| Consignee & Buyer | consignee, buyer and notify party with their addresses, port of discharge, final destination, country of final destination, terms of payment, and the linked Export Shipment |
| Export Shipping Details *(invoice only)* | pre-carriage, place of receipt, port of loading, vessel / flight, country of origin, marks & nos, container no, net and gross weight, packages, and the goods description printed above the item rows |

These used to be a collapsible section wedged mid-form. Fifteen fields deep that
reads as clutter on a domestic order and as a scavenger hunt on an export one.

---

### 0.7 How the form is laid out

The Export Shipment form is split into **seven tabs**, so a 290-field record
reads as seven short ones.

| Tab | Holds |
|---|---|
| **Overview** | References, consignee & buyer, carriage & terms, shipment type, remarks |
| **Compliance** | The destination's requirements, Form M / BA, pre-shipment inspection, insurance |
| **Production** | Readiness summary and the weekly updates |
| **Freight & Booking** | CHA comparison, selected freight, route & additional charges, container booking and cut-offs, containers, packing |
The tabs run Overview, Compliance, Production, **Payment**, Freight & Booking,
Documents, Post-Shipment, **Closure** — payment before the freight is committed,
closure after the documents are out.
| **Documents** | Pre-shipment checklist, CHA checklist, shipping bill, e-seal, e-way bill, signatory |
| **Post-Shipment** | Post-shipment checklist, COO, bill of lading, submission, sent-to-client, original documents |
| **Payment** | Payment summary, the receipts table with an XAR against each, letter of credit |
| **Closure** | Closure checklist, bank closure, export incentive |

Sections used to *disappear* until the shipment reached their stage. They no
longer do — a gate could otherwise demand a field you could not see. Instead each
section starts **collapsed and opens itself** when the stage that needs it
arrives, so nothing is ever out of reach and nothing is in your way early.

**Every child table sits alone in a full-width section.** A Frappe section that
also contains a column break renders in two columns, which squeezes the grid to
half width and truncates its own headers. So the CHA comparison, the two document
checklists, the weekly production updates and the indent items each own their
section, and the scalar fields that go with them live in the section immediately
below — *Selected Freight* under the CHA grid, *Totals* under the indent items. A
test enforces this (`tests/test_form_guidance.py`), so it cannot be undone by
accident.

The Letter of Credit and the Form M, inspection, e-seal and original-document
blocks do not key off the stage at all — they show when the shipment actually
needs them (LC route selected, the destination requires an inspection, FCL rather
than LCL, the client asked for originals).

---

### 0.8 The next-step panel — read this before anything else

Every saved shipment carries a panel between the tab bar and the tab content, so
it stays on screen whichever tab you are on -- it belongs to the shipment, not to
one tab. It answers
the only three questions the desk actually has.

```
  Freight Finalised                              Stage 3 of 13 · 17%
  ▮▮▮▯▯▯▯▯▯▯▯▯▯

  Next: Plan Dispatch → Dispatch Planned

  BLOCKING (1)
   ● Dispatch Planned On                                          go

  RECOMMENDED (1)
   ● Route, transshipment and additional charges verified          go
```

- **Blocking** is what `validate()` will refuse to save. You cannot take the
  workflow action until every one is cleared.
- **Recommended** is what the SOP asks for but which is not worth losing your
  work over — an unverified route, a missing e-way bill number, a draft BL the
  client has not signed off, a CHA checklist not yet approved. You may advance
  past them, and if you do they **follow the shipment forward** rather than
  quietly disappearing, so a skipped step stays visible until it is done.
- **go** jumps straight to the field, opening the right tab on the way.
- A destination with a country profile shows its note here too — *"The buyer
  opens Form M and the BA number before shipment. SONCAP inspection applies."*

The panel is generated from the same list of requirements that `validate()`
enforces, so it can never promise something the save will then refuse.

---

### 0.9 Country profiles — where a destination's rules live

**Where:** *Export Tracker → Setup → Export Country Profile*

The SOP is explicit that country rules must not be hard-coded. They are not: one
record per destination holds

- **Pre-Shipment Inspection Required** and the agency (SONCAP, SGS, …)
- **Form M / BA Required** — Nigeria's pre-shipment finance formality
- **Inland Haulage Required** — a landlocked destination such as Malawi
- default port of discharge, default incoterm, default certificate-of-origin type
- a **Special Requirement** note that shows on every shipment to that country
- **extra documents** appended to whatever the document template already loads

The install seeds Nigeria, Uganda, Malawi, Nepal, Bhutan and Sri Lanka. Add a
profile for a new destination and shipments to it pick the rules up on their own.

> **Shipments already in flight keep the flags they started with.** The profile
> is read when a shipment is created and whenever its destination changes — never
> retroactively. Switching a rule on today therefore cannot make a shipment that
> is already past that stage unsaveable. Tick the flag by hand on an individual
> shipment if you do want it applied.

---

## Part 1 — Enquiry and requirement gathering *(SOP A, B)*

### Step 1.1 — Record the lead
**Who:** Sales User · **Where:** *CRM → Lead* (or *Customer* if they already exist)

Set **Source** to reflect how they reached you — existing customer reference,
exhibition, old customer, Google, website, social media, management data.
This is what makes lead-source analysis possible later.

### Step 1.2 — Open an Opportunity
**Who:** Sales User · **Where:** *CRM → Opportunity*

Capture the requirement as it comes in by phone, email or WhatsApp. Log each
conversation as a **Comment** or **Communication** on the Opportunity so the
history stays on the record rather than in someone's inbox.

Set **Country** on the customer's address now — the shipment later uses it to
pick the right document template automatically.

---

## Part 2 — Quotation *(SOP C)*

### Step 2.1 — Create the Quotation
**Who:** Sales User · **Where:** *Selling → Quotation* (or *Create → Quotation* from the Opportunity)

**Tick `Is Export`.** This reveals the Export Details section and includes the
quotation in the export follow-up report.

### Step 2.2 — Fill the export details

| Field | Notes |
|---|---|
| Consignee Name / Address | Who receives the goods |
| Buyer Name / Address | Leave blank if the buyer is the consignee |
| Port of Discharge | e.g. *MOMBASA PORT* |
| Final Destination | e.g. *UGANDA* |
| Country of Final Destination | e.g. *UGANDA* |
| Terms of Payment | Free text as it should print, e.g. *100% ADVANCE* |
| Next Follow-up Date | Drives the follow-up reminder and report |
| Incoterm (standard field) | CIF, FOB, EXW … |
| Named Place (standard field) | The place that qualifies the Incoterm |

### Step 2.3 — Items, price and discount

Add items with quantity, UOM and rate. Rates come from the price list or from
management; **verify against a second team member working the same area** before
sending (*SOP C.9*). Use the standard discount fields for the discount structure.
Attach the shed layout from the design team to the Quotation (*SOP C.2*).

Make sure each item has an **HSN code** — it prints as the goods heading on the
invoice and feeds the incentive report.

### Step 2.4 — Freight in the quotation

Add freight, certification and insurance as **Sales Taxes and Charges** rows of
type *Actual*, using the non-GST heads from step 0.3. Quote CIF and the build-up
carries all the way to the invoice unchanged.

### Step 2.5 — Internal discussion and management approval

Discuss material and technical details with the team, then get management's
approval before sending (*SOP C.11–C.12*). **This step is currently outside the
system by design** — approval happens by email or WhatsApp and is not recorded on
the Quotation. If you later want it enforced in ERPNext, it can be added as
role-restricted approval fields.

### Step 2.6 — Send it

Print or email the Quotation using your existing quotation print format, then set
**Next Follow-up Date**.

---

## Part 3 — Follow-up and revision *(SOP D, E)*

### Step 3.1 — Follow up
By email, WhatsApp or phone. After each contact, update **Next Follow-up Date**
and add a comment.

**Report:** *Export Quotation Follow-up* lists every open export quotation with
days since last activity and whether the follow-up is overdue. Tick
**Follow-up Overdue Only** for today's call list.

### Step 3.2 — Revise
Revisions cover pricing, quantity and freight (*SOP E*).

**Cancel → Amend** the Quotation. ERPNext creates a new version (`…-1`, `…-2`)
and the *Revision Of* column in the follow-up report shows the chain. Do not
edit a submitted quotation in place — you lose the record of what the customer
was originally quoted.

---

## Part 4 — Finalisation *(SOP F)*

### Step 4.1 — Proforma invoice
**Who:** Sales User · **Where:** the Quotation → *Create → Sales Order*, then print

Create the Sales Order from the accepted Quotation, then print it with the
**Export Proforma Invoice** format. It carries the exporter block, banker block,
consignee/buyer, terms and the full charge build-up.

### Step 4.2 — Order confirmation details
On the Sales Order, confirm and complete (*SOP F.2*):

| Field | Where it comes from |
|---|---|
| `Is Export` | **must be ticked** |
| Terms of Payment | the confirmed payment terms |
| Port of Discharge | confirmed with the customer |
| Consignee Name / Address, Buyer Name / Address | confirmed spellings — these print on the invoice and BL |
| Incoterm + Named Place | the shipment terms |
| Customer's Purchase Order No / Date (standard `po_no`, `po_date`) | from their PO |
| HSN code on each item | required for customs |

Attach the customer's purchase order to the Sales Order.

### Step 4.3 — Submit
**Submit** the Sales Order. On submit the system:

1. creates an **Export Shipment** (`EXP-SHP-YYYY-#####`) at status **Order Confirmed**
2. copies consignee, buyer, port of discharge, final destination and payment terms onto it
3. fills pre-carriage, place of receipt, port of loading and country of origin from Settings
4. ticks **Insurance Applicable** automatically if the Incoterm is CIF or CIP
5. writes the shipment name back into **Export Shipment** on the Sales Order

The Sales Order form now shows an indicator with the shipment's live status, and
*Create → Export Shipment* / *Create → Export Indent* buttons.

> A Sales Order **without** `Is Export` creates nothing. Domestic orders are
> untouched.

> If you part-ship an order, use *Create → Export Shipment* again for the second
> consignment. Each shipment carries its own shipping bill, BL, XAR and EBRC.

---

## Part 5 — Indent *(SOP G.a)*

Replaces the Excel indent.

### Step 5.1 — Generate it
**Who:** Sales User · **Where:** submitted Sales Order → *Create → Export Indent*

Items, quantities, UOMs, rates and HSN codes copy across; totals compute
automatically.

### Step 5.2 — Production confirms the technical details
**Who:** Manufacturing / Stock Manager · **Where:** the Export Indent

Fill **Technical Specification** per item and **Technical Remarks** for the
consignment, then tick **Production Confirmed**. The system stamps who confirmed
it and when, and status becomes *Production Confirmed*.

### Step 5.3 — Management approves
**Who:** Sales Manager · **Where:** the Export Indent

Tick **Management Approved**. Stamped with user and date; status becomes
*Management Approved*.

> **Gate:** ticking Management Approved before Production Confirmed is refused —
> *"Production must confirm the technical details before management approval."*

### Step 5.4 — Advance the shipment
**Who:** Sales Manager · **Where:** the Export Shipment → *Actions → Approve Indent*

Status → **Indent Approved**.

> **Gate:** if an Export Indent is linked and not yet approved, the action is
> refused and the message links you to the indent.

---

## Part 5b — Production readiness *(SOP section 12)*

**Who:** Production · **Where:** Export Shipment → *Production* tab

Once the indent is approved the plant owns the shipment until it is ready. The
SOP asks for a **weekly** update, so recording one is a single dialog rather than
a grid row.

**Production → Add Weekly Update** asks for week ending, production status, qty
completed, qty pending, packing status, expected completion and remarks, then
saves the shipment. The newest update becomes the shipment's headline production
status — which is what the *Production Pending* counter on the dashboard and the
weekly reminder both read — and the full history stays in **Weekly Updates**.

`Not Started → In Production → Partially Ready → Ready → Dispatch Planning`

If a shipment that is still moving has no update in the last seven days, it turns
up in the daily *"Weekly production update overdue"* mail.

---

## Part 6 — Freight and CHA comparison *(SOP G.c.i.1–2)*

### Step 6.1 — Collect quotes
Send the shipment details to your clearing agents and collect freight quotes.

### Step 6.2 — Enter them side by side
**Who:** Sales User · **Where:** Export Shipment → *Freight & Booking* → **Freight Comparison**

One row per forwarder. The **grid carries the five things you decide on**;
everything the SOP's comparison table asks for is in the row editor (click the
pencil) and in the Compare dialog below.

| In the grid | |
|---|---|
| **Forwarder / CHA** | the supplier |
| **Landed Total** | every charge line added up, computed for you |
| **Transit Days** | *SOP G.c.i.2.b* |
| **Free Days** | free days for unloading at destination, *SOP G.c.i.2.c* |
| **Selected** | tick the winner |

| In the row editor | |
|---|---|
| Quote Date, Currency, Container Type | what they quoted, and for what |
| Charges | Ocean / Air Freight, Local Charges, THC, Documentation, Haulage, Other Charges — the SOP's charge lines, totalled into Landed Total as you type |
| Schedule & Terms | Vessel, ETD, ETA, Transit Days, Free Days |
| Decision | Selected, Remarks |

The whole quote history stays on the shipment for the next negotiation.

### Step 6.3 — Select the winner

**Freight → Compare Freight Quotes** puts the quotes side by side the way the SOP
draws them — freight, local + THC, documentation + haulage + other, landed total,
transit, free days, ETD — and tags the **cheapest** and the **fastest**. One click
on *Select* picks that forwarder and closes the dialog.

Or tick **Selected** on a row directly. Either way the parent fields **Selected
CHA**, **Selected Freight**, **Transit Days** and **Free Days** mirror it
automatically, the vessel and ETA copy across if the shipment does not have them
yet, and ticking a second row clears the first.

> **Gates:**
> - Two rows selected → *"Only one CHA quote can be marked as Selected. Rows 1, 2 are all selected."*
> - No row selected → *"Mark one CHA quote as Selected before finalising freight. Compare the quotes on price, transit time and free days first."*

### Step 6.4 — Advance
*Actions → Finalise Freight*. Status → **Freight Finalised**.

---

## Part 7 — Dispatch planning and container booking *(SOP G.c.i.3–4)*

### Step 7.1 — Plan the dispatch with the plant
**Who:** Sales User · **Where:** Export Shipment → *Container & Dispatch*

Agree the dispatch date with the people responsible for dispatch, then set
**Dispatch Planned On**.

### Step 7.2 — Verify the route before you book *(SOP section 14)*
**Where:** Export Shipment → *Freight & Booking* → **Route & Additional Charges**

Before the booking goes out, check the route end to end and record it:
**Route**, **Transshipment Port**, **Destination Charges**, **Special Country
Charges**, and — for a landlocked destination such as Malawi — **Inland Haulage
Charges**, which only appears when the country profile says haulage is required.
Then tick **Route & Charges Verified**.

That tick is a *recommendation*, not a blocker: it shows in the next-step panel
and follows the shipment forward until it is done, but it will not stop you
booking a vessel at four in the afternoon.

### Step 7.3 — Book the container with the CHA *(SOP section 15)*
**Where:** Export Shipment → *Freight & Booking* → **Container Booking**

Record **Booking No**, **Booking Date** and **Voyage No** — the vessel name is
already on the Overview tab — then the four deadlines that decide whether the
cargo makes this sailing:

| Cut-off | What it gates |
|---|---|
| **Gate / Cargo Cut-off** | the container has to be inside the terminal |
| **SI Cut-off** | shipping instructions to the line |
| **VGM Cut-off** | verified gross mass declaration |
| **Documentation Cut-off** | the line's paperwork |

Within three days of any of them the shipment shows a **red or amber indicator**
at the top of the form, and the daily reminder mails the desk. Confirm size, type
and availability, then fill **Container Type** and **No of Containers** on the
*Container & Dispatch* section.

### Step 7.4 — Advance
*Actions → Plan Dispatch*. Status → **Dispatch Planned**.

> **Gates:**
> - *"Set Dispatch Planned On before moving past dispatch planning."*
> - For a destination whose profile requires it, **Form M No** and **BA No** —
>   see Part 8.0.

---

## Part 8 — Pre-shipment documents *(SOP G.c.i.5)*

### Step 8.0 — Destination compliance *(SOP sections 9 and 16)*
**Who:** Export Executive · **Where:** Export Shipment → *Compliance* tab

The **Destination Requirements** section shows which of the three switches the
country profile turned on for this shipment. Each one reveals its own block only
when it applies.

**Form M / BA** — Nigeria. The buyer opens Form M with their bank and gets a BA
number; nothing ships before both are in hand. Record **Form M No**, **Form M
Date**, **Form M Status**, **BA No**, **BA Date**, the approval date and a copy of
each. *Form M No* and *BA No* are **blocking** at Dispatch Planned.

**Pre-Shipment Inspection** — SONCAP for Nigeria, SGS for Uganda, whatever a new
profile names. Work it through
`Not Started → Agent Assigned → Requested → Scheduled → Completed → Draft Report
→ Client Approved → Final Report`, recording the agency, agent, location, request
and inspection dates, the report number and the report itself. The agency's
invoice goes in the same block — **Inspection Invoice No**, amount and
**Accounts Payment Status** — so Accounts can be handed it without a separate
mail.

> **Gate (Customs Docs Prepared):** the inspection has to be closed out — status
> *Final Report*, or a report number recorded. If this destination no longer
> needs one, untick **Pre-Shipment Inspection Required** on the shipment.

**Inland Haulage** — a landlocked destination. Turns on the haulage charge field
in *Route & Additional Charges*.

### Step 8.1 — Set the route and destination
**Who:** Sales User · **Where:** Export Shipment → *References*

- **Destination Country** — usually filled from the customer's address
- **Post-Shipment Document Route** — *Direct through Client*, *Through Bank* or
  *Through Letter of Credit*. This decides which post-shipment set you get, so
  set it before loading the checklist.

### Step 8.2 — Load the checklist
Click **Documents → Load Document Checklist**.

The system picks the most specific matching template and fills both the
pre-shipment and post-shipment tables. A message tells you which template was
used and how many rows were added. Loading again only adds what is missing, so it
is safe to re-run after changing the route; **Reload from Template (overwrite)**
clears both tables and starts fresh.

> If nothing matches: *"No Export Document Template matches destination X and
> route Y."* Either create a template or set **Document Template** by hand.

### Step 8.3 — Work the list
For each row: prepare the document, then fill **Document No**, **Date**, attach
the file, and tick **Prepared**.

The grid deliberately shows only **Document, Prepared and Document No** — those
are what you scan. **Required**, **Responsibility**, **Stage**, **Date**,
**Attachment** and **Remarks** are one click away in the row editor (the pencil),
and *Pending Export Documents* reports on responsibility across every shipment.

The standard pre-shipment list covers commercial invoice, packing list, SCOMET
letter, annexure, examination report, export value declaration, VGM, Form 13,
bill of lading and insurance — plus whatever the destination adds (SONCAP for
Nigeria, SGS for Uganda, and so on).

**Documents the app prints for you** (Export Shipment → *Print*):

| Print format | Covers |
|---|---|
| SCOMET Letter | the SCOMET declaration |
| Verified Gross Mass | one VGM form per container, from the Containers table |
| FEMA Declaration | the Rule-7 declaration naming exporter and customs broker |
| Customs Broker Authorization | authorises your CHA or courier (e.g. DHL) to clear on your behalf |
| Export Value Declaration | value build-up + the standard declarations |
| Letter of Undertaking | the customs undertaking |
| Insurance Declaration | the request to your marine insurer |

**Documents issued by someone else are never generated here** — the Certificate
of Origin (FIEO/MACCIA portal), the Bill of Lading (your forwarder), the marine
insurance policy (the insurer), SONCAP, SGS, the examination report and Form 13.
The app tracks who owes each one, whether it has arrived, and holds the file on
the checklist row via **Responsibility** and **Attachment**.

Before Container Loaded, fill the **Containers** table — one row per container
with its seal, packages, net and gross weight, plus the weighbridge details. That
one table drives the VGM form, the container rows on the invoice, and the packing
list's grouping and per-container totals. Then fill **Packing Details**: one row
per part per container. Package numbers (1 TO 4, 5 TO 129, …) are assigned
automatically, running consecutively across the whole list.

> Export documents print with **international digit grouping** (185,079.90), not
> the site's Indian lakh format (1,85,079.90), because they are read abroad.

### Sea and air produce different documents

Set **Mode** on the shipment. The same print formats then produce the right
variant:

| | Sea | Air |
|---|---|---|
| SCOMET addressed to | Customs Office (Sea) in Settings | Customs Office (Air) — Sahar Air Cargo Complex |
| SCOMET body | description and port, no HS code | HS code and the Category 3B/3D Appendix-3 wording |
| Packing List | grouped by container, NOTIFY block | straight list, BUYER block, no container rows |

Air courier shipments have no containers, so leave the Containers table empty —
the packing list prints the lines straight through and the VGM does not apply.

**Signatory** comes from the shipment's *Signatory & Customs Broker* section, and
falls back to Export Tracker Settings when blank — your sea documents are signed
by one person and your air ones by another. **Customs Broker / Courier** on the
same section drives the FEMA declaration and the authorisation letter.

### Step 8.4 — Insurance, if applicable
**Where:** Export Shipment → *Insurance*

1. Tick **Insurance Applicable** (auto-ticked for CIF/CIP).
2. Print the **Insurance Declaration** and send it to the insurer.
3. Set **Premium Request Raised to Accounts** when you ask Accounts to pay.
4. Set **Premium Paid On** when they pay.
5. Enter **Policy No** and **Policy Date** when the policy arrives.

### Step 8.5 — Advance
*Actions → Prepare Customs Docs*. Status → **Customs Docs Prepared**.

> **Gate:** every row marked *Required* must be ticked *Prepared*, or the system
> lists exactly what is outstanding:
> *"These required Pre-Shipment documents are not prepared yet: – Commercial Invoice – Packing List – SCOMET Letter …"*

---

## Part 9 — Loading, sealing and e-sealing *(SOP G.c.i.6–7)*

### Step 9.1 — Load and seal at the plant
**Who:** Sales User · **Where:** Export Shipment → *Container & Dispatch*

| Field | From |
|---|---|
| Container Loaded On | the loading date |
| Container No(s) | the container numbers, one per line |
| Customs Seal No | customs seal applied at the plant |
| Shipping Line Seal No | shipping line's seal |
| Total Net Weight (KGS) | weighbridge / packing figures |
| Total Gross Weight (KGS) | |
| Total No of Packages | |
| VGM Submitted | tick once VGM is filed |
| Form 13 Received from CHA | tick on receipt |

### Step 9.2 — Advance
*Actions → Confirm Loading*. Status → **Container Loaded**.

> **Gate:** *"Container loading is incomplete. Missing: Container Loaded On,
> Container No(s), Customs Seal No, Shipping Line Seal No"* — it names only what
> is actually missing.

### Step 9.3 — E-seal the container
Follow the online e-sealing procedure, then record **E-Seal No** and
**E-Sealed On**.

### Step 9.4 — Optional: Delivery Note
If you move stock with a Delivery Note, tick `Is Export` on it and set
**Export Shipment**. On submit it stamps the loading date, and copies the
shipping bill details and net weight onto the shipment if they are not already
there.

---

## Part 10 — Export invoice and packing list

### Step 10.1 — Create the Sales Invoice
**Who:** Sales User / Accounts · **Where:** Sales Order → *Create → Sales Invoice*

1. Set the naming series to **`EXP/.###`**.
2. Tick **`Is Export`**.
3. Set **Export Shipment** — this pulls the consignee, buyer, entire carriage
   grid, container number, weights, packages and terms of payment from the
   shipment in one go.
4. Check GST: **GST Category** should be *Overseas*, and
   **Is Export With Payment of GST** set according to how you are exporting.
5. Add the charge rows (freight / certification / insurance) as **Actual** rows
   using the non-GST heads from step 0.3.

### Step 10.2 — Complete the print-only fields

| Field | Prints as |
|---|---|
| Marks & Nos | the left-hand column beside the item rows |
| Container No | the `CONTAINER NO.: …` heading row |
| Description of Goods (heading) | the underlined heading above the items, with the HSN appended |
| Total Net Weight / Gross Weight / No of Packages | the three footer lines |
| Shipping Bill Number / Date, Port Code (India Compliance fields) | filed customs reference |

### Step 10.3 — Check the totals before submitting

The invoice reads, top to bottom:

```
TOTAL EX-WORKS AMOUNT          net total of the item rows
(+) FREIGHT …                  each Actual charge row, in order
(+) CERTIFICATION CHARGES …
(+) INSURANCE
TOTAL <INCOTERM> AMOUNT        ERPNext grand total
```

Because the charges are real Sales Taxes and Charges rows, the printed CIF total
is always the accounting grand total — the invoice cannot silently disagree with
the ledger.

### Step 10.4 — Submit and print

Submit, then print **Export Invoice** and **Export Packing List**.

On submit the invoice links itself to the shipment and pushes the invoice amount,
currency and outstanding onto it. If you forgot to set **Export Shipment**, the
system finds the shipment via the Sales Order behind the invoice lines.

### Step 10.5 — Advance the shipment
Enter the shipping bill details (Part 11), then *Actions → Mark Shipped*.

---

## Part 11 — CHA checklist, shipping bill, e-seal, e-way bill

### Step 11.1 — The CHA checklist *(SOP section 24)*
**Who:** CHA Coordinator · **Where:** Export Shipment → *Documents* → **CHA & Checklist**

The CHA gets the final documents and sends back a checklist to verify before they
file. Record **Documents Sent to CHA On**, attach the **CHA Checklist**, and walk
the status through
`Not Sent → Awaiting Checklist → Under Review → Corrections Sent → Approved`,
reviewing invoice, HSN, value, quantity, container and seal numbers, buyer,
consignee, port, country and weight against it. Setting it to *Approved* stamps
who approved it and when.

An unapproved checklist shows as a **recommendation** on the way to Shipped — it
will not block the save, but it stays on the panel until it is done.

### Step 11.2 — Shipping bill

**Who:** Sales User · **Where:** Export Shipment → *Documents* → **Shipping Bill**

| Field | Notes |
|---|---|
| Shipping Bill No | from the filed shipping bill |
| Shipping Bill Date | **starts the realisation clock** |
| FOB Value | as declared |
| Port Code | needed again at bank submission |
| Let Export Order Date | when LEO is granted |
| Examination Report | the customs examination report, if any |
| Shipping Bill Copy | the filed document |
| ETD / ETA, Vessel / Flight No | on the Overview tab |

### Step 11.3 — E-sealing after the shipping bill *(SOP section 26)*
**Where:** Export Shipment → *Documents* → **E-Seal / RFID**

Only for FCL — the block hides itself for LCL, where the line's own seal applies.
Record the **E-Seal No**, date, provider/site, the container it went on, and the
portal confirmation. Missing on an FCL shipment it shows as a recommendation, not
a wall.

### Step 11.4 — E-way bill *(SOP section 27)*
**Who:** Dispatch · **Where:** Export Shipment → *Documents* → **E-Way Bill**

**E-Way Bill No**, date, **Valid Upto**, **Vehicle No**, **Transporter**, **LR
No** and **LR Date**, plus a copy. The LR is one of the three documents an INR
shipment cannot close without.

*Actions → Mark Shipped*. Status → **Shipped**.

> **Gates:**
> - *"Cannot mark as Shipped. Missing: Shipping Bill No, Shipping Bill Date, ETD"*
> - Under an LC: *"Under a Letter of Credit the LC must be received before shipment. Set LC Received On."*
> - Under an LC: *"ETD 05.08.2026 is after the LC's Last Date of Shipment 01.08.2026."*

---

## Part 12 — Post-shipment documents *(SOP G.c.ii)*

Which set applies depends on **Post-Shipment Document Route**.

### 12.1 Common to all three routes

**Certificate of Origin** — set **Certificate of Origin Type**, then fill
**COO No** and **COO Date**:

| Type | How it is obtained |
|---|---|
| MACCIA / Federation | online application to the chamber of commerce |
| ISFTA (India Sri-Lanka FTA) | through your consultant |
| CCVO (Nigeria) | combined certificate of value and origin, for Nigeria |
| Not Applicable | no COO needed |

**Bill of Lading** — set **Bill of Lading Type**:

| Type | Then |
|---|---|
| Seaway Bill of Lading (Telex BL) | email it — fill BL No and BL Date |
| Original BL | courier the hard copy — also fill **Courier No** and **Couriered On**. The importer cannot clear the goods without it |

**Insurance** — as recorded in step 8.4.

### 12.2 Route: Direct through Client
Invoice, packing list, certificate of origin, bill of lading, insurance policy —
sent straight to the customer.

### 12.3 Route: Through Bank
Everything above **plus** the bank set, which the checklist lists for you:

| Document | Print format |
|---|---|
| Bill of Exchange | **Bill of Exchange** |
| Dispatch Declaration | **Dispatch Declaration** |
| Letter of Undertaking | **Letter of Undertaking** |
| Request Letter to bank for export bill on collection | **Request Letter to Bank** |
| Document Set for Our Bank | prepare two sets |
| Document Set for Consignee Bank | one for your bank, one for the consignee's |

The **Request Letter to Bank** automatically lists the enclosures from the
post-shipment checklist and flags any that are still **(PENDING)** — so you
cannot post an incomplete set without seeing it on the covering letter.

Record **Submitted To (Bank / Client)** with the consignee bank's name.

### 12.4 Route: Through Letter of Credit
The bank set above plus the LC copy — see Part 13.

### 12.5 Advance
*Actions → Prepare Post-Shipment Docs*. Status → **Post-Shipment Docs Prepared**.

> **Gates:**
> - all required post-shipment rows must be *Prepared*
> - *"BL / AWB No is required for post-shipment documents."*
> - *"Certificate of Origin type is MACCIA / Federation but the COO No is not filled in."*
> - *"Insurance is applicable but the Policy No has not been received yet."*

---

## Part 13 — Letter of Credit *(SOP G.c.ii.3.g)*

The **Letter of Credit** section appears only when the route is
*Through Letter of Credit*. Work it in order:

| Step | Field | Meaning |
|---|---|---|
| 1 | LC Draft Received On | the customer sends the draft LC |
| 2 | Terms & Conditions Reviewed | you have read the terms |
| 3 | Management Confirmation Taken | management has seen and accepted the terms |
| 4 | Acceptance Sent to Customer On | you confirm acceptance to the customer |
| 5 | LC No, LC Issuing Bank, **LC Received On** | the customer's bank issues the LC in your name |
| 6 | LC Expiry Date, Last Date of Shipment | the two deadlines that matter |
| 7 | Payment Released On | the bank releases payment after confirming with the issuing bank |

Two protections:

- you cannot mark the shipment **Shipped** before **LC Received On** is set
- an **ETD** later than **Last Date of Shipment** is refused outright

The daily reminder warns 15 days before either LC deadline.

---

## Part 14 — Document submission

### Step 14.1 — Get management's signature
**Who:** management · **Where:** Export Shipment → *Document Submission*

Tick **Signed by Management**. The system stamps **Signed By** and **Signed On**.
The SOP is explicit that bank documents cannot go without it.

### Step 14.2 — Build the document pack *(SOP section 33)*

**Documents → Download Document Pack** zips every file attached to the shipment
into one archive, foldered:

```
1 Pre-Shipment/   every checklist row with an attachment
2 Post-Shipment/  every checklist row with an attachment
3 Shipment/       shipping bill, examination report, BL, COO, e-way bill,
                  e-seal confirmation, inspection report, Form M, BA,
                  CHA checklist, EBRC
```

The zip is saved as an attachment on the shipment, so what was sent is on the
record. Rows whose file has since been deleted are listed rather than skipped
silently, and a shipment with nothing attached is refused with *"Nothing to pack
yet."*

### Step 14.3 — Send the documents
Fill **Courier / Reference No** and **Submitted To (Bank / Client)**.
**Documents Submitted On** stamps itself with today's date when you take the
action, and stays editable if the real date differs.

**Sent to Client** records the email — date, recipient, and the client's
acknowledgement when it comes back.

**Original Documents** *(SOP section 35)* — if the client wants originals, tick
**Original Documents Required** and the block opens: confirm the courier address
first (that tick is a recommendation on the way to Docs Submitted), then record
courier company, tracking number, dispatch date, delivery status and the list of
what went.

### Step 14.4 — Advance
**Who:** Sales Manager · *Actions → Submit Documents*. Status → **Docs Submitted**.

> **Gate:** *"Documents cannot be submitted without the management signature. Tick Signed by Management."*

---

## Part 15 — Payment follow-up *(SOP G.h)*

### Step 15.1 — Chase the balance
By email, phone and WhatsApp, as before. What is different is that you no longer
maintain the outstanding statement by hand.

### Step 15.2 — Record receipts
**Who:** Accounts User · **Where:** *Accounts → Payment Entry*

Allocate the receipt against the export invoice (or the Sales Order for an
advance). On submit, the shipment recalculates:

- **Amount Received**, **Outstanding**
- **Payment Status** — Unpaid / Partly Paid / **Fully Paid**
- **Final Payment Received On** — stamped when it goes fully paid

Cancelling a Payment Entry recalculates the same way, so the status never lies.

### Step 15.3 — Report to management
**Report:** *Export Outstanding Payment Statement* — invoice, date, terms,
invoice amount, received, outstanding, age in days, status and route, with
outstanding totalled per currency at the top and anything over 90 days in red.
This is *SOP G.h.2*, generated rather than typed.

---

## Part 16 — Bank closure: XAR → bank → EBRC *(SOP I)*

**This whole part is blocked until the final payment is in.** That is the SOP's
own precondition, enforced by the system.

### Step 16.0 — The closure checklist *(SOP section 37)*
**Where:** Export Shipment → *Payment & Closure* → **Closure Checklist**

A shipment is not closed because it sailed. The checklist above the bank-closure
fields shows what this shipment specifically needs, and it differs by currency:

| Invoice currency | Mandatory to close |
|---|---|
| Anything but INR | Invoice · Shipping Bill · Bill of Lading |
| **INR** | Shipping Bill · Invoice · **LR** |

Green means the system can see it; red means it is missing, with a **go** link to
the field. The same list appears on the next-step panel as the shipment reaches
EBRC, as a recommendation rather than a hard refusal — an EBRC that genuinely
arrived should never be blocked by a filing gap.

### Step 16.1 — Confirm payment received
**Who:** Accounts User · *Actions → Confirm Payment Received*. Status → **Payment Received**.

> **Gate:** *"Bank closure cannot start before the final payment is received.
> Outstanding on this shipment is $ 2,422.00."*

### Step 16.2 — Generate the XAR on the bank's website
**Who:** Accounts department · **Where:** the payment-receiving bank's portal

Confirm that the particular payment relates to this particular shipment. The
portal returns an **XAR number**.

Back in ERPNext, on the Export Shipment → *Bank Closure*:

| Field | Value |
|---|---|
| XAR No | as generated |
| XAR Date | as generated |
| Bank Charges Deducted | what the receiving bank deducted from your payment |

*Actions → Generate XAR*. Status → **XAR Generated**.

> **Gate:** *"XAR No and XAR Date are required once the XAR is generated."*

### Step 16.3 — Submit the details on the bank website
**Who:** Accounts / Export Dept (with bank login access from Accounts)

On the bank's site, fill in shipping bill number, port code, dates, the XAR
number, description, and the bank charges deducted. **Select the specific XAR
number** for which the payment was received.

Everything you need is on one screen in ERPNext: shipping bill number and date,
port code, XAR number and date, bank charges.

*Actions → Complete Bank Submission*. Status → **Bank Submission Done**;
**Bank Submission Completed On** stamps itself.

> **Gate:** *"Bank submission is incomplete. Missing: Shipping Bill No, Port Code"*

### Step 16.4 — Generate the EBRC on DGFT
**Who:** Accounts Manager · **Where:** the DGFT website

Submit the XAR details and shipping details, authorise with management's digital
signature, then download the generated **EBRC**.

In ERPNext: fill **EBRC No**, **EBRC Date**, attach the copy to **EBRC Copy**,
add **Closure Remarks** if needed.

*Actions → Generate EBRC*. Status → **EBRC Generated** — the shipment is closed.

> **Gate:** *"EBRC No and EBRC Date are required to close the shipment."*

### Step 16.5 — Watch the clock
**Report:** *Export Bank Closure Ageing* shows every shipment's closure stage:

| Stage | Meaning |
|---|---|
| Awaiting Final Payment | closure cannot start |
| Pending XAR | paid, XAR not generated |
| Pending Bank Submission | XAR done, bank site not completed |
| Pending EBRC (DGFT) | bank done, EBRC not generated |
| Closed – EBRC Generated | done |

plus **Realisation Due By** (shipping bill date + the configured months) and
**Days Left**, coloured red when overdue and amber inside 30 days.

---

## Part 17 — Export incentive *(SOP J)*

**Who:** Export Dept · **Where:** Export Shipment → *Export Incentive*

### Step 17.1 — Send the Master Details
**Report:** *Export Incentive Master Details* — the consultant handoff sheet, with
invoice number/date/value, consignee, destination, HSN codes, shipping bill
number/date, port code, port of loading, BL number/date, XAR number/date, bank
charges, payment date, EBRC number/date and the bank block. By default it lists
only shipments that already have an EBRC, since that is when the consultant can
file.

Menu → **Export** to Excel and send it. Then set **Master Details Sent On** and
**Incentive Status = Details Sent**.

### Step 17.2 — Record the outcome
When the scrip arrives, fill **RoDTEP Scrip No**, **RoDTEP Amount**,
**Duty Drawback Amount** and set **Incentive Status = Scrip Received**.

> **Consultant** defaults from Settings.

Other filings the SOP mentions — EPCG documentation, bank verification for the
shipping line — remain outside the system; attach their paperwork to the
shipment as a record.

---

## Part 18 — Reports and daily reminders

### The Export Control Tower
**Where:** the *Export Tracker* workspace

The workspace opens on eleven live counters, grouped the way the SOP groups them,
over a bar chart of every shipment by stage.

| Group | Counters |
|---|---|
| Commercial | Quotations Pending |
| Production | Indent Approval Pending · Production Pending |
| Payment | Payment Outstanding *(total value, not a count)* |
| Logistics | Freight Selection Pending · Booking Pending |
| Compliance | Form M Pending · Inspection Pending |
| Documentation | Shipping Bill Pending · BL Approval Pending |
| Closure | Closure Pending |

Each one clicks through to the filtered list. Below them, shortcuts to Export
Shipment, Export Indent, the status board and the pending-documents report.

### Reports
**Where:** *Export Tracker → Reports*

| Report | Use it for |
|---|---|
| Export Shipment Status | the board — every shipment, stage, ETD, shipping bill, BL, outstanding, XAR, EBRC. Hides closed shipments by default |
| Pending Export Documents | one row per missing document, with responsibility and days to ETD (red when past) |
| Export Outstanding Payment Statement | management payment reporting *(SOP G.h.2)* |
| Export Bank Closure Ageing | XAR/bank/EBRC stage and the realisation clock |
| Export Incentive Master Details | the consultant handoff *(SOP J)* |
| Export Quotation Follow-up | today's follow-up calls *(SOP D)* |

### Daily reminders

One job runs each day and emails two audiences:

**Sales role** — export quotations awaiting follow-up; pre-shipment documents not
ready with ETD inside the alert window; **vessel, SI, VGM and documentation
cut-offs within three days**; **Form M / BA still missing** and **inspections not
closed out**; **draft BLs the client has not approved after two days**; **weekly
production updates more than a week old**; LCs approaching expiry or last shipment
date.

**Accounts role** — fully paid shipments with no XAR after N days; XAR done with
no EBRC after N days; shipments whose realisation window is closing.

Thresholds are all in Settings. **If no outgoing Email Account is configured on
the site the job runs and sends nothing** — every alert is also one of the reports
above, so the information is never lost, only the email.

---

## Appendix A — Workflow actions and who can take them

| From | Action | To | Role |
|---|---|---|---|
| Order Confirmed | Approve Indent | Indent Approved | Sales Manager |
| Indent Approved | Finalise Freight | Freight Finalised | Sales User |
| Freight Finalised | Plan Dispatch | Dispatch Planned | Sales User |
| Dispatch Planned | Prepare Customs Docs | Customs Docs Prepared | Sales User |
| Customs Docs Prepared | Confirm Loading | Container Loaded | Sales User |
| Container Loaded | Mark Shipped | Shipped | Sales User |
| Shipped | Prepare Post-Shipment Docs | Post-Shipment Docs Prepared | Sales User |
| Post-Shipment Docs Prepared | Submit Documents | Docs Submitted | Sales Manager |
| Docs Submitted | Confirm Payment Received | Payment Received | Accounts User |
| Payment Received | Generate XAR | XAR Generated | Accounts User |
| XAR Generated | Complete Bank Submission | Bank Submission Done | Accounts User |
| Bank Submission Done | Generate EBRC | EBRC Generated | Accounts Manager |

---

## Appendix B — Every gate and its exact message

Gates come in two strengths. **Blocking** ones refuse the save; **recommended**
ones only show on the next-step panel and in the reports, and follow the shipment
forward until they are done.

### Blocking

Most of them share one message. The panel lists them individually before you ever
press the button, and the save repeats them if you do:

> **Freight Finalised is incomplete**
> Freight Finalised is not complete. Still needed:
> • One CHA / forwarder quote marked as Selected

| Stage | What it demands |
|---|---|
| Indent Approved | the linked indent is approved by management |
| Freight Finalised | exactly one selected CHA / forwarder quote |
| Dispatch Planned | Dispatch Planned On; **Form M No** and **BA No** where the destination profile requires them |
| Customs Docs Prepared | **Shipment Type (FCL / LCL)**; every required pre-shipment document prepared, listed by name; the **inspection closed out** where the destination requires one |
| Container Loaded | Container Loaded On, Container No(s), Customs Seal No, Shipping Line Seal No |
| Shipped | Shipping Bill No, Shipping Bill Date, ETD; under an LC, LC received from the customer |
| Post-Shipment Docs Prepared | every required post-shipment document; BL / AWB No; COO No when a type is set; Insurance Policy No when insured |
| Docs Submitted | Signed by Management |
| Payment Received | invoice fully paid — *"Full payment received"*, with the outstanding shown as a hint |
| XAR Generated | XAR No, XAR Date |
| Bank Submission Done | Shipping Bill No, Port Code |
| EBRC Generated | EBRC No, EBRC Date |

Four gates are comparisons rather than "is this filled in", and keep their own
wording:

| Where | Message |
|---|---|
| any save | *"Only one CHA quote can be marked as Selected. Rows 1, 2 are all selected."* |
| any save | *"Packing row 3 names container ABCD1234567, which is not in the Containers table."* |
| Shipped, under an LC | *"ETD 12-03-2026 is after the LC's Last Date of Shipment 28-02-2026."* |
| Export Indent | *"Production must confirm the technical details before management approval."* |
| Sales Order cancel | *"Export Shipment … is already at status …. Roll it back or delete it before cancelling this Sales Order."* |

### Recommended

These never refuse a save. They appear under **RECOMMENDED** on the panel, carry
forward if you advance past them, and feed the dashboard counters and the daily
mail.

| Stage | What it asks for |
|---|---|
| Freight Finalised | Route, transshipment and additional charges verified |
| Shipped | CHA checklist approved · E-Seal / RFID No (FCL only) · E-Way Bill No |
| Post-Shipment Docs Prepared | Client approved the draft BL |
| Docs Submitted | Courier address confirmed, when originals are required |
| EBRC Generated | the currency-specific closure checklist — Invoice + Shipping Bill + BL, or Shipping Bill + Invoice + LR for INR |

Every one of these is evaluated on **save**, not just on the workflow button — so
they hold for API writes and bulk edits too, and the panel is generated from the
same list, so it can never promise something the save will refuse.

---

## Appendix C — Field-to-document map

Where each printed value comes from.

### Export Invoice

| Printed as | Source |
|---|---|
| Invoice No. & Date | Sales Invoice name and posting date |
| EXPORTER block | Company name + Settings: Exporter Address, Telephone, Email |
| IEC Code / End Use Code / PAN No. | Settings |
| GSTIN/UIN | Sales Invoice **Company GSTIN** (India Compliance) |
| CONSIGNEE / BUYER | Sales Invoice Consignee / Buyer name and address |
| PRE CARRIAGE BY / PLACE OF RECEIPT | Sales Invoice, defaulted from Settings |
| VESSEL /FLIGHT NO. / PORT OF LOADING | Sales Invoice |
| PORT OF DISCHARGE / FINAL DESTINATION | Sales Invoice |
| COUNTRY OF ORIGIN / FINAL DESTINATION | Sales Invoice |
| TERMS OF DELIVERY & PAYMENT | Incoterm + Terms of Payment |
| OUR BANKERS block | Settings banker fields |
| MARKS & NOS. / CONTAINER NO. | Marks & Nos, Container No |
| goods heading | Description of Goods + distinct HSN codes of the items |
| item rows | Sales Invoice items — name, description, qty, UOM, rate, amount |
| TOTAL EX-WORKS AMOUNT | net total |
| charge lines | Sales Taxes and Charges rows |
| TOTAL … AMOUNT | grand total |
| weights and packages | Sales Invoice Net / Gross Weight, No of Packages |
| AMOUNT IN WORDS | ERPNext *in words* |
| Declaration | Settings Invoice Declaration |
| signature block | Company name + Settings Authorised Signatory |

### Shipment letters
All seven pull from the Export Shipment plus the linked invoice plus Settings —
no retyping. The **Request Letter to Bank** additionally lists the post-shipment
checklist as its enclosures and switches its own heading between *export bill on
collection* and *negotiation under Letter of Credit* based on the route.

---

## Appendix D — Troubleshooting

**"Cannot charge GST in Row #1 since export is without payment of GST"**
A charge row points at a GST account head. Change it to an ordinary expense head
(see step 0.3).

**The invoice prints with blank IEC / bank details**
Export Tracker Settings is not filled in. See step 0.1.

**"No Export Document Template matches destination X and route Y"**
Either set **Destination Country** and **Post-Shipment Document Route** on the
shipment, or create a template for that destination, or set
**Document Template** manually.

**No Export Shipment was created when I submitted the order**
`Is Export` was not ticked. Tick it, then use *Create → Export Shipment* on the
submitted order.

**Reminders are not arriving**
Check that an outgoing Email Account exists on the site, that
**Enable Reminders** is on, and that users actually hold the notification roles.
The reports show the same information regardless.

**I need to cancel an export Sales Order**
Delete or roll back the Export Shipment first. Cancellation is blocked while a
shipment has moved past *Order Confirmed*, so tracking is never orphaned.

**A shipment shows the wrong payment status**
Re-save the shipment, or cancel and re-submit the Payment Entry. Status is
recomputed from the linked invoice's outstanding amount every time either is
saved.
