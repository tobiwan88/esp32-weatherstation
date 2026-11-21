# System architecture: power board, main board, SHT head

State 2026-11-21: schematics generated for `power-board/` and `main-board/` (split from `weatherstation-v1/`, which
stays as the single-board history with its layout and fab files). No layout for the split boards yet.
Requirements: `REQUIREMENTS-system.md`. Header pin map in code: `gen/boards_common.py` (`HEADER_PINS`), used by both
generators; `tools/split_check.py` proves both boards use it and that the split keeps every v1 part and net.

## Block diagram

```
 solar panel 6 V           LiFePO4 cell (26700)
     |  J5                     |  J6
+----v-------------------------v-------------------+         2x9 2.54 mm J10 (J_PWR)          +-----------------------------------------------+
| POWER BOARD  (power-board/)                      |   SYS (1,2) ------------------------->   | MAIN BOARD  (main-board/)                     |
|  PV: SMBJ10A D1, CM choke L3, ACFET2/RBFET2 M3/M4|   GND (3,4,7,8,11,12,15,16) ---------   |  SYS -> TPS63802 U2 -> +3V3 -> ESP32-S3 U1    |
|  USB: ACFET1/RBFET1 M1/M2  <---------------------|-- USB_VBUS (5,6) <------------------   |       -> Q40 -> 3V3_SW (sensor bus, SHT head) |
|  BQ25798 U3 (VAC1 USB, VAC2 PV, BC1.2 on D+/D-)  |<- USB_DP/USB_DN (9,10) <-----------   |  SYS -> TPS61023 U7 -> 5V_SW (PMS7003, O3)    |
|  cell: F1 PTC, TH1 NTC, HY2112 U6 + M60/M61      |<> CHG_SDA/CHG_SCL (13,14) <-------->   |  USB-C J1 + USBLC6 U4 (data to the ESP32)     |
|  no 3.3 V on this board                          |-> CHG_INT (17) -------------------->   |  charger pull-ups R20/R22/R54/R55 to +3V3     |
|                                                  |<- CHG_CE (18) <--------------------   |  sensor ports J2, J3 (Qwiic), J8, U8 (DNP)    |
+--------------------------------------------------+                                         +---------------------+-------------------------+
                                                                                                                   | J3 Qwiic cable (3V3_SW, I2C)
                                                                                                         +---------v---------+
                                                                                                         | SHT HEAD          |
                                                                                                         | (sht45-board/)    |
                                                                                                         +-------------------+
```

## J10 (J_PWR) pin table

2 x 9, 2.54 mm, through-hole, hand-soldered on both boards (same footprint `PinHeader_2x09_P2.54mm_Vertical`, no LCSC).
Odd pins = row A, even pins = row B. Direction is seen from the power board.

| Pins | Net | Direction | Notes |
|---|---|---|---|
| 1, 2 | SYS | power -> main | BQ25798 system rail (narrow VDC, about cell voltage, up to 5.5 V on the main board); 2 pins, 3 A per pin class header, >= 1 A required |
| 3, 4 | GND | | |
| 5, 6 | USB_VBUS | main -> power | USB-C VBUS to the ACFET1 drain (M1) and VAC1; 2 pins (USB input up to the 1.59 A ILIM clamp) |
| 7, 8 | GND | | |
| 9 | USB_DP | main -> power | BQ25798 D+ (BC1.2 detection only); also ESP32 IO20 via R32 on the main board |
| 10 | USB_DN | main -> power | BQ25798 D- ; also ESP32 IO19 via R33 |
| 11, 12 | GND | | |
| 13 | CHG_SDA | both | charger I2C, 0x6B; 10k pull-up R54 on the main board (ESP32 IO1, RTC I2C for the ULP) |
| 14 | CHG_SCL | main -> power | 10k pull-up R55 on the main board (IO2) |
| 15, 16 | GND | | |
| 17 | CHG_INT | power -> main | open drain (6 mA max sink), 10k pull-up R22 on the main board (IO10) |
| 18 | CHG_CE | main -> power | active low charge enable; 100k pull-up R20 on the main board = charge off (IO9) |

### Contract decisions
a. **Pin order.** Every signal row (USB_VBUS, D+/D-, I2C, INT/CE) has a GND row directly before it; SYS (row 1) and
   USB_VBUS (row 3) are on their own pins at the opposite end from the I2C rows (rows 7 and 9). Row 1 is SYS, not a
   signal: a rotated plug (pin 1 to pin 18) puts SYS on CHG_CE/CHG_INT, which are 6 V tolerant on the BQ25798 (6.1)
   but not on the ESP32 (3.6 V). Stacked headers make rotation impossible; for a cable use a keyed (shrouded) connector.
b. **USB D+/D- (BC1.2): carried over the header (pins 9/10). ENGINEER DECISION.** Reason (BQ25798 SLUSDV2C 7.3.4.5 and
   table 7-4): detection runs only on VAC1 with AUTO_INDET_EN = 1 (the POR default). Without D+/D- the result is not an
   SDP but an unknown or non-standard source: IINDPM 3 A, clamped by ILIM to 1.59 A, drawn from a PC port that may only
   supply 0.5 A. With D+/D- the SDP case gets 500 mA, DCP 3.25 A (clamped to 1.59 A). The weatherstation-v1 note says
   chargers were not detected without it (critical.yaml). Alternative: no D+/D- on the header, firmware writes
   AUTO_INDET_EN = 0 and sets IINDPM itself (500 mA unless it knows better). Cost of the chosen route: 2 pins + 1 GND row,
   and the D+/D- stubs reach the power board (full speed 12 Mbit/s, stubs short when stacked). Firmware still sets
   AUTO_INDET_EN = 0 after the first detection so a later re-detection does not disturb enumeration (v1 B5) and must
   never enable HVDCP (9/12 V on USB_VBUS would exceed the USBLC6 U4 VBR of 6 V on the main board).
c. **Pull-ups live on the main board** (Header sheet): R20 CE 100k, R22 INT 10k, R54/R55 I2C 10k, all to +3V3. The
   power board has no 3.3 V rail; REGN (5 V) is above the ESP32's 3.6 V and is the wrong rail for INT (7.3.11.2).
   A bought charger module brings its own rail; its pull-ups then sit in parallel (10k || its value).
d. **CE default: high (charge off)** through R20 until the firmware has written VREG 3.65 V (POR default 4.2 V is
   above the LFP limit 3.75 V). Main board without a power board: nothing on SYS, the board is unpowered unless a bench
   supply feeds SYS (bring-up below); the I2C pull-ups and R20 hang on +3V3 with nothing behind the header.
   **Power board without a main board: CE floats** (BQ25798 "must be pulled HIGH or LOW", 7.3), and the BQ25798 may
   charge to the POR 4.2 V. The TI EVM keeps its CE pull-up on the charger board (SLUUCB5, JP17). Open finding
   power-board/PARTS-REVIEW.md A1: add a CE pull-up on the power board (e.g. 100k to REGN with a divider to stay
   below the ESP32's 3.6 V, or to BAT_PACK).
e. **No back-feed with the main board unplugged:** USB_VBUS pins connect only to the ACFET1 drain and VAC1; RBFET1 M2
   blocks VBUS/PV from the USB_VBUS pins (figure 8-2). SYS pins stay live (cell voltage through the BQ25798 BATFET);
   exposed SYS pins on a loose power board are a short risk, not a back-feed.
f. **Future compatibility:** the main board needs only SYS (1.8-5.5 V, >= 1 A) and GND on J10. A bought charger module
   that supplies SYS can replace the power board; pins 5-18 then stay open (CE pulled high by R20, INT high, I2C idle,
   the firmware sees no device at 0x6B and runs without charger control). USB charging then needs the module's own input.

### Bring-up: main board alone
Bench supply on J10 pins 1/2 (SYS) and a GND pin: 3.3-4.2 V, current limit 0.5 A. **Never above 5.5 V** (TPS63802
recommended VIN maximum, abs max 6 V; TPS61023 5.5 V). USB-C then works for programming and USB-JTAG, but USB VBUS
alone does not power the main board: VBUS goes only to J10. (Optional dev jumper USB_VBUS -> SYS: decision in
main-board/PARTS-REVIEW.md C2.)

### Mechanics
Stacked: the main board carries J10 as a socket (or pins) at the same top-view position as the power board's J10 with
pin 1 on the same corner, so the mapping is 1:1. Stack versus side-by-side is open (REQUIREMENTS-system.md 10.5).
