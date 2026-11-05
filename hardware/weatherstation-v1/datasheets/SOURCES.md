# Datasheets and app notes: sources

Downloaded for hardware/weatherstation-v1. Every file was checked to start with `%PDF`. The PDFs were not opened or parsed (only `file` and `ls` were used), so revision dates below come from vendor pages or search snippets, not from the PDF covers. Section and page values were NOT verified: the PDFs could not be read as text, so none are quoted here. Read them from the PDF before relying on them.

## Datasheets

| File | Source URL | Revision/date | Size (bytes) | Status |
|---|---|---|---|---|
| ESP32-S3-WROOM-1.pdf | https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf (301 redirect to documentation.espressif.com) | not verified (cover not read) | 1280501 | OK |
| AP2112K-3.3.pdf | https://www.diodes.com/assets/Datasheets/AP2112.pdf | not verified | 755270 | OK |
| CN3791.pdf | MISSING. Tried: https://www.consonance-elec.com/pdf/datasheet/CN3791.pdf (HTML); https://datasheet.lcsc.com/lcsc/2304140030_Consonance-CN3791_C154992.pdf (HTML); https://cdn.ozdisan.com/ETicaret_Dosya/1042683_888586535..pdf (HTTP 400); LCSC product page https://lcsc.com/product-detail/PMIC-Battery-Management_CN3791_C154992.html (no PDF link in first 100k chars). Search reports Rev 1.0 copies exist but none fetched. | n/a | 0 | MISSING |
| TP4056.pdf | https://dlnmh9ip6v2uc.cloudfront.net/datasheets/Prototyping/TP4056.pdf | not on cover as read; PDF metadata title "tp4056_42_English", creation 2008-05-04 (metadata only, not a revision) | 60920 | OK |
| USBLC6-2SC6.pdf | MISSING. Tried: https://www.st.com/resource/en/datasheet/cd00050750.pdf (timeout / HTTP2 error); https://www.st.com/resource/en/datasheet/usblc6-2.pdf (timeout). Document ID per search: CD00050750. | n/a | 0 | MISSING |
| AO3401A.pdf | http://www.aosmd.com/res/data_sheets/AO3401A.pdf | not verified | 326568 | OK |
| SMBJ12A.pdf | MISSING. Tried: https://datasheet.lcsc.com/lcsc/2304140030_Littelfuse-SMBJ12A_C151251.pdf (HTML); https://www.littelfuse.com/products/tvs-diodes/surface-mount/smbj.aspx (HTTP 403). Littelfuse SMBJ product page is the right entry point. | n/a | 0 | MISSING |
| SWPA6045S220MT.pdf | MISSING. Tried: https://datasheet.lcsc.com/lcsc/2310251551_Sunlord-SWPA6045S220MT_C83454.pdf (HTML); https://www.sunlordinc.com/upload/pdf/SWPA6045S.pdf (HTML); Sunlord product pages (no PDF link found). | n/a | 0 | MISSING |
| SEN66.pdf | https://sensirion.com/resource/datasheet/SEN6x (shared SEN6x datasheet, 61 pages; covers SEN66) | not verified on cover; PDF metadata shows 2026-10-06 (metadata, not revision) | 1700626 | OK |
| SHT45.pdf | https://sensirion.com/media/documents/33FD6951/6A7C10A0/HT_DS_Datasheet_SHT4x_V7.3.pdf (linked from https://sensirion.com/products/catalog/SHT45) | V7.3, 04/2025 (per Sensirion product page) | 1049911 | OK |
| TYPE-C-31-M-12.pdf | MISSING. Tried: https://www.lcsc.com/datasheet/lcsc_datasheet_2410010003_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf (HTML); https://www.krhro.com/upload/pdf/TYPE-C-31-M-12.pdf (HTTP 404); https://www.hro.com.tw/upload/pdf/TYPE-C-31-M-12.pdf (DNS failure). Viewer link from search: https://en.krhro.com/npublic/opdfjs/web/viewer.html (not fetched). Pin count conflicts across listings (12 vs 16); check the PDF. | n/a | 0 | MISSING |
| 2N7002.pdf | https://www.vishay.com/docs/70226/70226.pdf (Vishay, 8 pages). Alternative: onsemi 2n7002e-d.pdf returned HTTP 403 to curl. | not verified | 98640 | OK |
| BMP585.pdf | https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp585-ds003.pdf | BST-BMP585-DS003-02 rev 1.2 (read from the PDF, 2026-11-04) | 71 pages | OK |
| VEML6030.pdf | https://www.vishay.com/docs/84366/veml6030.pdf | doc. 84366 rev 1.8, 28-Nov-2024 (read from the PDF) | 14 pages | OK |

## App notes (appnotes/)

| File | Source URL | Revision/date | Size (bytes) | Status |
|---|---|---|---|---|
| appnotes/esp32-s3-hw-design-guidelines.pdf | https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/esp-hardware-design-guidelines-en-master-esp32s3.pdf (master/latest edition) | "Feb 21, 2024" per search snippet, not verified on cover | 4193812 | OK |
| appnotes/sht4x-design-guide.pdf | https://sensirion.com/media/documents/FC5BED84/662B494D/Sensirion_Humidity_Temperature_Design_Guide.pdf | 04/2024 (per Sensirion SHT4x page) | 841796 | OK |
| appnotes/sht4x-handling.pdf | https://sensirion.com/media/documents/6D95AA80/6840311F/HT_Handling_Instructions_SHTxx.pdf | 06/2025 (per Sensirion SHT4x page) | 481502 | OK |
| appnotes/sen6x-testing-guide.pdf | https://sensirion.com/media/documents/AE5564E4/6A58BFB5/PS_AN_SEN6x_Testing_And_Evaluation_Guide_D1.pdf | "v1.0, July 2026" per search snippet, not verified | 280080 | OK |
| CN3791 application circuit | MISSING (no separate vendor app note found; datasheet application circuit is the source once fetched) | n/a | 0 | MISSING |
| TP4056 typical application | n/a: no separate app note found; datasheet typical application applies | n/a | n/a | MISSING (covered by TP4056.pdf) |
| AP2112K application circuit | n/a: datasheet is used (no separate app note) | n/a | n/a | MISSING (covered by AP2112K-3.3.pdf) |
| SEN66 integration guide | MISSING. Sensirion "SEN6x Mechanical Design and Assembly Guidelines" not located as a direct PDF URL. Found instead: appnotes/sen6x-testing-guide.pdf. | n/a | 0 | MISSING |
| SHT4x integration guide | Not found as one document. Closest: appnotes/sht4x-design-guide.pdf and appnotes/sht4x-handling.pdf. | n/a | n/a | covered by the two files above |

## Required section numbers (not verified)

Values could not be read: the PDFs stay closed by rule, and WebFetch returns the compressed PDF streams without text. Fill these in from the PDFs.

| Item | Section/page | Value as it appears |
|---|---|---|
| CN3791 MPPT pin voltage | not verified (CN3791 MISSING) | not verified |
| CN3791 Vcs / charge current formula | not verified (CN3791 MISSING) | not verified |
| CN3791 Fig.1 C4 value | not verified (CN3791 MISSING) | not verified |
| AP2112K dropout at 600 mA | not verified | not verified |
| TP4056 PROG current formula | not verified | not verified |
| TP4056 TEMP pin | not verified | not verified |
| SEN66 supply voltage range | not verified | not verified |
| SEN66 operating temperature range | not verified | not verified |
| SEN66 I2C pull-up recommendation | not verified | not verified |
| SEN66 I2C address | not verified | not verified |
| ESP32-S3-WROOM-1 strapping pins | not verified | not verified |
| ESP32-S3-WROOM-1 reserved pins | not verified | not verified |

## Status update 2026-11-01 (design parts)
Obsolete entries (not in the v1 design any more): CN3791, TP4056, AP2112K-3.3, SWPA6045S220MT, SMBJ12A and SMBJ24A (now SMBJ10A), TYPE-C-31-M-12 only as a placeholder.

| Part (design) | Local file | Source | Status |
|---|---|---|---|
| BQ25798RQMR | BQ25798.pdf | TI SLUSDV2C (copy from earlier download) | OK, read as text |
| TPS63802DLA | TPS63802.pdf | TI (copy from earlier download) | OK |
| TPS61023DRLR | TPS61023.pdf | TI https://www.ti.com/lit/ds/symlink/tps61023.pdf (SLVSF14B, Aug 2020; read sections 5, 6, 7.3, 8.2) | OK |
| HY2112-CB | HY2112-CB.pdf | copy hosted by SIS (earlier download); maker URL blocked | OK, V08 |
| CMF4532F (CMF4532F-102-2P-T) | CMF4532F_EMTEK_T-0602-102D.pdf | EMTEK T-0602-102D | OK |
| AO3400A (ACFET/RBFET, M60/M61) | AO3400A.pdf | https://www.aosmd.com/res/datasheets/AO3400A.pdf | OK (AOS, 318 KB) |
| SMBJ10A (PV TVS, Littelfuse, C151250) | Littelfuse_SMBJ.pdf | Littelfuse SMBJ series, revised JC.07/04/25 v4 (supplied by the user); SMBJ10A row: VR 10.0 V, VBR 11.10-12.30 V at 1 mA, VC 17.0 V at Ipp 35.3 A, IR 5 uA, 600 W 10/1000 us | OK, read as text |
| CMF4532F-900-2P-T (L3, C963746) | text only (HongyeX spec HYSP-CM000XX version D2, 2025-09-19, pasted by the user) | maker on LCSC is HYHONGYEX, not EMTEK: 90 ohm +/-25 % at 100 MHz, DCR 0.07 ohm max, Ir 3000 mA, 50 V, -40 to +85 C, body 4.5 x 3.2 x 2.8, terminal E 1.2 / F 1.0 typ. No land pattern or pin drawing in the text: footprint and pinout still come from the EMTEK T-0602-102D drawing; check against a HongyeX drawing before layout | ratings OK; land pattern 2026-11-05: EMTEK 7-1 re-read (0.7 = row gap), agrees with the LCSC/EasyEDA footprint of C963746 |
| USBLC6-2SC6 (U4, U5) | USBLC6-2.pdf | ST DS4260 Rev 7, December 2021 (supplied by the user); SOT23-6L pins 1/6 I/O1, 2 GND, 3/4 I/O2, 5 VBUS; VBR 6 V min, VCL 12 V at 1 A / 17 V at 5 A, Ci/o-GND 2.5 pF typ | OK, read as text |
| NCP18XH103F03RB (TH1) | MISSING | Murata product page not fetched; LCSC C13564 page is HTML | open |
| CBAK 26700LT (BT1) | CBAK_26700LT_A03.pdf | Dalian CBAK 26700LT-4000mAh spec, version A/03 (supplied by the user); section 5.1: 4000 mAh typ / 3900 min, <= 20 mOhm, 3.20 V nominal, standard charge 3.65 V CC/CV 0.5C to 0.01C, limit 3.75 V (upper 3.8 V), cut-off 2.0 V; 5.2 charge rate -10..0 C 0.2C, 0..20 C 0.5C, 20..40 C 1C, 40..50 C 0.5C; 5.4 charging -10..50 C, discharging -40..60 C; 6.3 capacity -20 C >= 80 %, -30 C >= 70 %, -40 C >= 50 % | OK, read as text; board.yaml cell values match |
| WPN201610HR47MT (L4) | Sunlord_WPN.pdf | Sunlord WPN series spec rev. 2018/12/13, LCSC copy https://atta.szlcsc.com/upload/public/pdf/source/20190118/C279949_8691A842418E258E770FD4F4C03A4887.pdf; HR47MT: 0.47 uH, DCR 49 mohm max, Isat 4.0 A max / 4.7 typ, Irms 2.7 / 3.1 A; land a 0.7 / b 0.7 / c 1.7 | OK |
| TYPE-C-31-M-12 (J1) | MISSING | earlier download was HTML | open |
| VLS252010HBX-1R0M-1 (L1, L5, C88211) | TDK_VLS252010HBX-1.pdf | TDK catalogue 20160411 (Chinese edition), LCSC copy https://atta.szlcsc.com/upload/public/pdf/source/20161226/1482720146834.pdf; 1R0M-1: Rdc 65 mohm max, Isat 3.22 A max-rated / 3.57 typ, Itemp 2.55 / 3.00 A; land 0.6 / 1.3 / 0.6 x 2.0 (page 5) | OK |
| PMS7003 (J2) | PMS7003_manual_V2.5.pdf | Plantower PMS7003 manual V2.5, https://github.com/hackerspace-silesia/Smogomierz/files/3746439/PMS7003_manual.pdf; 4.5-5.5 V, <= 100 mA, standby <= 200 uA, stable 30 s after wake-up, 10-pin 1.27 mm pinout | OK, read as text |
| SCD41-D-R2 (U8, DNP) | SCD4x_v1.7.pdf | Sensirion SCD4x datasheet v1.7 April 2025, https://sensirion.com/media/documents/48C4B7FB/67FE0194/CD_DS_SCD4x_Datasheet_D1.pdf (LCSC link returned HTML); VDD 2.4-5.5 V, peak 205 mA max at 3.3 V, ripple <= 30 mV | OK, read as text |
| SEN66 (was J2) | SEN66.pdf | dropped 2026-11-01 (sensor option A, sensors.md) | obsolete |
