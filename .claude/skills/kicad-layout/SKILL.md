---
name: kicad-layout
description: Use for PCB placement and routing in KiCad (gates 4 and 5) - floorplan, layout generators, keepouts, critical blocks (critical.yaml, calc/critical.py failures), USB and diff-pair impedance and net-class widths, hand-drawn critical copper, autorouting and freezing router results, EMI checks, stacked boards, DRC failures, layout review from renders, gerber plotting, and KiCad GUI problems (locks, stray projects, hangs, IPC API). Read hw-base first; schematic is kicad-schematic, fab files and ordering are hw-fab-order.
---

# KiCad layout

Read `hw-base`, then the board's `BOARD.md`, `board.yaml` and `critical.yaml`. `BOARD.md` names the generator files and
commands. Details: `references/placement-and-emi.md` (floorplan, EMI, stacked boards), `references/routing.md` (router).

## Before placing (requirements first)
- Docs against the netlist: `BOARD.md` layout notes, `critical.yaml` refs and pins, net-class net names. After a part or
  topology change they go stale silently; fix them first and list contradictions for the engineer.
- Area budget: the generator prints the courtyard share of the board. Above about 60 % with all parts on one side and two
  signal layers, routing gets hard. Bring options with their cost per unit to the engineer (THT bodies on the back,
  smaller parts, fewer connectors or holes, a bigger board); never drop a part or grow the outline on your own.
- Floorplan before coordinates, with a datasheet citation per rule: inputs at the edge they enter from, heat sources,
  sensors opposite the heat and clear of edges and copper where the datasheet says, the radio (antenna at the edge), USB-C
  and debug at an edge, ESD parts at their connectors. Write it into `BOARD.md`.
- Track widths come from current: net class `current_a` in `board.yaml`, checked by `calc/track_width.py` (gate).

## Source of truth
- Edit the layout generator (placement, outline, planes, keepouts, hand-drawn copper), not the `.kicad_pcb` (review).
- Big parts get hand positions; passives are placed by rule (each named pad as close as possible to the pin it serves,
  courtyards never overlap, critical blocks first), so a moved IC takes its passives along and runs are repeatable.
- The build is deterministic: placement, locked copper and frozen router results are inputs; a hand step on the generated
  board is written into the generator or the `BOARD.md` commands, because a rebuild does not replay it.
- The generator merges board settings into the existing `.kicad_pro`; schematic settings in it stay.
- Parts with no schematic symbol (mounting holes, fiducials): board-only footprints, excluded from BOM and position file.
- Fab floors live in `board.yaml` `fab.rules` and `fab.router_rules`: change both or neither (review).
- Custom DRC rules: edit the file at `board.yaml` `fab.custom_drc`; the generator copies it next to the board (gate).
- One `.kicad_pro` per board in the repo; intermediates go to temp dirs (review).
- Never run DRC on a bare board copy: without its project it uses default rules and no library table (review).

## Order of work
1. Fixed parts: connectors, USB-C, mounting holes, modules, display sockets (stacked boards: `references/placement-and-emi.md`).
2. Keepouts and `thermal_distance`: they decide where parts may go.
3. Critical blocks, in this order: `switcher_loop`, `decoupling`, `feedback`, `series_termination`, `diff_pair`. Tight, in signal-flow order.
4. Remaining parts by block: power, digital core, sensors, interfaces. Run `calc/critical.py --placement`, read the renders (gate 4).
5. Hard copper by hand in the generator, locked, BEFORE the router: the USB pair (one layer, solid plane below, lengths
   matched, no stubs, nothing routed beside it), other fast or sensitive paths, switching loops from the datasheet layout
   example, the pin row of fine-pitch power parts, feedback dividers, decoupling. Coordinates come from the placed pads,
   never hard-coded; assert the orientation you rely on.
6. Planes on the `role: plane` layers; power trunks by current (hand-drawn, widened after routing as far as DRC allows).
7. Autoroute the slow rest on `role: signal` layers only (`references/routing.md`).
8. Router stalls with a few nets open: follow the stuck protocol in `references/routing.md` (sweep, hand-lead bottlenecks,
   freeze good results). Do not stop at "N nets open".
9. Remove router leftovers, stitch (edge fence, grid), fill zones, clean silkscreen, run the gate and `calc/emi_check.py`.

## Rules
- A module antenna goes over the board edge (or into a full-layer keepout at the edge). A footprint whose courtyard
  includes its own keepout area needs a body-only courtyard for placement.
- Every new critical block gets a `critical.yaml` entry before routing (review).
- Regulator input loop smallest, inductor at the switch node (`switcher_loop`); switch-node copper area limited (`emi_check`).
- FB divider at the pin, short FB trace (`feedback`); FB, sense and I2C away from the switch node and inductor (`emi_check` parallel rows).
- Decoupling cap at the pin (`decoupling`); power routed through the cap pads, not a stub off a shared trace (review).
- Diff pair: net-class width/gap from `calc/impedance.py` on the pair's `layer` and the real stackup (gate); skew counted
  with via barrels and stubs (`diff_pair`, `emi_check`); on one layer next to a GND plane (review).
- A stackup change reruns `calc/impedance.py` and updates the diff-pair net-class widths (gate).
- Series R at the driving pin (`series_termination`).
- Heat sources away from sensors and the cell thermistor (`thermal_distance`); regulator dissipation near a sensor (review).
- Every signal has a continuous return path, also across slots and narrow necks (`emi_check` planes row). Signals that
  cross a fast pair do so on another layer with solid planes between, DC or slow only, listed as `known:`.
- Edge GND via fence at `emi.edge_pitch_mm`; exempt spans (antenna, holes, overhangs, module pad columns) listed with reasons.
- Nothing in keepouts (DRC rule areas); the router does not read rule areas: make them real track/via keepouts.
- No via in an SMD pad; same-net vias keep the copper clearance to SMD pads set in the custom DRC file (DRC).
- Courtyards never overlap (DRC); pin 1 aligned across identical parts (review).
- Pours: right net per zone, thermal reliefs from `board.yaml` `layout`, islands removed (review).
- Tracks and vias at the fab floor (router neck-downs) are checked against the fab's current capability page (`hw-fab-order`).
- A deviation you cannot fix this revision: `known:` on the constraint with the fix for next time. Never loosen a limit to pass (review).

## Review loop (every placement or routing change)
Regenerate, render (annotated PNG: whole board plus regions, no pours, nets named and coloured, mm grid), read each PNG
against the floorplan and the rules, fix the generator, repeat. An independent pass follows: `hw-render-reviewer`
(mode layout), then the engineer in KiCad. Findings and leftovers go to a "Routing review" section in `BOARD.md` with
numbers (skew, loop lengths, areas, gaps) and the residual risks that need a bench.

## Verification
- Gate: zero DRC errors and zero unhandled warnings, at all severities in the routing pipeline too (an errors-only run
  hides silkscreen and library warnings until the fab step), in the board's own project with schematic parity and
  refilled zones. Errors are never waived; a warning may be, in `<board>/drc-waivers.csv` (type, reference, reason),
  which the fab gate reads. Not KiCad DRC exclusions from scripts (their key format is internal).
- `calc/critical.py hardware/<board>` (`--placement` before routing): every block OK or a `known` WARN (gate).
- `calc/emi_check.py hardware/<board>` on the routed board: pair, edge, antenna, planes, loops, parallel (gate).
- 3D view: height conflicts, connector alignment, parts past the edge, stack gap (review).
- Gerbers and drill: zones filled before plotting (`kicad-cli --check-zones`).
- A land-pattern fix on a routed board: fix the footprint generator, swap the footprint in place
  (`tools/swap_footprint.py`, keeps position and nets), DRC, clear what now clashes. Write the hand step in `BOARD.md`.

## Pitfalls
| Symptom | Cause | Fix |
|---|---|---|
| Plane cut by signals | router used plane layers | route signals only on `role: signal` layers |
| Signal over a plane split or void | no return path | move it, or run a GND track beside it |
| Via inside an SMD pad | router ordering | see `references/routing.md`; keep the DRC rule |
| Diff pair partial, snaked through vias | interleaved connector pads (USB-C A6/B6, A7/B7) | draw the pair in the generator, lock it, keep input copper |
| Fine-pitch part won't route | pad gap allows only straight exits | hand-draw escape stubs in the generator |
| Router stalls at 2-6 open nets in every run | congestion at a few bottlenecks | stuck protocol: hand-lead, freeze, finish |
| Router hugs the board edge, blocks the via fence | cheapest path | temporary edge keepout for that net, then remove |
| Router results differ between runs | non-deterministic routing | pin the seed; freeze good results; restore the committed board after experiments |
| Zones missing in gerbers | zones not filled before plotting | fill zones, then plot |
| False `lib_footprint_issues` or clearance results | DRC in a temp dir (no library table) or unfilled zones | run in the project, refill zones |
| `critical.py` rejects a new key | unknown top-level key | put EMI settings in `emi.yaml` |
| `pcbnew` import error | system Python | KiCad's bundled Python (env command in `BOARD.md`) |
| `yaml` missing in the generator | KiCad's bundled Python has few packages | pass `board.yaml` data as JSON from the build script |
| Schematic settings gone | generator wrote a fresh `.kicad_pro` | merge into the existing project file |
| Passives packed with no via room | courtyards touching | leave routing channels in the floorplan; check the render |
| Switching charger/regulator won't route, or vias at the pins | autorouter cannot share a QFN's 0.4 mm pin row between power and signals | draw the power stage from the datasheet layout example (caps on the pin row, SW through vias), lock it; escape bands free beside the signal pins |
| Bulk caps of one net spread across the board | greedy placer | place each cap next to the previous cap of its net, or fix the block by hand |
| Gate runs routed-board checks on a placement | generator copper is locked, router copper is not | the gate keys on unlocked tracks |
| `SwigPyObject has no attribute ...` after editing a footprint | removing footprint items, or un-cast items from `GraphicalItems()` | move items to the Fab layer instead of removing; `.Cast()` items; read rules from `.kicad_pro` |
| `lib_footprint_mismatch` after a silk or land edit | board footprint differs from the library on purpose | fix the library footprint, or waive per reference with the reason |
| pcbnew SWIG going away | deprecated (verify the KiCad version) | read boards with `calc/pcb.py`; write via IPC API or S-expressions |
| KiCad opens a stray project / "already open" | intermediate saved as a project; `~*.lck` from a killed instance | temp dirs for intermediates; delete the lock when no KiCad runs |
| IPC API sees no KiCad | needs the project manager and `api.enable_server` | start KiCad's project manager, not the standalone PCB editor |
| Regenerated board: huge diff | new UUIDs each run | commit only real changes |
| Stacked board: connectors collide or face the wrong way | THT bodies on the side facing the other board | `references/placement-and-emi.md` stacked boards |
