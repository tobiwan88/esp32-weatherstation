# bmp585-board: barometric pressure add-on (Qwiic)

One link of the outdoor sensor chain (main-board J3 -> SHT45 head -> add-ons, any order). Generators:
`hardware/gen/addon_boards.py bmp585` (schematic, `bom.csv`, net check) and `hardware/gen/addon_pcb.py` (board, all
copper by hand). One command for both add-ons: `hardware/tools/build_addons.sh` (renders in `hardware/out/review/bmp585/`).
Status (2026-11-04): ERC 0, nets OK, 0 DRC violations (warnings included), 0 unconnected, parity clean.

## Circuit (Bosch BST-BMP585-DS003-02 rev 1.2)
- U1 BMP585 (LCSC C18184976, Extended, 5153 in stock, USD 3.59). Pressure 30-125 kPa, on-chip temperature.
- I2C mode: CSB tied to VDDIO (section 6.2.3). SDO low = address 0x46 (section 5.6: SDO must not float). INT unused.
- C1 100 nF at VDD, C2 100 nF at VDDIO (figure 25), C14663 (Basic). VDD and VDDIO both on the chain's VDD (3V3_SW).
- No pull-ups (main board R50/R51, 10k on 3V3_SW). The bus pull-ups and VDDIO switch off together, so no interface
  pin is held high while VDDIO is off (section 4.2 warns that this can damage the part).
- J1 IN / J2 OUT JST SH 4-pin (C160404), Qwiic order 1 GND, 2 VDD, 3 SDA, 4 SCL, wired 1:1. H1 M3 hole.
- Firmware: the sensor settles in sleep mode after power-up (4.2, 4.3.9); set the mode and oversampling every cycle.

## Layout (2 layers, 17 x 21.5 mm)
- Base identical to the SHT45 head (connectors, B.Cu chain rows, M3 hole at the same place), sensor above it.
- Land pattern from figure 29 + 25 um per side (section 9.3.3), project footprint
  `weatherstation:BMP585_LGA-8_3.25x3.25mm`. No traces or vias between the lands (rule area), no pour under the
  body, and one solder-mask opening over the body (9.3.3: no solder mask under the sensor).
- SDA crosses SCL once on B.Cu; VDD comes up the right side from J2's VDD via.

## Mounting
- Static pressure only: inside the radiation shield or the main enclosure (vented), out of direct wind and rain.
  The 0x46 address is free on the sensor bus (SHT45 0x44, SCD41 0x62, VEML6030 0x10).
