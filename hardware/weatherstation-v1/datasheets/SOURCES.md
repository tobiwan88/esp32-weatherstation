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
| SMBJ10A (PV TVS, Littelfuse, C151250) | MISSING (LCSC and littelfuse.com return HTML) | ratings from DigiKey listing 285966: standoff 10 V, breakdown 11.1-12.3 V, clamp 17 V at 35.3 A, 600 W | distributor data, maker PDF open |
| CMF4532F-900-2P-T (L3, C963746) | MISSING (family file on hand covers -102 only) | LCSC PDF from jlcparts | open |
| USBLC6-2SC6 (U4, U5) | MISSING | st.com CD00050750 URL did not download; alldatasheet returned HTML | open |
| NCP18XH103F03RB (TH1) | MISSING | Murata product page not fetched; LCSC C13564 page is HTML | open |
| CBAK 26700LT | MISSING | no spec sheet found by search; the cell spec read earlier came from the vendor (cells.md) | open |
| WPN201610HR47MT (L4) | Sunlord_WPN.pdf | Sunlord WPN series spec rev. 2018/12/13, LCSC copy https://atta.szlcsc.com/upload/public/pdf/source/20190118/C279949_8691A842418E258E770FD4F4C03A4887.pdf; HR47MT: 0.47 uH, DCR 49 mohm max, Isat 4.0 A max / 4.7 typ, Irms 2.7 / 3.1 A; land a 0.7 / b 0.7 / c 1.7 | OK |
| TYPE-C-31-M-12 (J1) | MISSING | earlier download was HTML | open |
| VLS252010HBX-1R0M-1 (L1, L5, C88211) | TDK_VLS252010HBX-1.pdf | TDK catalogue 20160411 (Chinese edition), LCSC copy https://atta.szlcsc.com/upload/public/pdf/source/20161226/1482720146834.pdf; 1R0M-1: Rdc 65 mohm max, Isat 3.22 A max-rated / 3.57 typ, Itemp 2.55 / 3.00 A; land 0.6 / 1.3 / 0.6 x 2.0 (page 5) | OK |
