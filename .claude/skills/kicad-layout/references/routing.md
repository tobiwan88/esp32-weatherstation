# Autorouting (read when routing)

## KiCadRoutingTools (KRT), preferred
- Planes first (`route_planes.py`): one plane net per `role: plane` layer, positionally (two GND planes: `--nets GND GND
  --plane-layers In1.Cu In2.Cu`); plane layers stay solid.
- Copy the `.kicad_pro` and `.kicad_dru` next to every stage board in the temp dir, or the stages lose the rules.
- Signals (`route.py`) on `role: signal` layers only (`--layers`).
- `--ordering inside_out`: the default order put vias into pads.
- `--same-net-pad-clearance`: keep it at or above the same-net via clearance in the custom DRC file (stops same-net vias in pads).
- `--no-fix-drc-settings --fab-overrides <fab.router_rules>`: otherwise KRT rewrites the project's fab rules.
- `--power-nets-widths`: keep equal to the board's net classes and `BOARD.md` notes (review).
- `--keep-input-copper`: keeps locked, hand-drawn critical copper; `route.py` skips complete nets.
- Diff pairs: KRT pairs nets by name suffix (see kicad-schematic).
- Pin the hash seed (`PYTHONHASHSEED`) for repeatable runs; output still depends on object ids, so loop place, route, gate and keep the first pass.
- Power-net neckdown: where a class-width tap does not fit, KRT routes it at `--track-width` (tens of mm at 0.2 mm on
  a dense board). Hand-draw the trunks of the current paths, then widen what fits after routing (try class width down
  to the DRC floor, keep the widest width DRC accepts).
- KRT does not read custom DRC rule areas: make keepouts real track/via keepouts, and pin the fab floors
  (`--fab-overrides`) to the project DRC values, or escalation (clearance 0.127, via to edge 0.3) creates DRC errors.
- It drops one layer's link between parallel vias (loop): use one bigger via instead.
- It still drops vias into small same-net pads now and then: give those pads a locked escape via, or nudge after routing.
- Separate pins of one internal node (ESD flow-through pins, pass-through pads) need a drawn link, or the router joins
  them the long way round (a 20 mm loop on a USB pair).
- When a few nets stay open in every run, sweep router settings (`--max-ripup`, `--ripup-blocker-select`) and read
  which nets fail across all runs: those need hand copper; nets that move between runs are congestion.
- A 0.4 mm-pitch pin row whose nets leave to both sides: staggered vias right under the row, then nested B.Cu lanes
  (the inner lane turns first, so no lane crosses another); check the lanes do not fence in the remaining pins.

## Freerouting, fallback
- Use a wrapper that turns automatic neckdown off (tracks thinner than the net class near fine pads).
- Mark inner plane layers as `power` in the DSN, or it routes signals on them. As a finisher on a KRT board it counted
  the plane nets as unrouted and did worse (first project, 2026-11).
- The native CLI has hung or crashed in its router thread; run the JAR (its analytics are on by default: the wrapper turns them off).
- KiCad 10's CLI has no DSN export (pcbnew SWIG has).

## Stuck protocol (when nets stay open; do not stop at "N open")
1. Sweep router settings (`--max-ripup`, `--ripup-blocker-select`, ordering) and read which nets fail in ALL runs: those
   need hand copper. Nets that move between runs are congestion, not a blocker.
2. Name the bottleneck from a render (a window under a pair, a pad column, a 0.4 mm pin row) and hand-lead the failing
   nets through it in the generator as locked copper, in lanes with room for the nets that follow; check the lanes do not
   fence in remaining pins.
3. Let the router finish the rest around the locked copper.
4. Freeze every good router result (`tools/main_freeze.py`-style: copper to `frozen-routes.json`, replayed as locked copper
   by the generator, minus the hand copper). Router order alone could not finish the last nets; the frozen result makes the
   routing reproducible. Re-freeze only on purpose.
5. Still stuck after a few tries: research how others do it (a web research agent: autorouters, escape fanout, tools that
   use KiCad's own DRC as the oracle) and try the second tool; timebox, then bring the blocker and the options to the engineer.
6. A long detour of a slow net is accepted only after the parallel-run and return-path checks pass; list it in the routing review.

## After routing
- Remove dangling stubs and vias one at a time, DRC-driven, reverting any removal that opens a connection.
- With pcbnew SWIG: keep Python references to items you iterate, or the board is freed under you.
- Check pairs and critical nets with `calc/critical.py` (skew, vias, FB length); layer and width per pair: script candidate (review until then).
