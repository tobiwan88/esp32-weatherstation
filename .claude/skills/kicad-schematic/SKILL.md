---
name: kicad-schematic
description: Use when creating or changing a KiCad schematic, editing a schematic generator (parts, nets, layout, wires, labels), reviewing a schematic for readability, or fixing ERC and net-intent failures. Read hw-base first; parts and datasheets are hw-parts, layout and KiCad GUI problems are kicad-layout.
---

# KiCad schematic

Read `hw-base`, then the board's `BOARD.md` and `board.yaml`. This is gate 3 (after requirements and BOM acceptance;
`hardware/GATES.md`). `BOARD.md` names the generator files and commands.

## Source of truth
- Edit the generator, never the `.kicad_sch`: GUI edits are overwritten.
- Generator layout: a board file (PARTS, NETS, drawing and routing), a layout file (blocks, notes, part positions, hand
  routes) and `schkit.py` (sheet writer, maze router, root writer; shared by every board). `review_checks.py` is the
  geometric review; `pins.py` prints pin positions in cells for hand routes and placement.
- Nets are the truth: `check_nets` compares NETS with KiCad's netlist after every run (net-intent check).

## The goal: a schematic an engineer can review
The reader must see what each block does, which part serves which pin, and where power flows, without tracing labels.
- Before drawing: a parts and circuit review (`<board>/PARTS-REVIEW.md`): every IC pin against its datasheet table, every
  value against its section, findings ranked A (wrong) / B (margin) / C (cleanup), each with a proposed fix. After
  drawing: independent reviewers (`hw-review`: `hw-datasheet-reviewer`, `hw-render-reviewer`).
- Draw each circuit like the datasheet's application figure. Netlist changes from the review only after the engineer
  decides; never change topology silently. Each round ends with the open decisions listed in the reply.

## Drawing rules (generator)
- Rails are power symbols, never wires (`POWER_SYMBOLS`; a rail without a library symbol uses `power:VCC` with the net as
  value). One symbol per rail pin at its stub end: up for a rail, down for GND, turned along a side stub. No hierarchical
  label on a rail. A cap with a rail on top and GND below reads as decoupling.
- Decoupling and bulk caps in a row (5 cells apart), never a stacked column.
- Wires inside a block, labels between blocks: each net is split per block; each cluster is routed and named by ONE label
  where its text is clear of every wire. A cluster that cannot be routed keeps a label per pin and is listed in `UNWIRED`.
- Anchor a passive directly on a pin only when it is the only other part on that net, its other end is a rail, and no
  other used pin of the host lies within 7 mm on that side. Otherwise give it a block position; the router wires it.
- Orientation: pull-ups rail on top, dividers vertical, series resistors horizontal, switches vertical (pin 1 up),
  back-to-back FETs sources facing, gates down.
- Mirrors: KiCad rotates first, then mirrors in sheet coordinates (`mirror y` = left-right); `pin_pos` and `pin_away` apply
  this. A 180 degree part turns its texts upside down: place them with `tag`.
- Short values on the sheet; the role and the datasheet section go in the block note. Sheet title line = sheet purpose.
- Root page: block diagram, boxes in signal-flow order, sheet pins on the edge facing the partner, ordered to avoid
  crossings, all stubs registered before any route, partners chosen deterministically. Nets on 3+ sheets may stay labelled.
- General drawing practice: 1.27 mm grid, orthogonal wires, at most 3 wire ends per point, power up / GND down,
  left-to-right flow, one function per framed block with a title and note.
- Hand routes (`HAND_ROUTES`): for circuits drawn a fixed way (switching stage, input protection chain, protection-IC gate
  drive, a bus across connectors, a rail along a connector) give polylines of (ref, pin) or (x, y) cells; get the
  coordinates with `pins.py`. Split polylines at every tee. Hand clusters count as wired and block other routes; their
  label sits beside a horizontal wire or at a fixed bus end (`HAND_LABELS`); a hand-drawn rail gets one power symbol.
- A pass-through part (ESD array, two pins on one net on opposite sides) cannot be joined by hand wires on one side: the
  two halves need a label each, or a wire around the part. Keep such nets labelled.
- Text on a busy row: `TAG_POS` / `TAGS_BELOW`; for a mirrored symbol give the un-mirrored justification (check the PNG).
- A library symbol whose pin order fights the drawing (common-mode choke) gets a project symbol (`build_symbols.py`);
  pad numbers stay the datasheet's. Footprints from maker drawings: `build_footprints.py`, source in the descr.
- Unused pins get a no-connect marker; the reason in the block note when not obvious. A not-fitted part has no fab
  number and says DNP and its fab number in the value.
- Net names: descriptive, uppercase, active-low ends `_N`, diff pairs end in the polarity suffix. A rail feeding several
  loads is named for the rail, not for one load (a boost feeding two sensors was named after one of them).
- The symbol must match the part: polarity (unidirectional vs bidirectional TVS, diode, LED), pin names, FET orientation,
  the arrow of a rail. A netlist can be right while the drawing makes the engineer order the wrong part.
- Notes and comments are generated from the values (or checked against them): a note saying 10k above a 2.2k resistor is a
  finding. Connector sheets show pin numbers and polarity (PV, cell, header pin 1).
- Title block: date and revision come from the generator run, never hard-coded. Reference designators sit beside their
  symbol, not on it. No stray power-flag symbols that read as orphaned parts. Block notes stay inside their frame.
- Sheet partition: one function per sheet, but merge sparse sheets; a bus that touches more than two sheets is a sign the
  partition is wrong. Root page: boxes in signal-flow order AND the power path between them. Header/board-edge sheets show
  signal direction (label shapes).

## Splitting a design into boards
- Phase A: a faithful split, no circuit change except the interface header; one commit. Phase B: each addition its own commit.
- A script proves the split against the old design: every part and net on exactly one side or on the header, no net split,
  values changed only where listed (`split_check.py` pattern). Net names stay the same across the split.
- The header's pin table exists once (architecture doc), both generators read the same constants; mating errors are
  tested by script (`hw-requirements`, `hw-review` checklist).

## Review loop (every sheet, before the gate)
1. The board's review script: regenerate, ERC (must be 0), `review_checks.py`, one PNG per sheet in `hardware/out/review/`.
2. Read each PNG: labels readable and not stacked; no text on a part or wire; each passive visibly at its pin; nothing
   outside the sheet frame; the root shows how blocks connect.
3. Findings to `hardware/out/review/review-notes.md`; fix the layout or generator; repeat.
4. Leftovers (`UNWIRED`, root labels) go to `BOARD.md` with the reason.
5. Independent pass: `hw-render-reviewer` (mode schematic) reads every PNG; small `hw-visual-check` questions for single
   doubts. The engineer reviews the PNGs last; they are the main quality gate.

## Verification
1. Net-intent check OK. 2. ERC zero errors and warnings (never waive an unconnected pin; a pin conflict only with a
datasheet reason). 3. Review loop. 4. Every IC against its datasheet card (hw-parts).

## Why these rules (lessons)
- Grid placement with a label on every pin, L-only routing and global labels gave unreadable sheets: hand-placed blocks,
  a maze router with obstacles and hierarchical labels fixed it.
- Rails routed as wires became spaghetti; label boxes not owned by their net blocked their own routes.
- Unregistered stubs and joins in the middle of a stub shorted nets or hid T-junctions: register all stubs first, join at
  stub ends, dots where 3+ wire ends meet.
- An ERC-clean sheet can still be wrong or unreadable: the net check and the PNG review catch what ERC cannot (a parts
  review found FETs in the wrong configuration, a sense resistor the IC does not need, caps on the wrong pin).
- "No engineer draws it like that" (labels on every pin, free-standing passives, nets going nowhere) was the engineer's
  first verdict on generated sheets: research drawing practice, then fix the generator, not the sheets. Sourced rules
  (KiCad manual): wire ends exactly on pins, pin ends on the 1.27 mm grid, junction dots, no-connect markers, power-flag
  ERC; switch the four-way-junction ERC on. Left-to-right flow and power-up/ground-down are conventions: warn, do not fail.

## Net names and the rest of the chain
- Full net names include the sheet path; layout scripts and `critical.yaml` use them: rename everywhere together, then the gate.
- Test points, holes and jumpers: no fab part number; out of the BOM.

## Pitfalls
| Symptom | Cause | Fix |
|---|---|---|
| Diode or LED reversed, ERC clean | rotation/mirror pin math (kicad-sch-api 0.5.x rotates pins the wrong way at 90/270 degrees and left-justifies every label; `schkit` corrects both) | net-intent check; `pins.py` |
| Net-intent check fails after an edit | NETS do not match the pins | fix NETS; the netlist is the truth |
| `unexpected net Net-(...)` after a hand route | a pass-through part split the net | keep the net labelled (rule above) |
| A rail symbol on every pin of a hand-drawn rail | power nets get a symbol per pin | hand-drawn rail: one symbol (generator handles it) |
| ERC pin conflict or unconnected pin | wrong pin number | symbol pins vs datasheet |
| "label connected to only one pin" | label with no partner on its sheet | wire it, or put the label on a wire that reaches the pins |
| Off-grid endpoints | cells vs mm mixed | pins on 0.5-cell positions; exit one cell out |
| Nets shorted after routing | two nets share a point | net-intent check; root uses the router |
| "created by an older version" | old sheet format | `kicad-cli sch upgrade --force` on every sheet |
| Huge diff after regenerating | element ids are numbered in drawing order | commit only real changes |
| Home path in a commit | the exported `.net` netlist | git-ignore `<board>/*.net` for every board |
| Block sticks out of the sheet | block width beyond the frame | check the PNG; A3 frame is about 160 cells wide |
| Generator edited, `.kicad_sch` not regenerated | notes/values differ from the committed sheet | regenerate, commit both; the net-intent check runs on the sheet |
| Drawing shows the wrong part (TVS direction) | generic symbol reused | project symbol or the right library symbol; polarity in the PNG review |
| Rail named after one load | net named where it was first drawn | rename everywhere together (generators, `critical.yaml`, notes), then the gate |
