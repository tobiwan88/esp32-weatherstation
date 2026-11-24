"""Writes the project footprints in hardware/gen/lib/weatherstation.pretty (land patterns taken from the maker drawings).

Each footprint names its source in the descr. Courtyard = pads and body + 0.25 mm. Run: python3 hardware/gen/build_footprints.py

- TPS63802_DLA: TI SLVSEU9 package DLA0010A (VSON-HR 10, 2 x 3 mm), "Example board layout" (4223750/D):
  pins 1-5 left, x = -0.9, 0.6 x 0.25; pins 6, 7, 9, 10 right, x = +0.75, 0.9 x 0.25; pin 8 (GND) bar 1.3 x 0.25 at x = +0.55;
  pitch 0.5, pin 1 top left. Corner radius 0.05.
- L_Sunlord_WPN201610H: Sunlord WPN series spec (rev. 2018/12/13), recommended land pattern a = 0.7 (gap), b = 0.7, c = 1.7.
  Body 2.0 x 1.6 x 1.0 max.
- L_TDK_VLS252010: TDK VLS252010HBX-1 catalogue (20160411) page 5: land 0.6 / 1.3 / 0.6 x 2.0. Body 2.5 x 2.0 x 1.0 max.
- CMF4532F_4P: EMTEK spec T-0602-102D section 7-1 (4.8 / 2.5 / 3.8 / 0.7 mm; 0.7 = gap between the pad rows). Body 4.5 x 3.2.
- BMP585_LGA-8_3.25x3.25mm: Bosch BST-BMP585-DS003-02 rev 1.2 figure 29 (bottom view) and section 9.3.3: lands = package
  pads + 25 um per side (0.55 x 0.8 -> 0.6 x 0.85), side pads at x +/-1.225, y 0 / +/-1.1, middle pads at y +/-1.225;
  pin 9 (laser-mark pad) gets no land. No solder mask under the sensor (9.3.3): one mask opening over the body
  + 20 um, so the footprint allows mask bridges. No traces or vias under it: rule area in the board generator.
- Bosch_LGA-10_2x2mm (BMP580): Bosch BST-BMP581-DS004-13 section 8.1.2 figure 30 (bottom view) and 8.2 figure 32
  (landing pattern), same package as the BMP580 (no public BMP580 datasheet; BMP5xy handling guide BST-BMP5xy-HS000-00
  section 3.2 gives the same land rule for the BMP580). Package pads 0.25 x 0.275 at a 0.5 mm pitch, row centres
  1.525 mm apart, 1.0 mm between the outer pads of a row; lands = pads + 25 um per side (0.30 x 0.325), gap >= 0.2 mm.
  Top view = bottom view mirrored: pin 1 top left, counter-clockwise. No solder mask under the body (mask opening = body
  + 20 um per side), no traces or vias under it (rule area in the board generator). The LCSC/EasyEDA footprint of
  C22391138 has the same pad numbers at +/-0.78 / +/-0.25 / +/-0.5 (0.0175 mm off): fitted by fab_package.fit.
- Vishay_VEML6030_2x2mm: Vishay 84366 rev 1.8 page 10 "Recommended Footprint": 6 pads 0.55 x 0.3, outer span 2.3 x 1.6
  (centres x +/-0.875, y 0 / +/-0.65). Top-view pinning: 1 GND bottom right, counter-clockwise to 6 VDD bottom left.
- LED_LiteOn_LTST-S270_SideView: Lite-On LTST-S270KRKT data sheet DS22-2000-210 rev G (2012-04-21). Page 1 package
  dimensions: body 1.65 long, 0.68 deep plus a 0.47 lens (1.15 total), 0.60 high (tape pocket 0.75 deep, page 7);
  terminals 0.33 at both ends. Page 7 "Suggest Soldering Pad Dimensions": two 1.10 x 1.10 pads, 0.90 gap (centres
  +/-1.0). Emission and polarity: page 1 (lens in the top view, cathode mark at the lower end, polarity symbol) and the
  page 7 tape drawing (lens toward the feed direction, "CATHODE" at the upper terminal) agree: lens up (-y) puts the
  cathode left (-x). Footprint: origin between the pads, pad 1 = cathode at -x, pad 2 = anode at +x, lens toward -y
  (place the -y side at the board edge); pads centred on the 0.68 body (terminal y +/-0.34 inside the 1.10 land, ends
  0.495-0.825 inside 0.45-1.55). The LCSC/EasyEDA footprint of C125114 has pad 1 (marked "-") at -0.9, pad 2 ("+") at
  +0.9 (0.8 x 0.7 pads) and draws the lens at -y: same pinning and orientation, centres 0.1 mm apart (fab_package fit).
"""

from pathlib import Path

OUT = Path(__file__).resolve().parent / "lib" / "weatherstation.pretty"
CY = 0.25  # courtyard clearance


def pad(num, x, y, w, h, shape="roundrect", rr=0.2):
    extra = f" (roundrect_rratio {rr})" if shape == "roundrect" else ""
    return (f'  (pad "{num}" smd {shape} (at {x:g} {y:g}) (size {w:g} {h:g}) '
            f'(layers "F.Cu" "F.Mask" "F.Paste"){extra})')


def footprint(name, descr, tags, pads, body, silk=(), pin1=None):
    """pads: (num, x, y, w, h[, shape, rr]); body: (half_w, half_h) of the package."""
    bx, by = body
    px = max(abs(p[1]) + p[3] / 2 for p in pads)
    py = max(abs(p[2]) + p[4] / 2 for p in pads)
    cx, cy = round(max(px, bx) + CY, 2), round(max(py, by) + CY, 2)
    lines = [f'(footprint "{name}"', '  (version 20240108)', '  (generator "weatherstation_build_footprints")',
             '  (layer "F.Cu")', f'  (descr "{descr}")', f'  (tags "{tags}")', '  (attr smd)',
             f'  (fp_text reference "REF**" (at 0 {-cy - 0.8:g} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
             f'  (fp_text value "{name}" (at 0 {cy + 0.8:g} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
             f'  (fp_text user "${{REFERENCE}}" (at 0 0 0) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))',
             f'  (fp_rect (start {-bx:g} {-by:g}) (end {bx:g} {by:g}) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
             f'  (fp_rect (start {-cx:g} {-cy:g}) (end {cx:g} {cy:g}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))']
    for (x1, y1), (x2, y2) in silk:
        lines.append(f'  (fp_line (start {x1:g} {y1:g}) (end {x2:g} {y2:g}) (stroke (width 0.12) (type default)) (layer "F.SilkS"))')
    if pin1:
        lines.append(f'  (fp_circle (center {pin1[0]:g} {pin1[1]:g}) (end {pin1[0] + 0.1:g} {pin1[1]:g}) '
                     '(stroke (width 0.2) (type default)) (fill solid) (layer "F.SilkS"))')
    lines += [pad(*p) for p in pads]
    lines.append(")")
    return "\n".join(lines) + "\n"


def dla():
    pads = [(str(i + 1), -0.9, -1.0 + 0.5 * i, 0.6, 0.25, "roundrect", 0.2) for i in range(5)]
    for num, y in (("10", -1.0), ("9", -0.5), ("7", 0.5), ("6", 1.0)):
        pads.append((num, 0.75, y, 0.9, 0.25, "roundrect", 0.2))
    pads.append(("8", 0.55, 0.0, 1.3, 0.25, "roundrect", 0.2))
    silk = [((-1.1, -1.6), (1.1, -1.6)), ((-1.1, 1.6), (1.1, 1.6))]
    return footprint("TPS63802_DLA_VSON-HR-10_2x3mm",
                     "TI DLA0010A VSON-HR 10 pin 2x3 mm, land pattern from TI example board layout 4223750/D (TPS63802 SLVSEU9)",
                     "TPS63802 DLA VSON-HR", pads, (1.0, 1.5), silk, pin1=(-1.55, -1.0))


def two_pad(name, descr, tags, centre, w, h, body):
    bx, by = body
    pads = [("1", -centre, 0, w, h, "roundrect", 0.15), ("2", centre, 0, w, h, "roundrect", 0.15)]
    gap = centre - w / 2 - 0.2  # silk only between the pads, top and bottom edge of the body
    silk = [((-gap, -by - 0.1), (gap, -by - 0.1)), ((-gap, by + 0.1), (gap, by + 0.1))] if gap > 0.1 else []
    return footprint(name, descr, tags, pads, body, silk)


def cmf():
    # 7-1: 4.8 outer and 2.5 inner span along the length -> pads 1.15 wide at x +/-1.825; 3.8 outer span and 0.7 gap
    # between the rows across the width -> pads 1.55 high at y +/-1.125 (fixed 2026-11-05: 0.7 had been read as the pad
    # height). Check: terminals D1 1.0 x D2 1.2 at the body corners (centres x +/-1.75, y +/-1.0) sit inside the lands;
    # the LCSC/EasyEDA footprint of C963746 is the same pattern turned 90 deg (1.5 mm pads at +/-1.75, +/-1.15).
    pads = [("1", -1.825, -1.125, 1.15, 1.55, "rect"), ("2", 1.825, -1.125, 1.15, 1.55, "rect"),
            ("3", 1.825, 1.125, 1.15, 1.55, "rect"), ("4", -1.825, 1.125, 1.15, 1.55, "rect")]
    silk = [((-1.0, -1.7), (1.0, -1.7)), ((-1.0, 1.7), (1.0, 1.7))]
    return footprint("CMF4532F_4P",
                     "EMTEK CMF4532F 2-line common-mode filter, 4.5x3.2 mm, land pattern from spec T-0602-102D section 7-1 (4.8 / 2.5 / 3.8 / 0.7 mm)",
                     "CMF4532F common mode choke", pads, (2.25, 1.6), silk, pin1=(-2.7, -1.125))


def bmp585():
    side = [("1", -1.225, -1.1), ("2", -1.225, 0.0), ("3", -1.225, 1.1), ("5", 1.225, 1.1), ("6", 1.225, 0.0), ("7", 1.225, -1.1)]
    pads = [(n, x, y, 0.6, 0.85, "roundrect", 0.15) for n, x, y in side]
    pads += [("4", 0.0, 1.225, 0.85, 0.6, "roundrect", 0.15), ("8", 0.0, -1.225, 0.85, 0.6, "roundrect", 0.15)]
    silk = [((-1.0, -1.8), (1.0, -1.8)), ((-1.0, 1.8), (1.0, 1.8))]
    text = footprint("BMP585_LGA-8_3.25x3.25mm",
                     "Bosch BMP585 LGA 3.25x3.25 mm, lands = pads + 25 um (BST-BMP585-DS003-02 rev 1.2 fig. 29, sec. 9.3.3); "
                     "no solder mask under the body; keep traces and vias out from under the sensor",
                     "BMP585 pressure LGA", pads, (1.625, 1.625), silk, pin1=(-2.0, -1.1))
    mask = ('  (fp_rect (start -1.645 -1.645) (end 1.645 1.645) (stroke (width 0) (type default)) (fill solid) (layer "F.Mask"))')
    return text.replace("  (attr smd)", "  (attr smd allow_soldermask_bridges)").replace("\n  (pad ", "\n" + mask + "\n  (pad ", 1)


def bmp580():
    c, r = 0.7625, 0.25  # row centre (1.525 / 2) and side-pad offset (0.5 / 2)
    side = [("1", -c, -r), ("2", -c, r), ("6", c, r), ("7", c, -r)]
    rows = [("3", -0.5, c), ("4", 0.0, c), ("5", 0.5, c), ("8", 0.5, -c), ("9", 0.0, -c), ("10", -0.5, -c)]
    pads = [(n, x, y, 0.325, 0.30, "roundrect", 0.15) for n, x, y in side]
    pads += [(n, x, y, 0.30, 0.325, "roundrect", 0.15) for n, x, y in rows]
    silk = [((-0.6, -1.15), (0.6, -1.15)), ((-0.6, 1.15), (0.6, 1.15))]
    text = footprint("Bosch_LGA-10_2x2mm",
                     "Bosch BMP580/BMP581 LGA-10 2.0x2.0 mm, lands = pads + 25 um (BST-BMP581-DS004-13 sec. 8.1.2 fig. 30, "
                     "sec. 8.2 fig. 32; BST-BMP5xy-HS000-00 sec. 3.2); no solder mask under the body (8.2); no traces or vias under it",
                     "BMP580 BMP581 pressure LGA", pads, (1.0, 1.0), silk, pin1=(-1.3, -0.9))
    mask = ('  (fp_rect (start -1.02 -1.02) (end 1.02 1.02) (stroke (width 0) (type default)) (fill solid) (layer "F.Mask"))')
    return text.replace("  (attr smd)", "  (attr smd allow_soldermask_bridges)").replace("\n  (pad ", "\n" + mask + "\n  (pad ", 1)


def veml6030():
    pos = [("1", 0.875, 0.65), ("2", 0.875, 0.0), ("3", 0.875, -0.65), ("4", -0.875, -0.65), ("5", -0.875, 0.0), ("6", -0.875, 0.65)]
    pads = [(n, x, y, 0.55, 0.3, "roundrect", 0.15) for n, x, y in pos]
    silk = [((-0.9, -1.15), (0.9, -1.15)), ((-0.9, 1.15), (0.9, 1.15))]
    return footprint("Vishay_VEML6030_2x2mm",
                     "Vishay VEML6030 2x2 mm, recommended footprint (doc. 84366 rev 1.8 page 10): 0.55 x 0.3 pads, span 2.3 x 1.6",
                     "VEML6030 ambient light", pads, (1.0, 1.0), silk, pin1=(1.45, 1.05))


def ltst_s270():
    """Side-view LED, asymmetric outline (lens beyond the body on the -y side), so not through footprint()."""
    name = "LED_LiteOn_LTST-S270_SideView"
    pads = [("1", -1.0, 0.0, 1.1, 1.1, "roundrect", 0.1), ("2", 1.0, 0.0, 1.1, 1.1, "roundrect", 0.1)]
    # courtyard: pads + 0.25 (x), lens tip + 0.25 (-y), pads + 0.15 on the inboard side (+y), so the part can stand at
    # the board edge beside a connector courtyard (main board J2); IPC-7351 courtyard excess for small chips 0.10-0.25
    cx, y_top, y_bot = 1.55 + CY, -0.81 - CY, 0.55 + 0.15
    descr = ("Lite-On LTST-S270 side-view LED 1.65x1.15x0.6 mm, lens toward -y, pad 1 cathode; land 1.10 x 1.10, gap 0.90 "
             "(DS22-2000-210 rev G pages 1 and 7)")
    lines = [f'(footprint "{name}"', '  (version 20240108)', '  (generator "weatherstation_build_footprints")',
             '  (layer "F.Cu")', f'  (descr "{descr}")', '  (tags "LED side view right angle LiteOn LTST-S270")', '  (attr smd)',
             f'  (fp_text reference "REF**" (at 0 {y_bot + 0.9:g} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
             f'  (fp_text value "{name}" (at 0 {y_bot + 2.0:g} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
             '  (fp_text user "${REFERENCE}" (at 0 0 0) (layer "F.Fab") (effects (font (size 0.4 0.4) (thickness 0.06))))',
             '  (fp_rect (start -0.825 -0.34) (end 0.825 0.34) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
             '  (fp_rect (start -0.6 -0.81) (end 0.6 -0.34) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
             '  (fp_line (start -0.825 0.34) (end -0.5 0.0) (stroke (width 0.1) (type default)) (layer "F.Fab"))',
             f'  (fp_rect (start {-cx:g} {y_top:g}) (end {cx:g} {y_bot:g}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))',
             # silk on the inboard side only (the lens side sits at the board edge): one line behind the cathode half
             # (pad 1 to the centre), 0.19 mm from the pad; it stays 0.25 mm from a neighbour's silk 0.8 mm further in
             # (main board: J2's outline), where a dot behind pad 1 would not fit
             '  (fp_line (start -1.6 0.8) (end 0 0.8) (stroke (width 0.12) (type default)) (layer "F.SilkS"))']
    lines += [pad(*p) for p in pads]
    lines.append(")")
    return "\n".join(lines) + "\n"


FOOTPRINTS = {
    "TPS63802_DLA_VSON-HR-10_2x3mm": dla(),
    # Sunlord WPN201610H: pads b = 0.7 wide, c = 1.7 tall, gap a = 0.7 -> centres at +/-(0.35 + 0.35)
    "L_Sunlord_WPN201610H": two_pad("L_Sunlord_WPN201610H",
                                    "Sunlord WPN201610H 2.0x1.6 mm power inductor, recommended land pattern a 0.7 / b 0.7 / c 1.7 (WPN series spec 2018/12/13)",
                                    "inductor Sunlord WPN201610", 0.7, 0.7, 1.7, (1.0, 0.8)),
    # TDK VLS252010: 0.6 / 1.3 / 0.6 by 2.0 -> centres at +/-(0.65 + 0.3)
    "L_TDK_VLS252010": two_pad("L_TDK_VLS252010",
                               "TDK VLS252010HBX-1 2.5x2.0 mm power inductor, land pattern 0.6 / 1.3 / 0.6 x 2.0 (TDK catalogue 20160411 page 5)",
                               "inductor TDK VLS252010", 0.95, 0.6, 2.0, (1.25, 1.0)),
    "CMF4532F_4P": cmf(),
    "BMP585_LGA-8_3.25x3.25mm": bmp585(),
    "Bosch_LGA-10_2x2mm": bmp580(),
    "Vishay_VEML6030_2x2mm": veml6030(),
    "LED_LiteOn_LTST-S270_SideView": ltst_s270(),
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in FOOTPRINTS.items():
        (OUT / f"{name}.kicad_mod").write_text(text)
        print("wrote", OUT / f"{name}.kicad_mod")
