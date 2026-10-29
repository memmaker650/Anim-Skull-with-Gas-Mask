"""Utilidades de dibujo compartidas por la calavera y la máscara.

Todo se dibuja en un espacio de coordenadas fijo (BASE_W x BASE_H) con
supersampling (SS) y al final se reduce para obtener bordes suaves.
"""

import math
import random

import pygame

BASE_W, BASE_H = 800, 1100
SS = 2


# ---------------------------------------------------------------- matemáticas

def clamp01(x):
    return max(0.0, min(1.0, x))


def lerp(a, b, x):
    return a + (b - a) * x


def lerp_color(a, b, x):
    return tuple(round(lerp(a[i], b[i], x)) for i in range(len(a)))


def smoothstep(x):
    return x * x * (3 - 2 * x)


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_in_cubic(x):
    return x ** 3


def smooth_closed(points, steps=10):
    """Curva Catmull-Rom cerrada que pasa por los puntos de control."""
    out = []
    n = len(points)
    for i in range(n):
        p0, p1, p2, p3 = points[i - 1], points[i], points[(i + 1) % n], points[(i + 2) % n]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t
                       + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                       + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3)
                for k in (0, 1)))
    return out


def symmetric(right_half):
    """Completa una silueta simétrica a partir de su mitad derecha (de arriba a abajo)."""
    return right_half + [(BASE_W - x, y) for x, y in reversed(right_half[1:-1])]


def mirror(points):
    return [(BASE_W - x, y) for x, y in points]


def both_sides(points):
    return (points, mirror(points))


def zigzag(points, amp, step, seed):
    """Línea dentada (suturas craneales) a lo largo de una polilínea."""
    rng = random.Random(seed)
    out = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        length = math.dist((x0, y0), (x1, y1))
        nx, ny = -(y1 - y0) / length, (x1 - x0) / length
        n = max(1, int(length / step))
        for i in range(n):
            t = i / n
            off = amp * rng.uniform(-1, 1) * (1 if i % 2 else -1)
            out.append((lerp(x0, x1, t) + nx * off, lerp(y0, y1, t) + ny * off))
    out.append(points[-1])
    return out


def ellipse_points(cx, cy, rx, ry, a0, a1, n=40):
    """Puntos de un arco de elipse; los ángulos van en sentido de pantalla (y hacia abajo)."""
    return [(cx + rx * math.cos(lerp(a0, a1, i / n)), cy + ry * math.sin(lerp(a0, a1, i / n)))
            for i in range(n + 1)]


# ---------------------------------------------------------------- primitivas en espacio base

def sc(points):
    return [(x * SS, y * SS) for x, y in points]


def r(v):
    return max(1, round(v * SS))


def sc_rect(x, y, w, h):
    return pygame.Rect(round(x * SS), round(y * SS), round(w * SS), round(h * SS))


def new_layer():
    return pygame.Surface((BASE_W * SS, BASE_H * SS), pygame.SRCALPHA)


def poly(surf, color, points):
    pygame.draw.polygon(surf, color, sc(points))


def lines(surf, color, points, width, closed=False):
    pygame.draw.lines(surf, color, closed, sc(points), r(width))


def circle(surf, color, center, radius, width=0):
    pygame.draw.circle(surf, color, (round(center[0] * SS), round(center[1] * SS)),
                       r(radius), r(width) if width else 0)


def ellipse(surf, color, center, rx, ry, width=0):
    pygame.draw.ellipse(surf, color, sc_rect(center[0] - rx, center[1] - ry, rx * 2, ry * 2),
                        r(width) if width else 0)


# ---------------------------------------------------------------- capas y sombreado

def silhouette(points):
    layer = new_layer()
    poly(layer, (255, 255, 255, 255), points)
    return layer


def alpha_shape(surf):
    """Silueta blanca con el mismo alfa que `surf` (para recortar otras capas)."""
    shape = surf.copy()
    shape.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_MAX)
    return shape


def clip_to(layer, shape):
    """Recorta `layer` a la silueta `shape` multiplicando su alfa."""
    layer.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return layer


def shape_fill(shape, color):
    layer = shape.copy()
    layer.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
    return layer


def _soft(draw, color, blur, radius):
    """Dibuja a baja resolución con `draw`, desenfoca y escala a tamaño de trabajo."""
    small = pygame.Surface((BASE_W // blur, BASE_H // blur), pygame.SRCALPHA)
    small.fill((*color[:3], 0))  # mismo RGB que el trazo: sin halos oscuros al desenfocar
    draw(small, lambda pts: [(x / blur, y / blur) for x, y in pts])
    small = pygame.transform.gaussian_blur(small, radius)
    return pygame.transform.smoothscale(small, (BASE_W * SS, BASE_H * SS))


def soft_spot(color, center, rx, ry, blur=4, radius=8):
    """Mancha difusa (brillos, sombras, manchas)."""
    def draw(s, to):
        (x, y), = to([center])
        pygame.draw.ellipse(s, color, (x - rx / blur, y - ry / blur, 2 * rx / blur, 2 * ry / blur))
    return _soft(draw, color, blur, radius)


def soft_fill(points, color, offset=(0, 0), blur=4, radius=4):
    def draw(s, to):
        pygame.draw.polygon(s, color, to([(x + offset[0], y + offset[1]) for x, y in points]))
    return _soft(draw, color, blur, radius)


def soft_line(points, color, width, closed=True, blur=4, radius=None):
    def draw(s, to):
        pygame.draw.lines(s, color, closed, to(points), max(1, round(width / blur)))
    return _soft(draw, color, blur, radius or max(1, round(width / blur / 2)))


def speckle(shape, seed, count, colors, bbox, size=(1, 2.2)):
    """Textura de puntos (poros del hueso, grano de la goma) recortada a `shape`."""
    rng = random.Random(seed)
    layer = new_layer()
    x0, y0, x1, y1 = bbox
    for _ in range(count):
        circle(layer, rng.choice(colors), (rng.uniform(x0, x1), rng.uniform(y0, y1)), rng.uniform(*size))
    return clip_to(layer, shape)


def shaded_part(surf, points, base, highlight, rim, light, outline, outline_w=2.5, drop=None,
                rim_width=46):
    """Pieza con volumen: sombra proyectada, oclusión en el borde, brillo y contorno.

    `light` es (centro, rx, ry) del brillo principal. Devuelve la silueta de la pieza.
    """
    if drop:
        shadow = soft_fill(points, drop, offset=(5, 12), radius=6)
        surf.blit(clip_to(shadow, alpha_shape(surf)), (0, 0))
    shape = silhouette(points)
    layer = shape_fill(shape, base)
    layer.blit(clip_to(soft_line(points, rim, rim_width), shape), (0, 0))
    layer.blit(clip_to(soft_spot(highlight, *light), shape), (0, 0))
    if outline:
        lines(layer, outline, points, outline_w, closed=True)
    surf.blit(layer, (0, 0))
    return shape


def cylinder(surf, top, bottom, rx_top, ry_top, rx_bot, ry_bot, dark, base, light,
             ribs=(), rib_dark=None, rib_light=None, outline=None):
    """Cilindro (o cono truncado) visto ligeramente desde abajo: se ve su cara inferior.

    Sombreado por columnas con luz desde arriba a la izquierda. `ribs` son fracciones
    de la altura en las que se dibujan anillos en relieve.
    """
    cx = top[0]
    body = ([(cx - rx_top, top[1]), (cx - rx_bot, bottom[1])]
            + ellipse_points(cx, bottom[1], rx_bot, ry_bot, math.pi, 0)
            + [(cx + rx_top, top[1])]
            + ellipse_points(cx, top[1], rx_top, ry_top, 0, -math.pi))
    shape = silhouette(body)
    shade = new_layer()
    x0, x1 = cx - max(rx_top, rx_bot), cx + max(rx_top, rx_bot)
    y0, y1 = top[1] - ry_top, bottom[1] + ry_bot
    for col in range(int(x0 * SS), int(x1 * SS) + 1):
        u = clamp01(((col / SS) - x0) / (x1 - x0)) * 2 - 1
        n = math.sqrt(max(0.0, 1 - u * u))
        k = clamp01(-0.45 * u + 0.89 * n)
        color = lerp_color(dark, base, k)
        color = lerp_color(color, light, k ** 14)
        pygame.draw.line(shade, color, (col, int(y0 * SS)), (col, int(y1 * SS)))
    surf.blit(clip_to(shade, shape), (0, 0))
    for f in ribs:
        cy = lerp(top[1], bottom[1], f)
        rx, ry = lerp(rx_top, rx_bot, f), lerp(ry_top, ry_bot, f)
        lines(surf, rib_dark, ellipse_points(cx, cy, rx, ry, math.pi, 0), 5)
        lines(surf, rib_light, ellipse_points(cx, cy + 5, rx * 0.99, ry, math.pi * 0.9, math.pi * 0.35), 2)
    if outline:
        lines(surf, outline, body, 2.5, closed=True)
    return shape


def finish(surf):
    return pygame.transform.smoothscale(surf, (BASE_W, BASE_H))
