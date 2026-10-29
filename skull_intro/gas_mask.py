"""Máscara de gas militar clásica, alineada con la calavera.

Pieza facial de goma con dos visores redondos con aro metálico, arnés de correas,
válvulas laterales y un filtro cilíndrico que cuelga de la barbilla visto en
perspectiva (se ven su cuerpo acanalado y su cara inferior perforada).
"""

import math

from .drawing import (
    BASE_W, circle, clip_to, cylinder, ellipse, ellipse_points, finish, lerp, lines, new_layer,
    poly, sc_rect, shape_fill, silhouette, smooth_closed, soft_line, soft_spot, speckle,
    symmetric,
)

import pygame

RUBBER = (40, 42, 37)
RUBBER_HI = (92, 96, 84, 170)
RUBBER_DARK = (18, 19, 16)
METAL = (138, 140, 130)
METAL_HI = (228, 228, 218)
METAL_DARK = (58, 60, 54)
OLIVE = (96, 104, 70)
OLIVE_DARK = (34, 38, 26)
OLIVE_HI = (188, 196, 150)
STRAP = (66, 60, 48)
STITCH = (124, 114, 94)

MASK_OUTLINE = smooth_closed(symmetric([
    (400, 280), (520, 274), (630, 298), (690, 370), (702, 470), (686, 580), (638, 690),
    (572, 790), (488, 868), (400, 888),
]))

LENSES = [(255, 405), (545, 405)]
LENS_R = 92

SNOUT = dict(top=(400, 548), bottom=(400, 760), rx_top=66, ry_top=20, rx_bot=128, ry_bot=36)
NECK = dict(top=(400, 752), bottom=(400, 806), rx_top=78, ry_top=22, rx_bot=82, ry_bot=24)
CANISTER = dict(top=(400, 800), bottom=(400, 1010), rx_top=112, ry_top=32, rx_bot=128, ry_bot=40)


def draw_strap(surf, start, end, width):
    lines(surf, STRAP, [start, end], width)
    # costuras a ambos lados de la correa
    length = math.dist(start, end)
    nx, ny = -(end[1] - start[1]) / length, (end[0] - start[0]) / length
    for off in (-width * 0.32, width * 0.32):
        steps = int(length // 14)
        for i in range(0, steps, 2):
            a = (lerp(start[0], end[0], i / steps) + nx * off, lerp(start[1], end[1], i / steps) + ny * off)
            b = (lerp(start[0], end[0], (i + 1) / steps) + nx * off, lerp(start[1], end[1], (i + 1) / steps) + ny * off)
            lines(surf, STITCH, [a, b], 1.6)


def draw_buckle(surf, center, w, h):
    rect = sc_rect(center[0] - w / 2, center[1] - h / 2, w, h)
    pygame.draw.rect(surf, METAL, rect, border_radius=rect.h // 5)
    pygame.draw.rect(surf, METAL_DARK, rect.inflate(-rect.w // 3, -rect.h // 3), border_radius=rect.h // 8)
    pygame.draw.rect(surf, METAL_HI, rect, 2, border_radius=rect.h // 5)


def draw_harness(skull_shape):
    straps = new_layer()
    draw_strap(straps, (400, 296), (400, 140), 52)
    for side in (lambda p: p, lambda p: (BASE_W - p[0], p[1])):
        draw_strap(straps, side((400, 150)), side((650, 10)), 44)
        draw_strap(straps, side((660, 330)), side((790, 250)), 46)
        draw_strap(straps, side((668, 600)), side((790, 560)), 46)
        draw_buckle(straps, side((700, 312)), 34, 46)
        draw_buckle(straps, side((708, 590)), 34, 46)
    draw_buckle(straps, (400, 160), 58, 38)
    return clip_to(straps, skull_shape)


def draw_lens(surf, center):
    cx, cy = center
    circle(surf, RUBBER_DARK, center, LENS_R + 26)                 # reborde de goma moldeado
    surf.blit(soft_line(ellipse_points(cx, cy, LENS_R + 20, LENS_R + 20, math.pi * 0.95, math.pi * 1.6),
                        (110, 114, 100, 200), 8, closed=False), (0, 0))
    circle(surf, METAL_DARK, center, LENS_R + 12)                  # aro metálico
    circle(surf, METAL, center, LENS_R + 8)
    lines(surf, METAL_HI, ellipse_points(cx, cy, LENS_R + 6, LENS_R + 6, math.pi * 0.95, math.pi * 1.55), 4)
    lines(surf, METAL_DARK, ellipse_points(cx, cy, LENS_R + 6, LENS_R + 6, math.pi * 0.05, math.pi * 0.55), 4)
    circle(surf, METAL_DARK, center, LENS_R - 2)
    # cristal ahumado semitransparente: deja intuir las cuencas de la calavera
    glass = new_layer()
    circle(glass, (255, 255, 255, 255), center, LENS_R - 6)
    tint = shape_fill(glass, (34, 54, 46, 168))
    tint.blit(clip_to(soft_spot((150, 190, 170, 90), (cx - 30, cy - 34), 50, 38), glass), (0, 0))
    surf.blit(glass, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)  # vacía el hueco del cristal
    surf.blit(tint, (0, 0))
    lines(surf, (255, 255, 255, 170), ellipse_points(cx - 4, cy - 4, LENS_R - 22, LENS_R - 22,
                                                     math.pi * 1.05, math.pi * 1.42), 6)
    lines(surf, (255, 255, 255, 110), ellipse_points(cx + 4, cy + 4, LENS_R - 20, LENS_R - 20,
                                                     math.pi * 0.15, math.pi * 0.3), 4)
    for k in range(8):                                                # tornillos del aro
        a = 2 * math.pi * k / 8 + math.pi / 8
        pos = (cx + (LENS_R + 4) * math.cos(a), cy + (LENS_R + 4) * math.sin(a))
        circle(surf, METAL_HI, pos, 5)
        lines(surf, METAL_DARK, [(pos[0] - 3, pos[1]), (pos[0] + 3, pos[1])], 1.5)


def draw_valve(surf, center, side):
    """Válvula de exhalación en la mejilla, girada hacia el lateral."""
    cx, cy = center
    ellipse(surf, RUBBER_DARK, center, 30, 38)
    ellipse(surf, METAL_DARK, (cx + side * 4, cy), 22, 30)
    for k in range(-2, 3):
        lines(surf, METAL, [(cx + side * 4 - 16, cy + k * 10), (cx + side * 4 + 16, cy + k * 10)], 3)
    ellipse(surf, METAL, (cx + side * 4, cy), 22, 30, 3)


def draw_canister_face(surf):
    cx, cy = CANISTER["bottom"]
    rx, ry = CANISTER["rx_bot"], CANISTER["ry_bot"]
    ellipse(surf, OLIVE_DARK, (cx, cy), rx, ry)
    ellipse(surf, (74, 80, 54), (cx, cy - 2), rx - 8, ry - 3)
    lines(surf, OLIVE_HI, ellipse_points(cx, cy, rx - 3, ry - 1, math.pi * 0.55, math.pi * 0.95), 3)
    ellipse(surf, (46, 50, 34), (cx, cy - 2), rx * 0.74, ry * 0.74)
    for ring, count in ((0.24, 8), (0.44, 14), (0.62, 20)):
        for k in range(count):
            a = 2 * math.pi * (k + 0.5 * (count % 2)) / count
            ellipse(surf, (10, 10, 8), (cx + ring * rx * math.cos(a), cy - 2 + ring * ry * math.sin(a)), 5, 2.5)
    ellipse(surf, METAL, (cx, cy - 2), 14, 5)
    ellipse(surf, METAL_HI, (cx - 3, cy - 3), 6, 2)


def draw_gas_mask(skull_shape):
    surf = new_layer()
    surf.blit(draw_harness(skull_shape), (0, 0))

    # pieza facial de goma: volumen, grano y borde enrollado
    face = silhouette(MASK_OUTLINE)
    layer = shape_fill(face, RUBBER)
    layer.blit(clip_to(soft_line(MASK_OUTLINE, (6, 6, 5, 220), 70), face), (0, 0))
    layer.blit(clip_to(soft_spot(RUBBER_HI, (300, 330), 170, 120), face), (0, 0))
    layer.blit(clip_to(soft_spot((80, 84, 74, 120), (560, 640), 90, 120), face), (0, 0))
    layer.blit(speckle(face, 21, 9000, [(0, 0, 0, 50), (120, 124, 110, 40)], (90, 270, 710, 900), (0.8, 1.8)),
               (0, 0))
    surf.blit(layer, (0, 0))
    lines(surf, RUBBER_DARK, MASK_OUTLINE, 9, closed=True)
    # brillo del borde enrollado a lo largo de la frente (el contorno empieza arriba en el centro)
    brow = len(MASK_OUTLINE) // 5
    surf.blit(soft_line(MASK_OUTLINE[-brow:] + MASK_OUTLINE[:brow], (120, 124, 108, 160), 8, closed=False),
              (0, 0))

    # pliegue central entre los visores
    surf.blit(soft_line([(400, 300), (396, 400), (400, 520)], (100, 104, 90, 180), 14, closed=False), (0, 0))
    lines(surf, RUBBER_DARK, [(404, 300), (402, 400), (406, 520)], 3)

    for center in LENSES:
        draw_lens(surf, center)
    for center, side in (((610, 600), 1), ((190, 600), -1)):
        draw_valve(surf, center, side)

    # morro del respirador (cono de goma acanalado)
    shadow = soft_spot((0, 0, 0, 170), (410, 700), 150, 90)
    surf.blit(clip_to(shadow, face), (0, 0))
    cylinder(surf, **SNOUT, dark=RUBBER_DARK, base=(64, 67, 58), light=(150, 154, 138),
             ribs=(0.22, 0.42, 0.62, 0.8), rib_dark=RUBBER_DARK, rib_light=(110, 114, 100, 200),
             outline=RUBBER_DARK)

    # filtro: cuerpo cilíndrico acanalado en perspectiva y cara inferior perforada
    surf.blit(soft_spot((0, 0, 0, 150), (420, 920), 150, 120), (0, 0))
    cylinder(surf, **CANISTER, dark=OLIVE_DARK, base=OLIVE, light=OLIVE_HI,
             ribs=(0.12, 0.2, 0.55, 0.85), rib_dark=OLIVE_DARK, rib_light=(170, 178, 132, 220),
             outline=OLIVE_DARK)
    draw_canister_face(surf)
    # rosca metálica que une el filtro con el morro
    cylinder(surf, **NECK, dark=METAL_DARK, base=METAL, light=METAL_HI,
             ribs=(0.25, 0.5, 0.75), rib_dark=METAL_DARK, rib_light=(240, 240, 230, 200), outline=METAL_DARK)

    return finish(surf)
