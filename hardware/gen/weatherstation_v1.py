"""weatherstation-v1 schematic: BQ25798 charger for USB-C and a PV panel, ESP32-S3-WROOM-1, 3.3 V LDO,
switched sensor rail, PMS7003 PM sensor and ZE25-O3 on a switched 5 V rail, SHT45 cable, optional SCD41 (DNP).

PARTS and NETS are the source of truth. check_nets() compares them with KiCad's own netlist.
Drawing: each pin gets a short stub with a net label (global label when the net crosses sheets,
local label otherwise). GND and +3V3 are power symbols. Unused pins get no-connect markers.
Values marked "candidate" or "confirm" are not final: see hardware/weatherstation-v1/usb-charger-bq25798.md.

Run: uv run --package weatherstation-hardware python hardware/gen/weatherstation_v1.py [out_dir]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boardgen import JLC_CLASS, Generator, check_nets, pin_direction  # noqa: E402,F401  (registers the project symbol library)
from layout_v1 import BLOCKS, HAND_LABELS, HAND_ROUTES, TAG_POS, TAGS_BELOW, SHEET_NOTES, ROOT_BOX, SHEET_COLOR, SHEET_PURPOSE  # noqa: E402,F401

R0603, C0603, C0805 = "Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric", "Capacitor_SMD:C_0805_2012Metric"
C0402, R0402 = "Capacitor_SMD:C_0402_1005Metric", "Resistor_SMD:R_0402_1005Metric"
JST_PH2 = "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"
TP = "TestPoint:TestPoint_Pad_D1.5mm"
SHEET_FILES = {"Input": "input.kicad_sch", "Charger": "charger.kicad_sch", "Battery": "battery.kicad_sch", "MCU": "mcu.kicad_sch",
               "Rails": "rails.kicad_sch", "Sensors": "sensors.kicad_sch"}
SHEET_NOTE = SHEET_NOTES

# ref: (symbol, value, footprint, LCSC or None, sheet)
PARTS = {
    # --- Input -------------------------------------------------------------------------------
    "J1": ("Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948", "Input"),
    "U4": ("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6 (USB)", "Package_TO_SOT_SMD:SOT-23-6", "C7519", "Input"),
    "R9": ("Device:R", "5.1k", R0402, "C25905", "Input"),
    "R10": ("Device:R", "5.1k", R0402, "C25905", "Input"),
    "M1": ("Transistor_FET:AO3400A", "AO3400A ACFET1 (N-channel, BQ25798 back-to-back)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Input"),
    "M2": ("Transistor_FET:AO3400A", "AO3400A RBFET1 (N-channel, BQ25798 back-to-back)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Input"),
    "M3": ("Transistor_FET:AO3400A", "AO3400A ACFET2 (N-channel, BQ25798 back-to-back)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Input"),
    "M4": ("Transistor_FET:AO3400A", "AO3400A RBFET2 (N-channel, BQ25798 back-to-back)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Input"),
    "R11": ("Device:R", "300 (candidate; figure 294)", R0603, "C23025", "Input"),
    "R12": ("Device:R", "300 (candidate; figure 294)", R0603, "C23025", "Input"),
    "C1": ("Device:C", "0.1u", C0402, "C307331", "Input"),
    "C2": ("Device:C", "0.1u", C0402, "C307331", "Input"),
    # 6 V class PV panel (Voc about 8 V cold): SMBJ10A standoff 10 V, clamp 17 V, below the 30 V abs max of VAC2/AO3400A
    # (PARTS-REVIEW A6, decided 2026-11-01). Littelfuse part.
    "D1": ("Device:D_TVS", "SMBJ10A (PV surge, standoff 10 V, clamp 17 V)", "Diode_SMD:D_SMB", "C151250", "Input"),
    # 2-line common-mode choke on the PV pair, >= 1 A. Pinout from EMTEK spec T-0602-102D (equivalent circuit):
    # winding A = 1 (in, top left) -> 2 (out, top right); winding B = 4 (in, bottom left) -> 3 (out, bottom right).
    # Footprint: project library weatherstation:CMF4532F_4P (land pattern from section 7-1).
    # 10 W 6 V panel: up to 1.7 A. The -900 variant: 3 A, 70 mohm DCR, 90 ohm at 100 MHz (the -102/-601 have 300-400 mohm
    # per winding: about 1 V lost at 1.5 A). Same family and land pattern; its own datasheet page still to check.
    "L3": ("weatherstation:CMC_2line", "CM choke 90 ohm 3 A (CMF4532F-900-2P-T; datasheet page to confirm)", "weatherstation:CMF4532F_4P", "C963746", "Input"),
    "J5": ("Connector_Generic:Conn_01x02", "PV IN", JST_PH2, None, "Input"),
    "#FLG1": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Input"),
    "#FLG2": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Input"),
    "#FLG12": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Input"),
    # --- Charger -----------------------------------------------------------------------------
    "U3": ("Battery_Management:BQ25798", "BQ25798RQMR", "Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm", "C2876593", "Charger"),
    "L1": ("Device:L", "1uH (TDK VLS252010HBX-1R0M-1: Isat 3.22 A, Itemp 2.55 A, 65 mohm max)", "weatherstation:L_TDK_VLS252010", "C88211", "Charger"),
    # Cell overcurrent backup: PTC hold 3 A, trip 5 A, 8 V. Backup to the HY2112 overcurrent cut.
    "F1": ("Device:Fuse", "PTC 3 A hold (SMD1812P300TF)", "Fuse:Fuse_1812_4532Metric", "C21004", "Battery"),
    "C3": ("Device:C", "47n", C0603, "C1622", "Charger"),
    "C4": ("Device:C", "47n", C0603, "C1622", "Charger"),
    "C5": ("Device:C", "4.7u", C0603, "C19666", "Charger"),
    "C6": ("Device:C", "0.1u", C0402, "C307331", "Charger"),
    "C7": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C8": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C9": ("Device:C", "0.1u", C0402, "C307331", "Charger"),  # 0402 on the pin row (SLUSDV2C 8.4.1 item 1), 50 V
    "C10": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C11": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C12": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C13": ("Device:C", "0.1u", C0402, "C307331", "Charger"),
    "C14": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C15": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C16": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C17": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C18": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C19": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C20": ("Device:C", "10u", C0805, "C15850", "Charger"),
    "C21": ("Device:C", "1n", C0402, "C1523", "Charger"),
    "R13": ("Device:R", "100", R0402, "C25076", "Charger"),
    "R14": ("Device:R", "3.0k (PROG: 1S, 1.5 MHz)", R0603, "C4211", "Charger"),
    "R15": ("Device:R", "120k (ILIM: REGN 5 V x 100/220 = 2.27 V -> 1.59 A clamp)", R0603, "C25808", "Charger"),
    "R16": ("Device:R", "100k", R0402, "C25741", "Charger"),
    "R17": ("Device:R", "5.1k (TS top; thresholds about +0.9 C vs 5.24k/30.31k)", R0402, "C25905", "Charger"),
    "R18": ("Device:R", "30k (TS bottom)", R0603, "C22984", "Charger"),
    "R19": ("Device:R", "2.2k", R0402, "C25879", "Charger"),
    "D2": ("Device:LED", "STAT red", "LED_SMD:LED_0603_1608Metric", "C2286", "Charger"),
    "R20": ("Device:R", "100k", R0402, "C25741", "Charger"),
    "R22": ("Device:R", "10k", R0402, "C25744", "Charger"),
    # Charger I2C bus (IO1 SDA / IO2 SCL: the RTC I2C pins of the ULP RISC-V driver) has its own 10k pull-ups to +3V3: readable while the sensor rail is off (PARTS-REVIEW A4).
    "R54": ("Device:R", "10k", R0402, "C25744", "Charger"),
    "R55": ("Device:R", "10k", R0402, "C25744", "Charger"),
    # Battery connector (hand-soldered): 1 BAT+, 2 BAT-. The cell NTC TH1 is on the board next to J6 (same cell temperature
    # as far as a board can tell; mount the holder close to the board edge where TH1 sits). TH1 bottom on GND like the TS
    # divider R18 (figure 8-1), not on the cell negative: PARTS-REVIEW B2.
    "J6": ("Connector_Generic:Conn_01x02", "BATTERY", JST_PH2, None, "Battery"),
    "TH1": ("Device:Thermistor_NTC", "10k NTC NCP18XH103F03RB (TS, next to J6)", R0603, "C13564", "Battery"),
    "#FLG3": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Charger"),
    "#FLG13": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Battery"),
    "#FLG14": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Battery"),
    # HY2112-CB (LiFePO4 1-cell protection, OVP 3.75 V / release 3.60 V, ODP 2.10 V / release 2.30 V, discharge OC 200 mV,
    # charge OC -200 mV, 0 V charge available). Pack negative = two common-drain N-FETs: M60 (OD, discharge, source on cell -), M61 (OC, charge, source on PB-).
    # Wiring follows HY2112 datasheet section 10: VDD via R60 100 ohm + C60 0.1 uF, CS via R61 2 kohm to PB- (system GND).
    "U6": ("weatherstation:HY2112-CB", "HY2112-CB LiFePO4 protection", "Package_TO_SOT_SMD:SOT-23-6", "C168764", "Battery"),
    "M60": ("Transistor_FET:AO3400A", "AO3400A discharge FET (OD)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Battery"),
    "M61": ("Transistor_FET:AO3400A", "AO3400A charge FET (OC)", "Package_TO_SOT_SMD:SOT-23", "C20917", "Battery"),
    "R60": ("Device:R", "100 (HY2112 VDD)", R0402, "C25076", "Battery"),
    "C60": ("Device:C", "0.1u (HY2112 VDD)", C0402, "C307331", "Battery"),
    "R61": ("Device:R", "2k (HY2112 CS)", R0402, "C4109", "Battery"),
    # --- MCU ---------------------------------------------------------------------------------
    "U1": ("RF_Module:ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N8", "RF_Module:ESP32-S3-WROOM-1", "C2913198", "MCU"),
    "C30": ("Device:C", "22u", C0805, "C45783", "MCU"),
    "C31": ("Device:C", "100n", C0402, "C307331", "MCU"),
    "C32": ("Device:C", "1u", C0402, "C52923", "MCU"),
    "R30": ("Device:R", "10k", R0402, "C25744", "MCU"),
    "C33": ("Device:C", "1u", C0402, "C52923", "MCU"),
    # RESET and BOOT as tweezer pads (engineer 2026-11-03: the 5.1 mm buttons are too big; short with tweezers). Not
    # assembled. Normal flashing needs neither: esptool resets the S3 over USB-JTAG; the pads recover a board whose
    # firmware sleeps or disables USB (short BOOT, then RESET).
    "JP1": ("Jumper:SolderJumper_2_Open", "RESET", "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", None, "MCU"),
    "R31": ("Device:R", "10k", R0402, "C25744", "MCU"),
    "JP2": ("Jumper:SolderJumper_2_Open", "BOOT", "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", None, "MCU"),
    "R32": ("Device:R", "22", R0402, "C25092", "MCU"),
    "R33": ("Device:R", "22", R0402, "C25092", "MCU"),
    # two status LEDs (engineer 2026-11-03), active high on IO41/IO42 (module pins 34/35, free; JTAG pins only if the
    # pad-JTAG eFuse is burnt, not used here). Same red 0603 as D2 (Basic, Vf about 2 V); 1k gives about 1.3 mA.
    "R34": ("Device:R", "1k", R0402, "C11702", "MCU"),
    "D10": ("Device:LED", "LED1 red", "LED_SMD:LED_0603_1608Metric", "C2286", "MCU"),
    "R35": ("Device:R", "1k", R0402, "C11702", "MCU"),
    "D11": ("Device:LED", "LED2 red", "LED_SMD:LED_0603_1608Metric", "C2286", "MCU"),
    "J7": ("Connector_Generic:Conn_01x04", "DEBUG UART", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", None, "MCU"),
    # --- Rails -------------------------------------------------------------------------------
    # 3.3 V buck-boost (replaces the AP2112K LDO: the LDO needs about 3.55 V in, and both cells sit below that).
    # Symbol: project library (pins from TI SLVSEU9D table 7-1). Footprint: project library, drawn from the TI DLA0010A example
    # board layout (build_footprints.py; PARTS-REVIEW B6).
    "U2": ("weatherstation:TPS63802DLA", "TPS63802DLA 3.3 V buck-boost", "weatherstation:TPS63802_DLA_VSON-HR-10_2x3mm", "C2845237", "Rails"),
    "L4": ("Device:L", "0.47uH (Sunlord WPN201610HR47MT: Isat 4.0 A max, Irms 2.7 A)", "weatherstation:L_Sunlord_WPN201610H", "C97009", "Rails"),
    "R52": ("Device:R", "220k 1% (FB top: 0.5 V x (1 + 220k/39k) = 3.32 V)", R0603, "C22961", "Rails"),
    "R53": ("Device:R", "39k 1% (FB bottom, datasheet max 100k)", R0603, "C23153", "Rails"),
    "C40": ("Device:C", "10u", C0603, "C19702", "Rails"),
    "C41": ("Device:C", "22u (TPS63802 output: 22 uF per table 10-1)", C0805, "C45783", "Rails"),
    "Q40": ("Transistor_FET:AO3401A", "AO3401A 3V3_SW switch", "Package_TO_SOT_SMD:SOT-23", "C15127", "Rails"),
    "R40": ("Device:R", "100k", R0402, "C25741", "Rails"),
    "Q41": ("Transistor_FET:2N7002", "2N7002 (sensor enable)", "Package_TO_SOT_SMD:SOT-23", "C8545", "Rails"),
    "R41": ("Device:R", "1k", R0402, "C11702", "Rails"),
    "R42": ("Device:R", "100k", R0402, "C25741", "Rails"),
    "C42": ("Device:C", "22u", C0805, "C45783", "Rails"),
    "C43": ("Device:C", "22u", C0805, "C45783", "Rails"),
    # 5V_SW 5 V boost for the ZE25-O3 (3.7-5.5 V; PARTS-REVIEW A5, decided 2026-11-01). TPS61023 (TI SLVSF14B): VIN 0.5-5.5 V
    # (start 1.8 V), true input/output disconnect and 0.1 uA in shutdown, so EN low = J8 unpowered. EN from BOOST_EN (IO12),
    # R45 pulls EN low = off by default (reset, deep sleep without hold). Figure 8-1 circuit: 1 uH, 10 uF in, 2 x 22 uF out.
    # FB: VREF 0.595 V x (1 + 510k/68k) = 5.06 V (580-610 mV: 4.93-5.18 V, OVP 5.5 V min). Values reuse BOM lines.
    "U7": ("weatherstation:TPS61023DRL", "TPS61023DRLR 5 V boost", "Package_TO_SOT_SMD:SOT-563", "C919459", "Rails"),
    "L5": ("Device:L", "1uH (VLS252010HBX-1R0M-1, same as L1)", "weatherstation:L_TDK_VLS252010", "C88211", "Rails"),
    "R43": ("Device:R", "510k 1% (boost FB top: 0.595 V x (1 + 510k/68k) = 5.06 V)", R0603, "C23192", "Rails"),
    "R44": ("Device:R", "68k 1% (boost FB bottom)", R0603, "C23231", "Rails"),
    "R45": ("Device:R", "100k (EN pull-down: boost off by default)", R0402, "C25741", "Rails"),
    "C44": ("Device:C", "10u (boost input)", C0603, "C19702", "Rails"),
    "C45": ("Device:C", "22u (boost output)", C0805, "C45783", "Rails"),
    "C46": ("Device:C", "22u (boost output)", C0805, "C45783", "Rails"),
    "TP1": ("Connector:TestPoint", "+3V3", TP, None, "Rails"),
    "TP2": ("Connector:TestPoint", "SYS", TP, None, "Rails"),
    "#FLG10": ("power:PWR_FLAG", "PWR_FLAG", None, None, "Rails"),
    # --- Sensors -----------------------------------------------------------------------------
    # PM sensor (option A, user 2026-11-01): Plantower PMS7003 on its 2x5 1.27 mm cable (manual V2.5): 1/2 VCC 5 V (4.5-5.5 V,
    # <= 100 mA, standby <= 200 uA), 3/4 GND, 5 RESET (internal pull-up, open), 6/8 NC, 7 RX, 9 TX, 10 SET (high/open = run,
    # low = sleep); data pins 3.3 V TTL. Stable data 30 s after wake-up. R48/R49 1k limit current into an unpowered module.
    "J2": ("Connector_Generic:Conn_02x05_Odd_Even", "PMS7003 (2x5 1.27 mm)", "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical", None, "Sensors"),
    "R48": ("Device:R", "1k (PM RX series)", R0402, "C11702", "Sensors"),
    "R49": ("Device:R", "1k (PM SET series)", R0402, "C11702", "Sensors"),
    # optional CO2: Sensirion SCD41-D-R2 (LCSC C3659294), footprint only (DNP) until CO2 is wanted. Datasheet SCD4x v1.7:
    # VDD 2.4-5.5 V, peak 205 mA max at 3.3 V, ripple <= 30 mV; VDD and VDDH tied at the sensor; single shot 0.45 mA avg (1/5 min).
    "U8": ("Sensor_Gas:SCD41-D-R2", "SCD41 DNP (C3659294)", "Sensor:Sensirion_SCD4x-1EP_10.1x10.1mm_P1.25mm_EP4.8x4.8mm", None, "Sensors"),
    "C47": ("Device:C", "10u (SCD41 VDD)", C0603, "C19702", "Sensors"),
    "J3": ("Connector_Generic:Conn_01x04", "SHT45 cable", "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal", "C160404", "Sensors"),
    "U5": ("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6 (I2C)", "Package_TO_SOT_SMD:SOT-23-6", "C7519", "Sensors"),
    # Sensor I2C bus (IO13/IO14): pull-ups and U5 VBUS on 3V3_SW, so nothing back-powers the sensors when the rail is off.
    # Firmware sets IO13/IO14 to input (or low) before switching 3V3_SW off (PARTS-REVIEW A4).
    "R50": ("Device:R", "10k", R0402, "C25744", "Sensors"),
    "R51": ("Device:R", "10k", R0402, "C25744", "Sensors"),
    # ZE25-O3 7-pin (Winsen table 2, user screenshot 2026-11-01): 1 reserved, 2 DAC 0.4-2.0 V = 0-10 ppm, 3 GND,
    # 4 Vin 3.7-5.5 V, 5 RXD (0-3.0 V input), 6 TXD (0-3.0 V output), 7 reserved. Pin numbers 1:1 to the module.
    "J8": ("Connector_Generic:Conn_01x07", "ZE25-O3 (cable pitch to confirm)", "Connector_JST:JST_PH_B7B-PH-K_1x07_P2.00mm_Vertical", None, "Sensors"),
    # module RXD accepts 0-3.0 V: ESP32 TX (3.3 V) through R46 1k with R47 10k to GND = 3.0 V
    "R46": ("Device:R", "1k (GAS RXD level: 3.3 V x 10/11 = 3.0 V)", R0402, "C11702", "Sensors"),
    "R47": ("Device:R", "10k", R0402, "C25744", "Sensors"),
}

# Big parts placed by hand (cell x, cell y, rotation). Everything else is auto-placed on its sheet.
# net name -> pins (ref, pin). GND and +3V3 are power symbols; flags (#FLG) make a net powered for ERC.
NETS = {
    # Input sheet: USB-C, ESD, USB ACFET1/RBFET1, PV TVS, ACFET2/RBFET2
    "USB_VBUS": [("J1", "A4"), ("J1", "A9"), ("J1", "B4"), ("J1", "B9"), ("U4", "5"), ("M1", "3"), ("C1", "1"), ("U3", "9"), ("#FLG1", "1")],
    "ACF1_MID": [("M1", "2"), ("M2", "2")],
    "ACG1": [("M1", "1"), ("M2", "1"), ("R11", "1")],
    "ACDRV1": [("R11", "2"), ("U3", "11")],
    "VBUS": [("M2", "3"), ("M4", "3"), ("U3", "2"), ("U3", "3"), ("C6", "1"), ("C7", "1"), ("C8", "1"), ("#FLG3", "1")],
    "PV_RAW": [("J5", "1"), ("D1", "1"), ("L3", "1")],
    "PV_N_RAW": [("J5", "2"), ("D1", "2"), ("L3", "4")],
    "PV_IN": [("L3", "2"), ("C2", "1"), ("M3", "3"), ("U3", "8"), ("#FLG2", "1")],
    "ACF2_MID": [("M3", "2"), ("M4", "2")],
    "ACG2": [("M3", "1"), ("M4", "1"), ("R12", "1")],
    "ACDRV2": [("R12", "2"), ("U3", "10")],
    "CC1": [("J1", "A5"), ("R9", "1")],
    "CC2": [("J1", "B5"), ("R10", "1")],
    "USB_DP": [("J1", "A6"), ("J1", "B6"), ("U4", "1"), ("U4", "6"), ("U3", "6"), ("R32", "1")],
    "USB_DN": [("J1", "A7"), ("J1", "B7"), ("U4", "3"), ("U4", "4"), ("U3", "7"), ("R33", "1")],
    # Charger sheet
    "REGN": [("U3", "5"), ("C5", "1"), ("R15", "1"), ("R17", "1"), ("R19", "1")],
    "BTST1": [("U3", "4"), ("C3", "1")],
    "SW1": [("U3", "28"), ("C3", "2"), ("L1", "1")],
    "BTST2": [("U3", "19"), ("C4", "1")],
    "SW2": [("U3", "26"), ("C4", "2"), ("L1", "2")],
    "PMID": [("U3", "29"), ("C9", "1"), ("C10", "1"), ("C11", "1"), ("C12", "1")],
    "SYS": [("U3", "25"), ("C13", "1"), ("C14", "1"), ("C15", "1"), ("C16", "1"), ("C17", "1"), ("C18", "1"),
            ("U2", "10"), ("U2", "1"), ("C40", "1"), ("U7", "3"), ("L5", "1"), ("C44", "1"), ("TP2", "1")],
    "BAT_CON": [("J6", "1"), ("F1", "1")],
    # BAT caps C19/C20 on BAT (table 5-1: 2 x 10 uF at BAT); BATP only senses through R13 100 ohm (review A3)
    "BAT_PACK": [("U3", "22"), ("U3", "23"), ("R13", "1"), ("F1", "2"), ("R60", "1"), ("C19", "1"), ("C20", "1")],
    "BAT_N": [("J6", "2"), ("U6", "6"), ("C60", "2"), ("M60", "2"), ("#FLG14", "1")],
    "HY_VDD": [("R60", "2"), ("C60", "1"), ("U6", "5"), ("#FLG13", "1")],
    "OD": [("U6", "1"), ("M60", "1")],
    "OC": [("U6", "3"), ("M61", "1")],
    "PB_MID": [("M60", "3"), ("M61", "3")],  # common drain (HY2112 section 10, review A1)
    "HY_CS": [("U6", "2"), ("R61", "1")],
    "BATP": [("U3", "18"), ("R13", "2")],
    "SDRV": [("U3", "24"), ("C21", "1")],
    "PROG": [("U3", "20"), ("R14", "1")],
    "ILIM": [("U3", "17"), ("R15", "2"), ("R16", "1")],
    "TS": [("U3", "16"), ("R17", "2"), ("R18", "1"), ("TH1", "1")],
    "STAT": [("U3", "1"), ("D2", "1")],
    "LED_A": [("R19", "2"), ("D2", "2")],
    "CHG_CE": [("U3", "13"), ("R20", "2"), ("U1", "17")],
    # QON (pin 12) left open: internal pull-up (PARTS-REVIEW C, R21 removed 2026-11-01); no-connect marker.
    "CHG_INT": [("U3", "21"), ("R22", "1"), ("U1", "18")],
    # Two I2C buses (PARTS-REVIEW A4): charger on IO1/IO2 (always powered; RTC I2C, so the ULP core can manage charging in
    # deep sleep: ESP-IDF ulp_riscv_i2c allows SDA IO1/IO3, SCL IO0/IO2), sensors on IO13/IO14 (3V3_SW).
    "CHG_SDA": [("U3", "15"), ("U1", "39"), ("R54", "1")],
    "CHG_SCL": [("U3", "14"), ("U1", "38"), ("R55", "1")],
    "SEN_SDA": [("U1", "21"), ("U8", "10"), ("J3", "3"), ("R50", "1"), ("U5", "1"), ("U5", "6")],
    "SEN_SCL": [("U1", "22"), ("U8", "9"), ("J3", "4"), ("R51", "1"), ("U5", "3"), ("U5", "4")],
    # MCU sheet
    "EN": [("U1", "3"), ("R30", "2"), ("C33", "1"), ("JP1", "1")],
    "IO0": [("U1", "27"), ("R31", "2"), ("JP2", "1")],
    "LED1": [("U1", "34"), ("R34", "1")],
    "LED1_A": [("R34", "2"), ("D10", "2")],
    "LED2": [("U1", "35"), ("R35", "1")],
    "LED2_A": [("R35", "2"), ("D11", "2")],
    "ESP_DP": [("R32", "2"), ("U1", "14")],
    "ESP_DN": [("R33", "2"), ("U1", "13")],
    "TXD0": [("U1", "37"), ("J7", "2")],
    "RXD0": [("U1", "36"), ("J7", "3")],
    "SENSOR_EN": [("U1", "19"), ("R41", "1")],
    "BOOST_EN": [("U1", "20"), ("U7", "2"), ("R45", "1")],
    "GAS_TXD": [("U1", "10"), ("R46", "1")],
    "GAS_RXIN": [("R46", "2"), ("R47", "1"), ("J8", "5")],
    "GAS_RXD": [("U1", "11"), ("J8", "6")],
    "GAS_DAC": [("U1", "7"), ("J8", "2")],  # IO7 = ADC1: backup reading if the UART fails
    # Rails sheet
    "3V3_SW": [("Q40", "3"), ("C42", "1"), ("C43", "1"), ("U8", "7"), ("U8", "19"), ("C47", "1"), ("J3", "2"), ("U5", "5"), ("R50", "2"), ("R51", "2"),
               ("#FLG10", "1")],
    "SEN_G": [("Q40", "1"), ("R40", "2"), ("Q41", "3")],
    "SEN_EN_G": [("Q41", "1"), ("R41", "2"), ("R42", "1")],
    "GAS_SW": [("U7", "5"), ("L5", "2")],
    "GAS_FB": [("U7", "1"), ("R43", "2"), ("R44", "1")],
    "5V_SW": [("U7", "6"), ("R43", "1"), ("C45", "1"), ("C46", "1"), ("J8", "4"), ("J2", "1"), ("J2", "2")],
    "PM_TXD": [("U1", "4"), ("R48", "1")],     # IO4 = UART2 TX
    "PM_RXIN": [("R48", "2"), ("J2", "7")],
    "PM_RXD": [("U1", "5"), ("J2", "9")],      # IO5 = UART2 RX
    "PM_SET": [("U1", "6"), ("R49", "1")],     # IO6: low = PMS7003 sleep (fan off) while 5V_SW stays on for the O3 module
    "PM_SETIN": [("R49", "2"), ("J2", "10")],
    # Power symbols
    # R20 (CE pull-up) on +3V3, not REGN: CE is also an ESP32 GPIO (3.3 V I/O). PARTS-REVIEW A7.
    "+3V3": [("R20", "1"), ("U1", "2"), ("C30", "1"), ("C31", "1"), ("C32", "1"), ("R30", "1"), ("R31", "1"), ("J7", "1"), ("R22", "2"),
             ("R54", "2"), ("R55", "2"), ("TP1", "1"), ("U2", "6"), ("C41", "1"), ("Q40", "2"), ("R40", "1"), ("R52", "1")],
    "BUCK_L1": [("U2", "9"), ("L4", "1")],
    "BUCK_L2": [("U2", "7"), ("L4", "2")],
    "FB": [("U2", "4"), ("R52", "2"), ("R53", "1")],
    "GND": [("J1", "A1"), ("J1", "A12"), ("J1", "B1"), ("J1", "B12"), ("J1", "SH"), ("U4", "2"), ("R9", "2"), ("R10", "2"),
            ("C1", "2"), ("C2", "2"), ("L3", "3"), ("M61", "2"), ("R61", "2"), ("R53", "2"), ("U2", "2"), ("U2", "3"), ("U2", "8"),
            ("U3", "27"), ("TH1", "2"), ("C5", "2"), ("C6", "2"), ("C7", "2"), ("C8", "2"),
            ("C9", "2"), ("C10", "2"), ("C11", "2"), ("C12", "2"), ("C13", "2"), ("C14", "2"), ("C15", "2"), ("C16", "2"),
            ("C17", "2"), ("C18", "2"), ("C19", "2"), ("C20", "2"), ("C21", "2"), ("R14", "2"), ("R16", "2"), ("R18", "2"),
            ("U1", "1"), ("U1", "40"), ("U1", "41"), ("C30", "2"), ("C31", "2"), ("C32", "2"),
            ("C33", "2"), ("JP1", "2"), ("JP2", "2"), ("D10", "1"), ("D11", "1"), ("J7", "4"), ("C40", "2"), ("C41", "2"), ("Q41", "2"),
            ("R42", "2"), ("C42", "2"), ("C43", "2"), ("U7", "4"), ("R44", "2"), ("R45", "2"), ("C44", "2"), ("C45", "2"),
            ("C46", "2"), ("J2", "3"), ("J2", "4"), ("U8", "6"), ("U8", "20"), ("U8", "21"), ("C47", "2"), ("J3", "1"),
            ("U5", "2"), ("J8", "3"), ("R47", "2"), ("#FLG12", "1")],
}
# Rails: drawn as a power symbol on every pin (never routed as a wire, no hierarchical label). This is how an engineer
# reads a schematic: a capacitor with a rail symbol on top and GND below is decoupling for that rail, no wire to trace.
POWER_SYMBOLS = ("GND", "+3V3", "3V3_SW", "SYS", "VBUS", "USB_VBUS", "PMID", "REGN", "5V_SW", "BAT_PACK")
RAIL_LIB = {"GND": "power:GND", "+3V3": "power:+3V3", "VBUS": "power:VBUS"}  # others: power:VCC with the net as value


SHEET_VALUE = {"L3": "CMC 90R 3A", "L4": "0.47uH", "U4": "USBLC6-2SC6", "U5": "USBLC6-2SC6", "F1": "PTC 3A",
               "TH1": "10k NTC", "U6": "HY2112-CB", "U2": "TPS63802",
               **{m: "AO3400A" for m in ("M1", "M2", "M3", "M4", "M60", "M61")}, "Q40": "AO3401A",
               "Q41": "2N7002", "U7": "TPS61023", "L5": "1uH"}

HAND_SOLDER = {"J2", "J5", "J6", "J7", "J8"}  # JST PH and pin header: hand-soldered, not in the assembly BOM
TP_NOTE = "GND/3V3 test pads"
SHEET_TITLE_Y = 3  # v1 drawing kept as it was reviewed
PROJECT, TITLE, SHEET_PREFIX = "weatherstation-v1", "weatherstation v1", "weatherstation v1"
ROOT_TEXTS = [(6, 6, "#weatherstation v1 (esp32-weatherstation): block diagram"),
              (6, 10, "Each box is a sheet. Wires join the sheet pins, which are the hierarchical labels inside each sheet."),
              (6, 96, "Power path: USB-C or PV -> Input (ACFET/RBFET pairs) -> VBUS -> Charger (BQ25798) -> SYS -> Rails (TPS63802) -> +3V3 -> 3V3_SW;"),
              (6, 98, "SYS -> TPS61023 5 V boost -> 5V_SW. Cell: Battery (HY2112, PTC) <-> BAT_PACK <-> Charger. Rails (GND, +3V3, SYS, VBUS, ...) are power symbols on each sheet, not wires here."),
              (6, 101, "Open engineer decisions: hardware/weatherstation-v1/PARTS-REVIEW.md (parts and circuit review, 2026-11-01).")]

# The drawing engine is shared with the power and main boards (boardgen.py, factored out 2026-11-21; output unchanged).
_G = Generator(sys.modules[__name__])
UNWIRED = _G.UNWIRED
draw, layout_positions, build, write_bom, drawing_issues = _G.draw, _G.layout_positions, _G.build, _G.write_bom, _G.drawing_issues
sheets_of, short_value, root_interfaces = _G.sheets_of, _G.short_value, _G.root_interfaces


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("hardware/weatherstation-v1")
    path = build(out)
    write_bom(out / "bom.csv")
    errors = check_nets(path, NETS) + drawing_issues()
    print("\n".join(errors) or f"{path}: nets OK; bom.csv written")
    sys.exit(1 if errors else 0)
