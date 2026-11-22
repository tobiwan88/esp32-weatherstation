---
name: hw-fab-order
description: Use when producing fab files and ordering a PCB or assembly (gerbers, drill, BOM, CPL), choosing stackup, surface finish and assembly options, checking footprint fit against the fab's own footprints, writing order notes and the bring-up list, or deciding which parts are hand-soldered. Gate 6. Read hw-base first; part choice and stock are hw-parts.
---

# Fab files and order (gate 6)

Read `hw-base`, then the board's `BOARD.md` and its order notes (`ORDER.md`). Commands are in `BOARD.md`. Part choice and
stock are `hw-parts`. The tool names below are the JLCPCB flow; another fab needs its own fit and file rules.

## Before the files
- Routed board, gate OK at all DRC severities (zones refilled, schematic parity, only waived warnings), `hw-check` with
  `--strict --stock --qty N` right before ordering, on a clean committed tree (the silk carries the commit SHA).
- The engineer's KiCad review of schematic and layout is done. Commit everything under `hardware/`.
- Fab capability: smallest track, space, via and drill used on the board against the fab's current capability page for the
  layer count (a human reads it; the router's neck-downs sit at the floor). Note any option or fee it triggers.

## Production files (`tools/fab_package.py`)
- One command writes gerbers, drill, BOM and CPL into the ignored `out/` folder; it refuses a dirty tree, a DRC that is not
  clean and a part whose placement does not fit.
- Gerbers follow the fab's KiCad guide: its file extensions, soldermask subtracted from silk, zones checked, no X2 or
  netlist attributes, all copper, paste, mask, silk and Edge.Cuts layers; drill in mm, plated and non-plated files apart.
- The script stops when any file holds a local path or the user name; still look at silk text and metadata of every new
  binary export (gerbers, STEP, images) before it is committed or uploaded.
- CPL angle and centre come from fitting the fab's own footprint (its placement preview draws it) onto the placed pads.
  Never from a rotation table: tables date from other library versions and miss origin shifts (a module's origin, a USB-C
  shell moved by millimetres). Pads that differ between the libraries are fitted on geometry and confirmed by a human once.
- Fab APIs rate-limit: slow, cached, honest User-Agent; on 403/429 wait. Never work around a refusal.

## Choices to write into the order notes
- Stackup: the fab's default standard-prepreg stack for the layer count and thickness (no surcharge). Compute the
  controlled-impedance pair with `calc/impedance.py` for that stack, then cross-check with the fab's calculator (a human
  runs it; write inputs and result down). A thinner prepreg stack changes the impedance a lot (same tracks 90 ohm vs 69 ohm);
  do not pick it without recomputing. Pay for impedance control only when speed needs it (full-speed USB does not).
- Surface finish: immersion gold for fine-pitch QFN/VSON and tiny packages; hot-air leveling domes pads at 0.4 mm pitch.
- Copper weight, via tenting, board thickness, order-number marking (remove it, or let the fab place it).
- Assembly: side(s), economy vs standard (a large module can force standard: ask), process edges only where nothing
  overhangs (antenna, connector), a routed gap where a connector sticks out, and "send the placement preview first".
- Parts not placed and why, listed per reference: through-hole connectors on the back, DNP options, jumper pads, test pads,
  holes. Fab through-hole assembly costs per joint and needs a second side; hand-soldering is usual for a few connectors.
- Cost: from `calc/bom_check.py --stock --qty N` plus one manual quote; compare with the order limit before paying.

## Placement preview (human, before payment)
Confirm every IC, connector, polarised part (diode cathode, LED), module and USB-C shell in the fab's preview. A wrong one
is fixed in the footprint or in the fit's reviewed list, never by editing the CPL by hand.

## Bring-up list (goes into the order notes)
Made from the review: first power on a bench supply with no cell, which rails to measure, registers to write before the
first charge, addresses that must ACK, chip-id reads that prove each unverified pin map, the order of connecting cell,
panel and sensors, and what "good" looks like at each step. Parts that arrive hand-soldered are listed with their order.

## Pitfalls
| Symptom | Cause | Fix |
|---|---|---|
| Dirty-tree refusal after opening KiCad | the GUI rewrote `.kicad_pro` | restore it (keep a copy) unless the setting change is intended |
| Part rotated or shifted in the preview | table instead of a fit | fit the fab footprint; fix the footprint, not the CPL |
| Land covers only part of a terminal | a gap read as a pad size | overlap check against the package drawing; fab-footprint fit |
| Quote shows small-hole or impedance fees | vias or stack beyond the default | keep to the default stack and the fab's minimums |
| Extended parts cost more than the board | one fee per unique part | reuse values, Basic equivalents (`hw-parts`) |
| Preview shows the antenna clipped | edge rails or routing on the overhang | order note: rails on the other sides only |
| Stock changed after the check | volatile part | recheck right before paying; buy ahead |
| Order notes describe the previous design | not in the "copies to update" list | `hw-base` Changing a decision |
