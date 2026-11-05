# veml6030-board: ambient light add-on (Qwiic)

One link of the outdoor sensor chain (main-board J3 -> SHT45 head -> add-ons, any order). Generators:
`hardware/gen/addon_boards.py veml6030` and `hardware/gen/addon_pcb.py`; build both add-ons with
`hardware/tools/build_addons.sh` (renders in `hardware/out/review/veml6030/`).
Status (2026-11-04): ERC 0, nets OK, 0 DRC violations (warnings included), 0 unconnected, parity clean.

## Circuit (Vishay VEML6030, doc. 84366 rev 1.8)
- U1 VEML6030 (LCSC C132182, Extended, 10613 in stock, USD 0.73): 0-120 klx, 16-bit, 2 x 2 mm.
  Same die as the VEML7700 (C504893, USD 1.14) in the smaller package.
- ADDR low = address 0x10 (figure 8 notes). INT (open drain) unused.
- C1 100 nF at VDD (C14663, Basic). The optional 10 R / 10 uF supply filter of figure 8 is left out.
- No pull-ups (main board R50/R51). J1 IN / J2 OUT as on every chain board. H1 M3 hole.
- Firmware: the sensor powers up shut down (ALS_SD = 1); configure gain and integration time after every power-up.
  Full sunlight needs the low gain (1/8 or 1/4) setting.

## Layout (2 layers, 17 x 21.5 mm)
- Base identical to the SHT45 head. Sensor rotated 90 degrees so all signals stay on F.Cu; footprint
  `weatherstation:Vishay_VEML6030_2x2mm` from the datasheet's recommended footprint (page 10).
- The sensor sits at the top edge, 13 mm from the connectors (about 2.9 mm tall), so they shade only the last
  ~12 degrees above the horizon on that side.

## Mounting
- Outside the radiation shield (the shield blocks light), facing the sky under a clear, UV-stable window
  (glass or PMMA). The window transmission scales the reading: calibrate once against a reference lux meter.
- The 0x10 address is free on the sensor bus (SHT45 0x44, BMP585 0x46, SCD41 0x62).

## Ordering
Production files and PCB/assembly options: `hardware/ORDER-sensor-boards.md`.
