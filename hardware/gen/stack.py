"""Stack geometry shared by both split boards (plain Python: read by gen/power_pcb.py, gen/main_pcb.py and
tools/stack_check.py, which runs in the gate without KiCad).

Stack (power-board/BOARD.md and main-board/BOARD.md "Layout"): main board on top, power board below, both 50 x 50 mm,
outlines on top of each other (OFFSET = (0, 0) in top view), parts of both boards on their top side. J10 joins them:
2x10 2.54 mm male header on the main board (body on its underside, pins down, pin 3 pulled) into the 2x10 socket on
the power board (hole 3 blocked). Both footprints identical, unmirrored on F.Cu, at the same top-view position, so pin 1
is at the same corner. Board gap = socket body height + male header plastic (8.5 + 2.5 mm for the common parts; check
the bought parts) = M3 standoff length between the boards.
"""

W = H = 50.0                      # REQUIREMENTS-system.md section 7: each board at most 50 x 50 mm
OFFSET = (0.0, 0.0)               # power-board origin in main-board coordinates (top view)
GAP_MM = 11.0                     # board gap: 8.5 mm socket + 2.5 mm male header plastic (typical, unverified for the bought parts)
# M3 holes, the same on both boards: not symmetric about either axis and not 180-degree symmetric (ARCHITECTURE.md J10
# keying and mounting). H2 sits below the ESP32 module (top-right corner is the module and its antenna); its mirror
# images (mirror left-right: (3.5, 24.0); top-bottom: (46.5, 26.0) and (46.5, 3.5)) leave at least one hole without a partner, so a
# flipped or rotated board cannot be screwed on.
HOLES = {"H1": (3.5, 3.5), "H2": (46.5, 24.0), "H3": (3.5, 46.5), "H4": (46.5, 46.5)}
# J10 pin 1 position and rotation (270: pin 1 = SYS at the right end, odd pins on the upper row, columns run to -x,
# pin 19/20 = USB_VBUS at x - 22.86)
J10_AT = (42.0, 33.5, 270)
