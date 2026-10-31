# Hardware plan: weatherstation-v1

Goal: a solar + USB powered ESP32-S3 air-quality weather station PCB, JLCPCB-assembled, built with the same
generator-driven KiCad pipeline as desk_notifier (schematic, placement, routing, checks, fab files) with human checkpoints.

## Done
- Research (sensors, ready-made options, power budget, cost) and decisions: `weatherstation-v1/BOARD.md`, `REQUIREMENTS.md`.
- BOM with verified LCSC numbers for the main parts; six numbers still TBD.
- Board profile (`board.yaml`, `critical.yaml`, datasheet cards), gate (`scripts/hw-check.sh`) with BOM and power checks.
- Skills and tools copied from desk_notifier (`.claude/skills`, `hardware/calc`, `hardware/tools`, `hardware/rules`, `hardware/agents`).

## Next
1. Close the open items in `BOARD.md` (TBD numbers, panel Vmp, datasheet sections, Basic/Extended classes).
2. Schematic generator `hardware/gen/weatherstation_v1.py` (PARTS/NETS from `bom.csv`, sheets: Power, MCU, Sensors, USB) based on
   `reference/desk_notifier/gen/{notifier_v1,schkit,sheets_v1}.py`; net-intent check.
3. Layout generator `layout_v1.py` (outline at most 50 x 50 mm, antenna keepout, two GND planes, heat corner, NTC at the cell); custom DRC file.
4. Routing and fab package from `reference/desk_notifier/tools/` (`pipeline`, `route_krt.sh`, `finish.py`, `fab_package.py`); rename the board and net names.
5. Fill `critical.yaml` pins, run `calc/critical.py`, review renders, human KiCad review, order (`ORDER.md`).
6. Firmware (`firmware/`): ESP-IDF, SEN66 + SHT45 drivers, deep-sleep cycle, charge inhibit, MQTT/Home Assistant.

## Reuse from desk_notifier
- Board-neutral: skills, calc scripts, jlcparts lookup, rules, agent prompts (copied as is).
- Board-specific (kept under `reference/desk_notifier/`, not active): generators, pipeline scripts, rotation/fab package tool, profile examples, its PLAN with lessons.
