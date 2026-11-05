# Sensor-chain boards: JLCPCB order (SHT45 head, BMP585 pressure, VEML6030 light)

Three separate designs (`hardware/sht45-board/`, `hardware/bmp585-board/`, `hardware/veml6030-board/`), same base:
J1 IN / J2 OUT JST SH (C160404), one M3 hole, sensor and 100 nF. Main board: `weatherstation-v1/ORDER.md`.

## Build the files (on a clean, committed tree)
```sh
source scripts/kicad-env.sh
python3 -I hardware/tools/fab_package.py --require-clean \
    hardware/sht45-board/sht45-board.kicad_pcb hardware/bmp585-board/bmp585-board.kicad_pcb \
    hardware/veml6030-board/veml6030-board.kicad_pcb
```
The script refuses a board whose DRC (with schematic parity and refilled zones) is not clean, then writes per board in
`hardware/out/fab/<board>/` (gitignored):

| File | Upload as |
|---|---|
| `<board>-<sha>-gerbers.zip` | Gerber file (PCB) |
| `<board>-bom.csv` | BOM (assembly) |
| `<board>-cpl.csv` | CPL / pick and place (assembly) |
| `placement-fit.txt` | not uploaded: how each part's JLC (EasyEDA) footprint was fitted onto the KiCad pads |

CPL angles and centres are not KiCad's origin plus a guessed correction: `fab_package.py` fits the EasyEDA footprint that
JLC's placement preview uses onto the placed KiCad pads (see its docstring). Fit results (2026-11-05), worst pad centre:
SHT45 0.023 mm (0 deg correction), BMP585 0.000 mm (0), VEML6030 0.001 mm (**180 deg** correction: its EasyEDA footprint
is drawn the other way round), 0603 caps 0.075 mm (land size differs), connectors 0.001 mm on geometry (pad numbers
differ: tabs "MP" vs 5/6).

## PCB options (all three)
- Layers **2**, FR-4, thickness **1.6 mm** (default; stiff enough for the M3 screw and the cable plug, no surcharge),
  1 oz outer copper, any colour (green is cheapest and fastest).
- Sizes: SHT45 head 17 x 36 mm, BMP585 and VEML6030 17 x 21.5 mm. Quantity 5 each (the minimum).
- Surface finish **ENIG** recommended: flat pads for the BMP585 LGA (pads 0.6 x 0.85 mm, no solder mask under the part),
  the VEML6030 (0.55 x 0.3 mm pads) and the SHT45 DFN. Lead-free HASL is cheaper but leaves domed pads on these.
- Via covering: tented (default). Impedance control: no (I2C at 100-400 kHz).
- Order number: there is no `JLCJLCJLCJLC` mark on these small boards; choose "Remove order number" if offered at no or
  low cost, otherwise let JLC place it (the back side is mostly free).
- Rules used: `rules/jlc-2layer.json` (vias 0.6/0.3, clearance 0.15 mm, copper 0.3 mm from the edge).

## Assembly options
- Economic PCBA, **top side**. J1 and J2 sit at the board edge: if the quote asks for edge rails, choose "added by
  JLCPCB" (do not add rails in the design).
- Placement preview: check U1 pin 1 (dot on the silk next to it) and that J1/J2 open towards the board edge.
- Extended parts per design: SHT45 board 2 (SHT45 C5360602, JST C160404), BMP585 board 2 (C18184976, C160404),
  VEML6030 board 2 (C132182, C160404); the 100 nF (C14663) is Basic. Each separate order pays the setup and its own
  Extended fees: about USD 8.18 setup + 1.53 stencil + 2 x 3.07 per design (2026-10 prices).
- Check stock right before ordering: `python3 hardware/tools/jlcparts.py C5360602 C18184976 C132182 C160404 C14663`.

## Handling after delivery
- SHT45: keep the sensor opening free of coating; Sensirion handling instructions apply (reflow done by JLC).
- VEML6030: mount under a clear, UV-stable window outside the radiation shield; BMP585 inside the shield or enclosure.
