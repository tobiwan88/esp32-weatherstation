---
name: hw-parts
description: Use when choosing, adding or swapping parts, checking a circuit against a datasheet or app note, writing datasheet cards, regulator design checks (calc/buck.py, MISSING rows), checking fab stock and price (e.g. JLCPCB/LCSC), setting BOM alternates, cutting assembly fees, or accepting a BOM (gate 2). Read hw-base first; fab files and ordering are hw-fab-order.
---

# Parts, datasheets, stock (gate 2)

Read `hw-base`, then the board's `BOARD.md` (decisions, commands) and `board.yaml`. Fab files and the order are `hw-fab-order`.

## Choosing a part (review)
- Start from the requirement: function, supply voltage and current, package, temperature (including charging and cold
  limits), the datasheet's application circuit, a reference design that already works.
- Collect 2-3 candidates; stock and price with the fab lookup tool in `BOARD.md` (`hw-part-lookup`, `hw-researcher`).
  A search-engine miss is not a stock miss: look the part up in the fab's library before writing "not available".
- Basic first, at selection time: for every passive pick a basic value and do the divider/threshold math with it, rather
  than an exact value and a Basic hunt later. Reuse one fab number across designators; move 0603 to 0402 when the part is
  Basic (check the voltage rating against the net, e.g. a charger or panel net sees the TVS clamp, not the nominal volts).
  Every other part type adds a loading fee per order (`calc/bom_check.py` counts them).
- Fit to the power cycle: warm-up, minimum on-time, sampling rate, current per phase (`hw-requirements`).
- Cost per finished unit including modules and sensors bought outside the fab; write it into `BOARD.md` when it changes.
  Price tiers: the cost at the order quantity's tier, not the 1-piece price (`bom_check` uses the first tier, which
  overstates larger orders; say so when quoting).
- Marketplace modules and parts are allowed when the engineer says so; the fab-assembled route stays the default.
- The fab listing's maker must match the datasheet's maker. Same series name from another maker = another drawing.
- Stock covers boards x parts per board (gate FAILs below 1x, flags LOW STOCK below 2x).
- Compare the footprint's land pattern and pin 1 with the datasheet drawing, not only the package name.
- A footprint drawn by hand is checked twice before it goes on a board (review; gate):
  - each terminal from the package drawing (body size, terminal length and width) lies inside its land: compute the
    overlap, do not eyeball it. Read every dimension off its arrow ends: a gap between pad rows and a pad size look alike.
  - the fab's own footprint for the part number fits onto it (`fab_package.py --fit-only`, in the gate): pads within
    0.25 mm, or the difference explained.
- Symbols and footprints for parts without a library entry come from the generators (`build_symbols.py`,
  `build_footprints.py`), pad numbers as in the datasheet, source in the description.
- Add the part to the schematic generator with its fab part number; no number = not assembled (hand-soldered or DNP, say which).
- Place it in the layout generator, outside keepouts, with the datasheet's placement rules (edge distance, no copper under
  the body, airflow) as rule areas (`kicad-layout`). When a datasheet rule contradicts the engineer's wish, follow the
  datasheet and list it as a decision.
- A module or pin-compatible swap may change firmware config, address or pin maps: check and note it.
- Flexible BOM variants (cell chemistry, protection thresholds): same footprint, alternate in `board.yaml`, and the note
  says which thresholds change; check the protection IC's trip voltages against every chemistry the engineer wants to keep.

## Cutting assembly cost (numbers from `bom_check`)
- Count unique Extended types; try Basic equivalents, one value reused, fewer connector families.
- Hand-solder a few through-hole or fine connectors instead of paying per joint or a second side; keep it as a fallback
  option in `BOARD.md` until a real quote says it is needed.
- Splitting into boards doubles setup, stencil and shared Extended parts: show the delta before splitting.
- A part with a fee but small value (a PTC, a nice-to-have sensor): record the option and its fee in `PARTS-REVIEW.md`
  instead of adding it.

## Datasheet card (every IC and critical passive)
- One file `parts/<MPN>.yaml`: `source.url` (manufacturer site, not a distributor listing or third-party design),
  `source.revision`, and `values` with a `section` each. Format: `templates/parts-card.yaml`.
- Not read yet: `value: null`. Datasheet silent: `value: null, section: not stated`. Never fill a value from memory or a
  reference design. A substitute document (sibling part, no public datasheet): every value tagged `unverified: <source>`,
  and the bring-up list gets the check that proves it (address ACK, chip-id read).
- Extraction: `hw-datasheet-extractor`. Check each number that drives a decision against the PDF page yourself.
- Download: the maker's own URL first; fab/distributor links often return an HTML page. Each download goes to its own new
  folder; check the `%PDF` header; read with `pdftotext -layout` or view the page (figures are images). Record file,
  revision and URL in the board's datasheet source list. Maker sites with direct links work; the engineer can download
  what you cannot: ask, naming the exact document and revision.
- Check against the schematic; tick each item in the card's `checklist:` with the confirming section:
  - decoupling per supply pin: count, value, placement
  - enable/reset RC, pull-ups, strapping pins and their levels, power-on register defaults
  - regulator: divider, input/output caps, inductor (`calc/buck.py`); saturation above peak current; DC-bias derating
  - USB-C sink: CC pull-downs; ESD array pinout vs data lines (review)
  - I2C: addresses unique, pull-up sizing for bus load and cable (`calc/i2c_bus.py`)
  - thermal: exposed pad, dissipation, distance to sensors (`critical.py` `thermal_distance`)
  - layout notes: turn them into `critical.yaml` entries (`kicad-layout`)
- `MISSING`: a card or profile value is still `null`. `WARN (unsourced)`: no section or source. Fix both before ordering.

## Swapping a value or part
- Recompute every formula the part sits in (regulator feedback, current limits, thermistor thresholds) with the new value
  and the datasheet limits (a maximum divider resistance); record the shift in the note (e.g. "+0.9 C").
- Then follow `hw-base` "Changing a decision" for every copy of the old value.

## Stock and alternates
- List substitutes in `board.yaml` `alternates`, each with a `note` of what else must change.
- When a part runs short the gate names the first in-stock alternate. It never swaps silently: change the generator and follow the note.
- Volatile stock: consider buying the part into the fab's inventory ahead (review).

## Pitfalls
| Symptom | Cause | Fix |
|---|---|---|
| Stock check fails | part out of stock | alternate from `board.yaml`, follow its note |
| Stock drops between check and order | volatile part | re-check right before ordering; buy ahead |
| Unexpected cost | setup fees, price tier | Basic equivalent; price at the order quantity |
| Researcher says "not on the fab" | snippet search only | fab lookup tool by number and keyword |
| Land covers only part of the terminal | a gap dimension read as a pad size | overlap check; fab-footprint fit |
| Fab footprint numbers pins differently | other maker's numbering, same body | fit on geometry; confirm pairing (windings, pin 1) from the drawing |
| Pin 1 or centre pad unclear | package name vs KiCad footprint differ | compare land patterns with the datasheet drawing |
| Part missing from BOM | no fab part number | add it, or hand-placed/DNP by design |
| Card value plausible but unsourced | filled from memory or notes | find its section, or set it `null` |
| Datasheet download is an HTML page | distributor link | maker URL, or ask the engineer for the PDF |
| Footprint from one maker, part from another | same series name, other maker | get the listed maker's drawing |
| Sensor fine on the bench, useless in the field | continuous sampling or long warm-up | check against the power cycle at selection |
| Protection IC trips the other chemistry | thresholds fixed for one chemistry | list thresholds per chemistry; alternate part, same footprint |
| Datasheet of a sibling used silently | no public datasheet | tag unverified; bring-up check |
