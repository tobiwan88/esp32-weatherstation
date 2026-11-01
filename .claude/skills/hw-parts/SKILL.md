---
name: hw-parts
description: Use when choosing, adding or swapping parts, checking a circuit against a datasheet or app note, writing datasheet cards, regulator design checks (calc/buck.py, MISSING rows), checking fab stock and price (e.g. JLCPCB/LCSC), setting BOM alternates, generating BOM/CPL with rotations, or preparing a PCB assembly order. Read hw-base first.
---

# Parts, datasheets, stock, ordering

Read `hw-base`, then the board's `BOARD.md` (decisions, commands, order checklist) and `board.yaml`.

## Choosing a part (review)
- Start from the requirement: function, supply voltage and current, package, temperature, the datasheet's application circuit.
- Collect 2-3 candidates from the fab library; stock and price with the lookup tool in `BOARD.md`.
- Basic first, at selection time: for every passive pick a basic value and do the divider/threshold math with it, rather
  than choosing an exact value and hunting a basic part later. Other parts add a setup fee (gate counts them).
- Fit to the power cycle: warm-up, minimum on-time, required sampling rate, current per phase (hw-base requirements).
- Cost per finished unit, including modules and sensors bought outside the fab: write it into `BOARD.md` when it changes.
- The fab listing's maker must match the datasheet's maker. Same series name from another maker = another drawing.
- Stock covers boards x parts per board (gate FAILs below 1x, flags LOW STOCK below 2x).
- Compare the footprint's land pattern and pin 1 with the datasheet drawing, not only the package name.
- Add the part to the schematic generator with its fab part number; no number = not assembled.
- Place it in the layout generator, outside keepouts (kicad-layout).
- A module or pin-compatible swap may change firmware config or pin maps: check and note it.

## Datasheet card (every IC and critical passive)
- One file `parts/<MPN>.yaml`: `source.url` (manufacturer site, not a distributor listing or third-party design), `source.revision`, and `values` with a `section` each. Format: an existing card.
- Not read yet: `value: null`. Datasheet silent: `value: null, section: not stated`. Never fill a value from memory or a reference design.
- Extraction: the helper prompt `hardware/agents/datasheet_extract.md`. Check each number against the PDF page yourself before it goes into the card.
- Download: the maker's own URL first; fab/distributor datasheet links often return an HTML page. Each download goes to
  its own new folder; check the `%PDF` header; read with `pdftotext -layout` or by viewing the page (figures, e.g. an
  application circuit, are images). Record file, revision and URL in the board's datasheet source list.
- When the user can download a file you cannot, ask; give the exact document and revision.
- Check against the schematic; tick each item in the card's `checklist:` with the confirming section:
  - decoupling per supply pin: count, value, placement
  - enable/reset RC, pull-ups, strapping pins and their levels
  - regulator: divider, input/output caps, inductor (`calc/buck.py`)
  - inductor saturation above peak current with margin; capacitor DC-bias derating at the operating voltage (`calc/buck.py`)
  - USB-C sink: CC pull-downs; ESD array pinout vs data lines (review)
  - I2C: addresses unique, pull-up sizing for bus load (review; script candidate)
  - thermal: exposed pad, dissipation, distance to sensors (review; script candidate)
  - layout notes: turn them into `critical.yaml` entries (kicad-layout)
- `MISSING`: a card or profile value is still `null`. `WARN (unsourced)`: a value has no section or source. Fix both before ordering.

## Swapping a value or part
- Recompute every formula the part sits in (regulator feedback, current limits, thermistor thresholds) with the new value
  and the datasheet limits (for example a maximum divider resistance); record the shift in the note (e.g. "+0.9 C").
- Then follow hw-base "Changing a decision" for every copy of the old value.

## Stock and alternates
- List substitutes in `board.yaml` `alternates`, each with a `note` of what else must change.
- When a part runs short the gate names the first in-stock alternate. It never swaps silently: change the generator and follow the note.
- Volatile stock: consider buying the part into the fab's parts inventory ahead (review).

## Fab outputs
- Confirm every IC, connector and polarised part in the fab's placement preview. Fix a wrong one in the board's rotation-correction table (`BOARD.md`), never in the CPL (review).
- The stackup in `board.yaml` is part of the order. Cross-check `calc/impedance.py` with the fab's calculator (a human runs it); write its inputs and result into the order notes (review).

## Before ordering
- Gate with the stock check for the order quantity, right before ordering, on a clean committed tree (command in `BOARD.md`). At order time `MISSING` fails.
- Walk the board's order checklist: PCB and assembly options, placement preview, human KiCad review, connector pinouts vs the mating module (review).

## Pitfalls
| Symptom | Cause | Fix |
|---|---|---|
| Stock check fails | part out of stock | alternate from `board.yaml`, follow its note |
| Stock drops between check and order | volatile part | re-check right before ordering; buy ahead |
| Unexpected cost | setup fees | basic-part equivalent |
| Part rotated wrong in preview | old rotation table | correction entry per footprint |
| Pin 1 or centre pad unclear | fab package name vs KiCad footprint differ | compare land patterns with the datasheet drawing |
| Part missing from BOM | no fab part number | add it, or it is hand-placed by design |
| Card value plausible but unsourced | filled from memory or notes | find its section, or set it `null` |
| Datasheet download is an HTML page | distributor link | maker URL, or ask the user for the PDF |
| Footprint from one maker, part from another | same series name, other maker | get the listed maker's drawing |
| Sensor fine on the bench, useless in the field | needs continuous sampling or long warm-up | check against the power cycle at selection |
