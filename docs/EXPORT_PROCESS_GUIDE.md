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
  - [0.7 How the form reveals itself](#07-how-the-form-reveals-itself)
- [Part 1 — Enquiry and requirement gathering](#part-1--enquiry-and-requirement-gathering-sop-a-b)
- [Part 2 — Quotation](#part-2--quotation-sop-c)
- [Part 3 — Follow-up and revision](#part-3--follow-up-and-revision-sop-d-e)
- [Part 4 — Finalisation](#part-4--finalisation-sop-f)
- [Part 5 — Indent](#part-5--indent-sop-ga)
- [Part 6 — Freight and CHA comparison](#part-6--freight-and-cha-comparison-sop-gci1-2)
- [Part 7 — Dispatch planning and container booking](#part-7--dispatch-planning-and-container-booking-sop-gci3-4)
- [Part 8 — Pre-shipment documents](#part-8--pre-shipment-documents-sop-gci5)
- [Part 9 — Loading, sealing and e-sealing](#part-9--loading-sealing-and-e-sealing-sop-gci6-7)
- [Part 10 — Export invoice and packing list](#part-10--export-invoice-and-packing-list)
- [Part 11 — Shipping bill](#part-11--shipping-bill)
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

### 0.7 How the form reveals itself

The Export Shipment form does not show all of its sections at once. Each section
appears when the shipment reaches the stage that needs it, and **stays visible
from then on** — so you never lose sight of the CHA quotes after shipping.

| Section | Appears at |
|---|---|
| References, Consignee & Buyer, Carriage & Terms, Freight & CHA Comparison, Selected Freight, Letter of Credit, Remarks | immediately |
| Pre-Shipment Documents, Payment | Indent Approved |
| Container & Dispatch, Insurance | Freight Finalised |
| Shipping Bill | Customs Docs Prepared |
| Post-Shipment Documents, Certificate of Origin & Bill of Lading | Container Loaded |
| Document Submission | Shipped |
| Bank Closure | Docs Submitted |
| Export Incentive | Bank Submission Done |

**Every child table sits alone in a full-width section.** A Frappe section that
also contains a column break renders in two columns, which squeezes the grid to
half width and truncates its own headers. So the CHA comparison, the two document
checklists and the indent items each own their section, and the scalar fields that
go with them live in the section immediately below — *Selected Freight* under the
CHA grid, *Certificate of Origin & Bill of Lading* under the post-shipment
checklist, *Totals* under the indent items. A test enforces this
(`tests/test_section_visibility.py`), so it cannot be undone by accident.

Every section appears at or before the stage where its fields are first
demanded, so the disclosure can never block you from advancing. That property is
enforced by a test (`tests/test_section_visibility.py`), not just intended —
adding a gate that demands a field from a not-yet-visible section will fail it.

The Letter of Credit section is the one exception to stage-based reveal: it keys
off **Post-Shipment Document Route** instead, because the LC has to be accepted
long before shipment.

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

## Part 6 — Freight and CHA comparison *(SOP G.c.i.1–2)*

### Step 6.1 — Collect quotes
Send the shipment details to your clearing agents and collect freight quotes.

### Step 6.2 — Enter them side by side
**Who:** Sales User · **Where:** Export Shipment → *Freight & CHA Comparison* → **CHA Quotes**

One row per agent:

| Column | Meaning |
|---|---|
| CHA | the supplier |
| Quote Date | when they quoted |
| Currency | quote currency |
| Freight | base freight (row editor) |
| Other Charges | everything else they add (row editor) |
| **Total** | shown in the grid — freight + other charges, computed for you |
| **Transit Days** | shown in the grid — *SOP G.c.i.2.b* |
| **Free Days** | shown in the grid — free days for unloading at destination, *SOP G.c.i.2.c* |
| Container Type | what they quoted for |
| Selected | tick the winner |
| Remarks | anything worth remembering |

The grid shows exactly the three axes the SOP compares on — **Total, Transit
Days, Free Days** — plus the CHA and which one won, so the comparison is a single
glance. Freight and Other Charges live in the row editor (click the pencil);
Total is what you compare. The whole quote history stays on the shipment for the
next negotiation.

### Step 6.3 — Select the winner
Tick **Selected** on one row. The parent fields **Selected CHA**,
**Selected Freight**, **Transit Days** and **Free Days** mirror it automatically.
Ticking a second row clears the first.

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

### Step 7.2 — Book the container with the CHA
Confirm size, type and availability, then fill **Container Type** and
**No of Containers**.

### Step 7.3 — Advance
*Actions → Plan Dispatch*. Status → **Dispatch Planned**.

> **Gate:** *"Set Dispatch Planned On before moving past dispatch planning."*

---

## Part 8 — Pre-shipment documents *(SOP G.c.i.5)*

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
| Export Value Declaration | value build-up + the standard declarations |
| Letter of Undertaking | the customs undertaking |
| Insurance Declaration | the request to your marine insurer |

Certificates issued by third parties — SONCAP, SGS, the examination report,
Form 13 — are attachments; the app tracks who owes them and whether they have
arrived, using the **Responsibility** column.

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

## Part 11 — Shipping bill

**Who:** Sales User · **Where:** Export Shipment → *Shipping Bill*

| Field | Notes |
|---|---|
| Shipping Bill No | from the filed shipping bill |
| Shipping Bill Date | **starts the realisation clock** |
| Port Code | needed again at bank submission |
| Let Export Order Date | when LEO is granted |
| ETD / ETA | sailing and expected arrival |
| Vessel / Flight No | |

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

### Step 14.2 — Send the documents
Fill **Courier / Reference No** and **Submitted To (Bank / Client)**.
**Documents Submitted On** stamps itself with today's date when you take the
action, and stays editable if the real date differs.

### Step 14.3 — Advance
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
ready with ETD inside the alert window; LCs approaching expiry or last shipment date.

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

| Stage | Requirement | Message |
|---|---|---|
| Indent Approved | linked indent must be approved | *"Export Indent EXP-IND-… is not approved by management yet."* |
| Freight Finalised | exactly one selected CHA quote | *"Mark one CHA quote as Selected before finalising freight…"* |
| any save | at most one selected quote | *"Only one CHA quote can be marked as Selected. Rows 1, 2 are all selected."* |
| Dispatch Planned | dispatch date | *"Set Dispatch Planned On before moving past dispatch planning."* |
| Customs Docs Prepared | all required pre-shipment rows prepared | *"These required Pre-Shipment documents are not prepared yet: …"* |
| Container Loaded | loading date, container no, both seals | *"Container loading is incomplete. Missing: …"* |
| Shipped | shipping bill no + date, ETD | *"Cannot mark as Shipped. Missing: …"* |
| Shipped (LC) | LC received | *"Under a Letter of Credit the LC must be received before shipment…"* |
| Shipped (LC) | ETD within LC's last shipment date | *"ETD … is after the LC's Last Date of Shipment …"* |
| Post-Shipment Docs | all required rows prepared | *"These required Post-Shipment documents are not prepared yet: …"* |
| Post-Shipment Docs | BL number | *"BL / AWB No is required for post-shipment documents."* |
| Post-Shipment Docs | COO number if a type is set | *"Certificate of Origin type is … but the COO No is not filled in."* |
| Post-Shipment Docs | policy number if insured | *"Insurance is applicable but the Policy No has not been received yet."* |
| Docs Submitted | management signature | *"Documents cannot be submitted without the management signature…"* |
| Payment Received | invoice fully paid | *"Bank closure cannot start before the final payment is received. Outstanding on this shipment is …"* |
| XAR Generated | XAR no + date | *"XAR No and XAR Date are required once the XAR is generated."* |
| Bank Submission Done | shipping bill no, port code | *"Bank submission is incomplete. Missing: …"* |
| EBRC Generated | EBRC no + date | *"EBRC No and EBRC Date are required to close the shipment."* |
| Export Indent | production before management | *"Production must confirm the technical details before management approval."* |
| Sales Order cancel | no live shipment | *"Export Shipment … is already at status …. Roll it back or delete it before cancelling this Sales Order."* |

Every one of these is enforced on **save**, not just on the workflow button — so
they hold for API writes and bulk edits too.

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
