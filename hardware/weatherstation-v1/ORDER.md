# weatherstation-v1: JLCPCB order

Sensor-chain boards (SHT45, BMP585, VEML6030): `hardware/ORDER-sensor-boards.md`.

## Order of operations
1. Board routed and reviewed (`hardware/tools/route_v1.sh` ends with `silk_fix.py`), gate OK:
   `scripts/hw-check.sh --strict --stock --qty 5` prints `hardware checks: OK` right before ordering.
2. Human review in KiCad of schematic and layout. **Commit everything under `hardware/`** (the silk carries the SHA).
3. Build the files on the clean tree:
   ```sh
   source scripts/kicad-env.sh
   python3 -I hardware/tools/fab_package.py --require-clean hardware/weatherstation-v1/weatherstation-v1.kicad_pcb
   ```
   It refuses a dirty `hardware/` tree, a DRC that is not clean (schematic parity, refilled zones; only the warnings in
   `drc-waivers.csv` pass) and any part whose placement does not fit (see below). Output, gitignored:
   `hardware/out/fab/weatherstation-v1/`.
4. `VERSION.txt` has no `-dirty`; in JLC's gerber viewer the bottom silk reads `weatherstation v1 <sha>`.

| File | Upload as |
|---|---|
| `weatherstation-v1-<sha>-gerbers.zip` | Gerber file (PCB) |
| `weatherstation-v1-bom.csv` | BOM (assembly) |
| `weatherstation-v1-cpl.csv` | CPL / pick and place (assembly) |
| `placement-fit.txt` | not uploaded: per part, how JLC's footprint was fitted onto ours |

Gerbers follow JLC's KiCad guide: Protel extensions, soldermask subtracted from silk, zones checked, no X2 and no netlist
attributes; F/In1/In2/B Cu, F/B Paste, F/B Mask, F/B Silkscreen, Edge.Cuts; Excellon in mm (decimal), PTH and NPTH in
separate files, no map file. The script stops if any file contains a local path or the user name.

### Placement (CPL)
JLC's placement preview draws its own (EasyEDA) footprint of each LCSC part. `fab_package.py` fetches that footprint and
fits it onto our placed pads: the CPL holds the angle and the point that put JLC's footprint on ours, not KiCad's origin
plus a guessed correction table. Result 2026-11-05 (98 placements):
- 95 parts: every pad within 0.25 mm (J1, J3 and L3 fitted on geometry, confirmed by hand: `GEOMETRY_OK` in the
  script). Angle corrections found: 180 deg for the SOT-23, SOT-563 and HY2112 SOT-23-6 parts, 270 deg for the
  USBLC6 (U4, U5), 90 deg for L3; origin shifts 3.65 mm for U1 (ESP32 module) and 1.5 mm for J1 (USB-C).
- `LAND` (land drawn differently, angle unambiguous): F1 1812 fuse (pad pitch 4.28 vs 3.7 mm), Q40 SOT-23 (0.28 mm),
  U3 BQ25798 (four odd corner pads 0.25-0.39 mm; the other 25 pads fit).
Still look at the preview before paying: U1, U3, U2, U4, U6, U7, D1 (cathode band), LEDs, J1, J3, L3.

## PCB options
- Layers **4**, 50 x 50 mm, FR-4, **1.6 mm**, stackup **JLC04161H-7628** (the default, no surcharge). The USB pair
  (0.27 mm tracks, 0.15 mm gap on F.Cu over In1 GND) is sized for it: 90.6 ohm with mask (`calc/impedance.py`). On
  JLC04161H-3313 (0.0994 mm prepreg) the same tracks give about 69 ohm, so do not pick 3313.
  JLC calculator cross-check (jlcpcb.com/impedance): 4 layers, 1.6 mm, JLC04161H-7628, differential, L1 ref L2, W 0.27, S 0.15.
- **Impedance control: no.** Full-speed USB (12 Mbit/s, edges >= 4 ns), pair about 30 mm, critical length about 165 mm.
- Outer copper 1 oz, inner 0.5 oz (default). Via covering: tented. Min track/space 0.127/0.15 mm; vias 149 x 0.6/0.3,
  52 x 0.45/0.25, 5 x 0.45/0.2: inside JLC's 4-layer minimum (0.15 mm drill), no option needed; check that the
  quote shows no small-hole fee.
- Surface finish **ENIG** recommended: BQ25798 0.4 mm-pitch VQFN, TPS63802 VSON-HR, SOT-563. HASL leaves domed pads at
  0.4 mm pitch.
- Order number: there is no `JLCJLCJLCJLC` mark on the board. Choose "Remove order number" if offered at low cost,
  otherwise let JLC place it.

## Assembly options
- Economic PCBA, **top side** (all assembled parts are on top). If the quote forces Standard for the ESP32 module,
  expect about USD 40-50 more (REQUIREMENTS.md 5a).
- **Edge rails on LEFT and RIGHT only**, added by JLCPCB. Not on top: the module antenna overhangs the top edge by about
  6 mm. J1 (USB-C) sticks out of the left edge by about 0.5 mm: ask for a routed gap at J1. J3 sits 0.03 mm from the bottom
  edge (no rail there). Remark for the PCBA order:
  > Process edges on LEFT and RIGHT sides only, none on top/bottom (ESP32-S3-WROOM-1 antenna overhangs the top edge by
  > about 6 mm). USB-C J1 (C165948) protrudes about 0.5 mm past the left edge: please leave a routed gap between board and
  > rail at J1, do not clip the connector. Please send the placement preview before assembly.
- Not assembled (no LCSC in BOM/CPL): J2, J5, J6, J7, J8 (through-hole, bottom side, hand-soldered), U8 SCD41 (DNP),
  JP1/JP2 (open solder jumpers), TP1/TP2, the four M3 holes.
- 42 BOM lines, 14 Extended part types (J1, U4/U5, D1, L3, U3, L1, F1, TH1, U6, U1, U2, L4, U7, J3): 14 x USD 3.07 per
  order. Stock: `scripts/hw-check.sh --stock --qty N`.

## Cost
See BOARD.md "Cost basis" and REQUIREMENTS.md 5a; get the JLC quote for 5 boards before ordering.

## Bring-up (first board)
1. USB only, no cell: SYS and 3.3 V, USB enumerates (USB-JTAG), flash a blink/serial test; status LEDs.
2. Firmware writes the BQ25798 registers (VREG 3.65 V, ICHG) before CE is released (charge-policy.md); then the cell.
3. Cell without sun: deep-sleep current, 3V3_SW and BOOST_EN switching, battery reading.
4. USB charge, then PV charge with the real panel (MPPT, ICHG, JEITA), board temperature near U3/L1.
5. Sensors: PMS7003 on J2 (5V_SW), SHT45 chain on J3 (plus BMP585/VEML6030 if fitted), ZE25-O3 on J8; WiFi range in the enclosure.
