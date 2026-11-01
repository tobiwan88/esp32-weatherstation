---
name: kicad-schematic
description: Use when creating or changing a KiCad schematic, editing a schematic generator (parts, nets, layout, wires, labels), reviewing a schematic for readability, or fixing ERC and net-intent failures. Read hw-base first; parts and datasheets are hw-parts, layout and KiCad GUI problems are kicad-layout.
---

# KiCad schematic

Read `hw-base`, then the board's `BOARD.md` and `board.yaml`. Gate: requirements, then BOM acceptance, then schematic (see `hardware/GATES.md`). A schematic is started only after the BOM gate passes.

## Source of truth
- Edit the generator, never the `.kicad_sch`. GUI edits are overwritten.
- Three files in `hardware/gen/`: `weatherstation_v1.py` (PARTS, NETS, drawing and routing), `layout_v1.py` (blocks, notes and part positions), `schkit.py` (sheet writer, maze router, root writer). `review_checks.py` is the geometric review.
- Nets are the truth: `check_nets` compares NETS with KiCad's own netlist. Run it after every generator run.

## The goal: a schematic an engineer can review
The schematic is where a human engineer checks the design and makes the major decisions. Every rule below serves that:
the reader must see what each block does, which part serves which pin, and where power flows, without tracing labels.
- Before drawing: a parts and circuit review (`<board>/PARTS-REVIEW.md`): every IC pin against its datasheet table,
  every value against the datasheet section, findings ranked A (wrong) / B (margin) / C (cleanup), each with a proposed
  fix. Netlist changes from that review are made only after the engineer decides. Never change topology silently.
- Each review round ends with the decisions the engineer must make, listed in the reply (not buried in files).

## Drawing rules (generator)
- Rails are power symbols, never wires: GND, +3V3, 3V3_SW, SYS, VBUS, USB_VBUS, PMID, REGN, GAS_VCC, BAT_PACK
  (`POWER_SYMBOLS`; non-library rails use `power:VCC` with the net as value). Each rail pin gets its own symbol at its stub
  end: vertical stubs point up (rail) or down (GND), side stubs turn the symbol along the stub so it stays on its row.
  A capacitor with a rail symbol on top and GND below reads as decoupling at a glance. Rails get no hierarchical label.
- Decoupling and bulk caps: in a row (5 cells apart), never in a stacked column (symbols of one cap hit the next).
- Wires inside a block, labels between blocks: each net is split per block (`BLOCK_OF`); each cluster is routed as wires
  and named by ONE label placed where its text is clear of every wire (pin exit, wire middle, any orientation).
  A cluster that cannot be routed keeps a label on every pin and is listed in `UNWIRED`.
- A passive sits directly on a pin (anchored, no stub) only when (a) it is the only other part on that net, (b) its
  other end is a rail (pull-up, pull-down, PROG/RT-type resistor, single cap), and (c) no other used pin of the host on
  that side lies within 7 mm. Otherwise it gets a block position next to its pin and the router wires it.
- Orientation: pull-ups rail on top (rot 180 where pin 1 is the signal), dividers vertical, series resistors horizontal,
  switches vertical (rot 270: pin 1 up). Back-to-back FETs: sources face each other, gates down (rot 90, mirror on the
  second). Draw protection circuits like the datasheet figure (HY2112: gate pins down, OD left of OC).
- Mirrors: KiCad rotates first, then mirrors in sheet coordinates (`mirror y` = left-right). `schkit.pin_pos` and
  `pin_away` both apply this; a wrong order shorts nets (the net check catches it).
- Short values on the sheet (`SHEET_VALUE` or the text before " (" ); the role goes in the block note.
- Block note: function, key values and the datasheet table/section they come from. Sheet title line = sheet purpose.
- Root page: block diagram. Boxes in signal-flow order (sources left, MCU right, loads below); sheet pins on the edge
  facing the other end, ordered along the edge by the other end's position (no crossings); all stubs registered before
  any route. A power-path note replaces rail wires. Nets that span 3 sheets may stay labelled.
- Rules sourced from the 2026-11-01 drawing research (KiCad 9 manual, Xcircuit and PCBWay guides): 1.27 mm grid,
  orthogonal wires, at most 3 wire ends per point, power up / GND down, left-to-right flow (a warning, not absolute),
  root = block diagram, one function per framed block with a title and note.
- Hand routes (`layout_v1.HAND_ROUTES`): for the few circuits an engineer draws a fixed way (switching power stage,
  input protection chain, protection-IC gate drive, a bus across connectors) give polylines of (ref, pin) or (x, y)
  cells. Split polylines at every tee so each joint is a wire end (dots are only drawn at wire ends). Those clusters
  count as wired and block other routes; their name label sits beside a horizontal wire (justify bottom) or at a fixed
  bus end (`HAND_LABELS`). Use the maze router for everything else.
- Text of parts on a busy row: `TAG_POS` / `TAGS_BELOW`. For a mirrored symbol KiCad flips the justification again,
  so give the un-mirrored justification (check the PNG).
- Parts whose library symbol fights the drawing (pin order of a common-mode choke) get a project symbol in
  `build_symbols.py`; pad numbers stay the datasheet's.
- Unused pins get a no-connect marker; say the reason in the block note when it is not obvious (PG, NC, strap).
- Net names: descriptive, uppercase, active-low ends `_N`, diff pairs end in the polarity suffix.

## Review loop (every sheet, before the gate)
1. `scripts/schematic-review.sh`: regenerates, ERC (must be 0), `review_checks.py` (labels on labels, wires through text,
   small text, diagonal wires, four-way junctions), one PNG per sheet in `hardware/out/review/`.
2. Read each PNG. Check: every label readable and not stacked; no text on a part or wire; each passive visibly belongs
   to its pin; caps read rail-cap-GND; the root shows how blocks connect and where power flows.
3. Findings to `hardware/out/review/review-notes.md` (sheet, what, where). Fix layout or generator, regenerate, repeat.
4. Leftovers (labelled clusters in `UNWIRED`, root labels) go to `BOARD.md` with the reason. Not waived silently.

## Verification
1. Net-intent check prints OK (generator).
2. ERC through the gate: zero errors and zero warnings. Never waive an unconnected pin; a pin conflict only with a datasheet reason.
3. Review loop above.
4. Every IC against its datasheet card (hw-parts).

## Learnings (2026-11-01) and what was wrong
- Wrong: automatic grid placement with a label on every pin. Parts scatter, labels stack, no flow. Right: hand-placed blocks.
- Wrong: L-shaped routes only. Too many nets fall back to labels. Right: maze router on a grid with blocks as obstacles.
- Wrong: global labels for nets between sheets, and a root sheet with empty boxes plus text. Right: hierarchical labels, sheet pins on the root, wires between boxes.
- Wrong: routing that let a new pin join the middle of its own stub. It produces T-junctions the writer does not mark. Right: join only at stub ends; the root writer adds junction dots where 3+ wire ends meet.
- Wrong: a root route that reused a fixed channel formula. Nets crossed and shorted. Right: route the root with the same router (boxes as obstacles).
- Wrong: a wire could run through text. Right: label and note boxes are obstacles for other nets; iterate routing until the labelled set is stable.
- Wrong: one label per pin piled on one point. Right: one label per wired net; duplicate points dropped.
- Learned: sheet pins must sit on the 0.5-cell routing grid, and exits must be one cell out (units: cells vs mm is an easy slip; check with the grid test).
- Learned: a net with 2+ pins and no name gets an auto name (`Net-(...)`). Name each wired net with one label.
- Learned: an ERC clean board can still be unreadable. Read the PNGs.
- Learned (2026-11-01, second pass): the router cannot draw a datasheet-style power stage (it looped BTST/SW/L around the
  caps). Hand routes fixed it. A geometry check that models a label box wrongly (centred vs beside the wire) hides or
  invents findings: `review_checks` reads the justification.
- Learned: root pins of two-sheet nets on facing edges take the partner's coordinate (straight wires); choose the
  partner deterministically (nearest sheet), never by set order, or results change between runs.
- Wrong (2026-11-01): GND and rails routed as wires (spaghetti across the sheet) and a label box blocking its own net in
  the next routing pass (63 unwired). Right: rails as power symbols, label boxes owned by their net, per-block routing (8).
- Wrong: anchoring every passive to the nearest host pin. Passives stacked on 1.27 mm pitch pins and on each other.
  Right: anchor only terminating passives on uncrowded pins (rule above).
- Wrong: root stubs registered net by net; an earlier route ran over a later pin and shorted two nets. Right: all stubs first.
- Wrong: drawing a circuit without checking it against the datasheet figure. The parts review found FETs common-source
  where the HY2112 needs common-drain, an external Rs where the BQ25798 senses internally, BAT caps on BATP.

## Net names and the rest of the chain
- Net full names include the sheet path; hierarchical labels make the root name. Router scripts and `critical.yaml` use full names: rename everywhere together, then run the gate.
- Test points, holes and jumpers: no fab part number; keep them out of the BOM (review).

## Pitfalls
| Symptom | Cause | Fix |
|---|---|---|
| Diode or LED reversed, ERC clean | library pin math (rotation) | net-intent check; verify pin positions |
| Net-intent check fails after an edit | NETS do not match the parts' pins | fix NETS; the netlist is the truth |
| ERC pin conflict or unconnected pin | wrong pin number | compare the symbol pin numbers with the datasheet |
| "label connected to only one pin" | a hierarchical or local label with no partner on its sheet | keep the label on a wire that reaches the other pins, or wire it |
| "wire not connected to anything" / off-grid endpoints | pin or exit off the 1.27 mm grid, or units mixed (cells vs mm) | put pins on 0.5-cell positions; exit one cell out |
| Nets shorted after routing | two nets share a wire point or a channel | run the net-intent check; the root must use the router |
| "global label only once" | single global label per net | hierarchical or power symbol |
| KiCad: "created by an older version" | old sheet format | `kicad-cli sch upgrade --force` on every sheet |
| Huge diff after regenerating | new UUIDs each run | commit only real changes |
| Part value runs across other blocks | long BOM description as the sheet value | short name on the sheet (`short_value`) |
| Root boxes empty or unconnected | no interface pins or wires | root from `root_interfaces()` (hierarchical pins + routed wires) |
