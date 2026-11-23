# Hardware decisions that must not be lost

Carried over unchanged from CLAUDE.md on 2026-11-23, where they were written for the first single-board design. The three-board
split is described in `ARCHITECTURE.md` and `REQUIREMENTS-system.md`; confirm an item there before relying on it, and fix this file
in the same step as any decision (`hw-base`, changing a decision).

- 4 layers, In1 and In2 both solid GND; outline at most 50 x 50 mm (cheapest JLCPCB tier).
- USB-C = programming, debug (native USB-JTAG) and charging. One charger for USB and solar: BQ25798 (two inputs via ACFET/RBFET pairs), 1S LiFePO4 cell with HY2112-CB protection (commit 7db8d9c). CE pulled high = charge off until the firmware has written VREG 3.65 V (POR default is 4.2 V); firmware handles cold charging. Open circuit findings: `hardware/weatherstation-v1/PARTS-REVIEW.md`.
- Sensor rail 3V3_SW switched by a P-FET; SHT45 off-board in a radiation shield; PMS7003 on J2 (5V_SW, UART IO4/IO5);
  SEN66 dropped for cost (sensor option A, `hardware/weatherstation-v1/sensors.md`); no VOC/NOx; NO2 not on v1.
- Two I2C buses: charger on IO1/IO2 (RTC I2C, so the ULP core can manage charging in deep sleep; pull-ups to +3V3), sensors on
  IO13/IO14 (pull-ups on 3V3_SW). ZE25-O3 gas module (J8, 7-pin 1:1, UART IO17/IO18 with RXD divided to 3.0 V, DAC to IO7) on
  a TPS61023 5 V boost from SYS, EN = IO12 (BOOST_EN), off by default (pull-down, true disconnect).
- Solar charging stays on during deep sleep (user, 2026-11-01): CE held low by GPIO hold, chip JEITA active (`charge-policy.md`).
- 3.3 V from a TPS63802 buck-boost on SYS (the LDO and its 3.5 V cutoff are gone); HY2112 overdischarge 2.10 V is the hardware floor.
- Thermal: heat corner away from the NTC and sensor connectors. EMC: solid planes, antenna keepout on all layers, ESD on USB and the outdoor I2C cable, TVS on solar input.

