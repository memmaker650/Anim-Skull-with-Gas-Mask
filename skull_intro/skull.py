"""Calavera humana en vista frontal, construida hueso a hueso.

Cada hueso (cráneo, mandíbula, maxilar, cigomáticos, nasales) es una pieza con su
propio volumen y contorno para que se distinga la estructura ósea; encima van
cuencas, cavidad nasal, dientes, suturas, forámenes y textura.
"""

from .drawing import (
    alpha_shape, both_sides, circle, clip_to, ellipse, finish, lerp, lerp_color, lines,
    mirror, new_layer, poly, shaded_part, shape_fill, silhouette, smooth_closed, soft_fill, soft_line,
    soft_spot, speckle, symmetric, zigzag,
)

BONE = (222, 211, 186)
BONE_HI = (250, 245, 230, 210)
BONE_RIM = (118, 100, 74, 175)
OUTLINE = (82, 66, 48)
SUTURE = (98, 80, 58)
CAVITY = (13, 10, 8)
DROP = (25, 18, 10, 150)
ENAMEL = (238, 230, 206)
ENAMEL_BACK = (182, 168, 138)

CRANIUM = smooth_closed(symmetric([
    (400, 38), (540, 56), (642, 122), (702, 222), (724, 338), (716, 440), (698, 520),
    (690, 600), (668, 652), (620, 650), (400, 610),
]))

MANDIBLE = smooth_closed(symmetric([
    (400, 786), (498, 782), (552, 766), (584, 728), (598, 650), (606, 566), (648, 560),
    (652, 680), (640, 790), (614, 858), (568, 902), (496, 934), (400, 948),
]), 8)

MAXILLA = smooth_closed(symmetric([
    (400, 468), (452, 476), (560, 490), (594, 584), (580, 640), (556, 690), (488, 708),
    (400, 712),
]))

ZYGOMATIC = smooth_closed([
    (590, 462), (640, 430), (662, 445), (668, 488), (704, 502), (716, 528), (690, 548),
    (650, 556), (622, 586), (590, 600), (566, 566), (560, 508),
])

NASAL_BONES = smooth_closed(symmetric([
    (400, 432), (418, 436), (436, 488), (440, 520), (400, 514),
]), 6)

NASAL_APERTURE = smooth_closed(symmetric([
    (400, 508), (430, 516), (456, 560), (466, 604), (448, 636), (418, 650), (400, 652),
]), 8)

ORBIT = smooth_closed([
    (448, 336), (518, 314), (592, 320), (636, 356), (646, 418), (628, 470), (572, 496),
    (504, 494), (462, 466), (444, 404),
])

# (ancho, alto, tipo) desde la línea media hacia el fondo de la boca
UPPER_TEETH = [(32, 58, "incisor"), (26, 52, "incisor"), (25, 62, "canine"),
               (22, 48, "premolar"), (21, 46, "premolar"), (21, 40, "molar"), (18, 36, "molar")]
LOWER_TEETH = [(23, 44, "incisor"), (23, 44, "incisor"), (24, 52, "canine"),
               (22, 44, "premolar"), (21, 42, "premolar"), (21, 36, "molar"), (18, 32, "molar")]


def bite_line(i):
    """Altura del plano de oclusión: sube ligeramente hacia los molares."""
    return 750 - 0.6 * i * i


def teeth_layout(specs):
    x = 0
    for i, (w, h, kind) in enumerate(specs):
        for side in (1, -1):
            yield i, 400 + side * (x + w / 2) * 0.92, w, h, kind
        x += w


def tooth_points(cx, root, edge, w, kind):
    d = 1 if edge > root else -1  # dirección raíz -> borde
    hw = w / 2
    mid = lerp(root, edge, 0.45)
    pts = [(cx - hw * 0.78, root), (cx + hw * 0.78, root), (cx + hw, mid), (cx + hw * 0.92, edge - d * 6)]
    if kind == "canine":
        pts += [(cx + hw * 0.35, edge - d * 1), (cx, edge + d * 4), (cx - hw * 0.35, edge - d * 1)]
    elif kind == "molar":
        pts += [(cx + hw * 0.3, edge), (cx, edge - d * 3), (cx - hw * 0.3, edge)]
    else:
        pts += [(cx + hw * 0.4, edge), (cx - hw * 0.4, edge)]
    pts += [(cx - hw * 0.92, edge - d * 6), (cx - hw, mid)]
    return smooth_closed(pts, 3)


def draw_teeth(surf, specs, upper):
    for i, cx, w, h, kind in sorted(teeth_layout(specs), key=lambda t: -t[0]):
        bite = bite_line(i)
        edge, root = (bite, bite - h) if upper else (bite + 2, bite + 2 + h)
        pts = tooth_points(cx, root, edge, w, kind)
        enamel = lerp_color(ENAMEL, ENAMEL_BACK, i / 7)
        poly(surf, enamel, pts)
        # sombra hacia el lado alejado de la línea media y hacia la encía
        side = 1 if cx > 400 else -1
        lines(surf, lerp_color(enamel, (90, 75, 55), 0.45),
              [(cx + side * w * 0.36, lerp(root, edge, 0.15)), (cx + side * w * 0.36, lerp(root, edge, 0.85))], 3)
        lines(surf, (255, 252, 240), [(cx - side * w * 0.18, lerp(root, edge, 0.3)),
                                      (cx - side * w * 0.18, lerp(root, edge, 0.75))], 2)
        lines(surf, (96, 80, 58), pts, 1.6, closed=True)


def draw_orbit(surf, pts):
    shape = silhouette(pts)
    layer = shape_fill(shape, CAVITY)
    # paredes de la órbita iluminadas cerca del borde, fondo muy oscuro
    layer.blit(clip_to(soft_line(pts, (128, 110, 84, 235), 44), shape), (0, 0))
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    layer.blit(clip_to(soft_spot((0, 0, 0, 230), (cx + (8 if cx > 400 else -8), cy + 12), 52, 46), shape), (0, 0))
    surf.blit(layer, (0, 0))
    # fisura orbitaria superior
    side = 1 if cx > 400 else -1
    poly(surf, (4, 3, 2), smooth_closed([(cx - side * 6, cy - 4), (cx + side * 30, cy - 22),
                                         (cx + side * 38, cy - 16), (cx + side * 4, cy + 6)], 4))
    lines(surf, OUTLINE, pts, 2.5, closed=True)


def draw_skull():
    """Devuelve (superficie BASE_W x BASE_H, silueta a resolución de trabajo)."""
    surf = new_layer()

    # cráneo (frontal y parietales)
    cranium = shaded_part(surf, CRANIUM, BONE, BONE_HI, BONE_RIM, ((360, 200), 250, 200), OUTLINE,
                          rim_width=70)
    # fosas temporales y líneas temporales
    for side in (lambda p: p, mirror):
        surf.blit(clip_to(soft_fill(side([(640, 330), (712, 360), (716, 470), (690, 528), (640, 540),
                                          (630, 430)]), (95, 78, 55, 120), radius=10), cranium), (0, 0))
        surf.blit(soft_line(side([(612, 322), (634, 262), (646, 205), (648, 168)]), (245, 238, 220, 190),
                            10, closed=False), (0, 0))
        surf.blit(soft_line(side([(622, 330), (644, 266), (656, 208), (658, 170)]), (120, 100, 74, 150),
                            10, closed=False), (0, 0))
        # zona profunda tras la rama de la mandíbula
        surf.blit(clip_to(soft_fill(side([(600, 560), (700, 560), (690, 650), (600, 660)]), (40, 30, 20, 200),
                                    radius=8), cranium), (0, 0))
    # sutura coronal
    coronal = zigzag([(150, 230), (215, 140), (305, 92), (400, 80), (495, 92), (585, 140), (650, 230)],
                     4, 9, seed=3)
    lines(surf, (128, 108, 82), coronal, 1.8)
    lines(surf, (246, 240, 224), [(x + 1, y + 2) for x, y in coronal], 1)

    # mandíbula, con su cavidad bucal detrás de los dientes
    shaded_part(surf, MANDIBLE, BONE, BONE_HI, BONE_RIM, ((400, 900), 130, 60), OUTLINE, drop=DROP)
    for pts in both_sides([(590, 724), (598, 660), (604, 600)]):  # borde anterior de la rama
        lines(surf, (170, 150, 118), pts, 3)
    poly(surf, CAVITY, smooth_closed(symmetric([(400, 712), (530, 708), (566, 740), (536, 778), (400, 784)]), 6))
    # protuberancia mentoniana y agujeros mentonianos
    surf.blit(clip_to(soft_spot((252, 248, 236, 170), (400, 905), 70, 32), alpha_shape(surf)), (0, 0))
    for c in both_sides([(510, 862)]):
        ellipse(surf, CAVITY, c[0], 5, 4)
    draw_teeth(surf, LOWER_TEETH, upper=False)

    # maxilar con eminencias de las raíces dentales
    shaded_part(surf, MAXILLA, BONE, BONE_HI, BONE_RIM, ((400, 560), 140, 90), OUTLINE, drop=DROP,
                rim_width=36)
    for i, cx, w, h, kind in teeth_layout(UPPER_TEETH):
        if i < 5:
            top = bite_line(i) - h
            length = 46 if kind == "canine" else 28
            surf.blit(soft_line([(cx - 3, top - 2), (cx - 3, top - length)], (252, 247, 232, 150), 10,
                                closed=False), (0, 0))
            surf.blit(soft_line([(cx + w / 2, top - 2), (cx + w / 2, top - length + 6)], (130, 110, 82, 140),
                                8, closed=False), (0, 0))
    draw_teeth(surf, UPPER_TEETH, upper=True)
    for c in both_sides([(518, 524)]):  # agujeros infraorbitarios
        ellipse(surf, CAVITY, c[0], 6, 4)
    for c in both_sides([(492, 600)]):  # fosa canina
        surf.blit(soft_spot((110, 92, 66, 110), c[0], 38, 42), (0, 0))

    # pómulos (cigomáticos) con sus suturas
    for pts in both_sides(ZYGOMATIC):
        shaded_part(surf, pts, BONE, BONE_HI, BONE_RIM, ((pts[0][0] + (40 if pts[0][0] > 400 else -40), 500),
                                                        60, 40), OUTLINE, drop=DROP, rim_width=30)
    for c in both_sides([(600, 640)]):
        surf.blit(clip_to(soft_spot((60, 46, 30, 150), c[0], 50, 70), alpha_shape(surf)), (0, 0))
    for pts in both_sides(zigzag([(562, 506), (572, 548), (590, 598)], 4, 9, seed=5)):
        lines(surf, SUTURE, pts, 2)
    for pts in both_sides(zigzag([(640, 432), (656, 452)], 3, 6, seed=6)):
        lines(surf, SUTURE, pts, 2)

    # textura: poros y manchas de envejecimiento
    skull_shape = alpha_shape(surf)
    surf.blit(speckle(skull_shape, 11, 5000, [(120, 100, 72, 40), (255, 250, 236, 45), (90, 70, 50, 30)],
                      (80, 30, 720, 960)), (0, 0))
    for c, rx, ry in (((300, 160), 70, 40), ((560, 250), 50, 70), ((470, 880), 60, 30), ((230, 470), 30, 50)):
        surf.blit(clip_to(soft_spot((150, 118, 70, 45), c, rx, ry), skull_shape), (0, 0))

    # cuencas de los ojos y arcos superciliares
    for pts in both_sides([(436, 326), (520, 300), (608, 310), (658, 352)]):
        surf.blit(soft_line(pts, (252, 248, 236, 200), 18, closed=False), (0, 0))
    for pts in both_sides(ORBIT):
        draw_orbit(surf, pts)
    for c in both_sides([(492, 318)]):  # escotadura supraorbitaria
        ellipse(surf, CAVITY, c[0], 6, 4)

    # cavidad nasal: tabique, cornetes y espina nasal
    poly(surf, CAVITY, NASAL_APERTURE)
    for pts in both_sides(smooth_closed([(412, 590), (440, 584), (452, 610), (430, 628), (410, 622)], 4)):
        poly(surf, (44, 36, 28), pts)
    poly(surf, (92, 78, 60), [(398, 524), (402, 524), (405, 640), (395, 640)])
    poly(surf, BONE, [(388, 646), (412, 646), (400, 664)])
    lines(surf, OUTLINE, NASAL_APERTURE, 2.5, closed=True)

    # huesos nasales y sutura frontonasal
    shaded_part(surf, NASAL_BONES, BONE, BONE_HI, BONE_RIM, ((392, 470), 18, 34), OUTLINE, drop=DROP,
                rim_width=14)
    lines(surf, SUTURE, [(400, 434), (400, 512)], 1.6)
    lines(surf, SUTURE, zigzag([(380, 432), (420, 432)], 2, 5, seed=8), 1.8)

    return finish(surf), alpha_shape(surf)
