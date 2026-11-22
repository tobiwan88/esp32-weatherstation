# Firmware rules from the hardware

Rules the hardware depends on; each names its review item or datasheet section. Register addresses are checked against the datasheet when the driver is written.
1. Order at boot and wake before any charge: <watchdog, cell count, voltage, current, limits>
2. Power-on defaults to override: <register, POR value, value to write>
3. Charge suspend conditions (cold, hot) and who acts in deep sleep
4. Pin states before a rail is switched off; wait after a rail turns off or on (bleed time)
5. Clamps: values the code must never exceed
