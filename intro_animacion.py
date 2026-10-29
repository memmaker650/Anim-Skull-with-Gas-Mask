"""Animación de entrada del logo de Skull With Gas Mask Co.

Guion:
    1. Fondo negro con un punto blanco en el centro.
    2. El punto crece y se revela como una calavera que llega a primer plano.
    3. Una máscara de gas cae sobre la calavera y se ajusta a su cara.
    4. Gas venenoso verde sube y llena la pantalla hasta un 75 % de opacidad.
    5. Aparece el texto de la compañía bajo la calavera.

Uso:
    python intro_animacion.py                  # ventana 1280x720
    python intro_animacion.py --fullscreen     # pantalla completa
    python intro_animacion.py --loop           # repetir (ESC para salir)
    python intro_animacion.py --export frames  # guardar PNGs a 60 fps

Para usarla dentro de otra aplicación pygame:
    from intro_animacion import play_intro
    play_intro(screen)
"""

import argparse
import math
import os
import random
import sys

import pygame

WIDTH, HEIGHT = 1280, 720
FPS = 60
TEXT = "Skull With Gas Mask Co."

# Línea de tiempo (segundos)
T_DOT_IN = 0.8
T_ZOOM_START, T_ZOOM_END = 1.0, 4.6
T_MASK_START, T_MASK_END = 5.0, 5.75
T_SHAKE_END = 6.15
T_GAS_START, T_GAS_END = 6.4, 9.6
T_TEXT_START, T_TEXT_END = 9.2, 10.9
DURATION = 13.0

GAS_MAX_ALPHA = round(255 * 0.75)  # opacidad final del gas: 75 %
GAS_COLOR = (52, 160, 38)
GAS_LIGHT = (100, 210, 66)

# Espacio de coordenadas en el que se dibujan la calavera y la máscara
BASE_W, BASE_H = 800, 1000
SS = 2  # supersampling para suavizar los bordes


# ---------------------------------------------------------------- utilidades

def clamp01(x):
    return max(0.0, min(1.0, x))


def progress(t, start, end):
    return clamp01((t - start) / (end - start))


def lerp(a, b, x):
    return a + (b - a) * x


def smoothstep(x):
    return x * x * (3 - 2 * x)


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_in_cubic(x):
    return x ** 3


def smooth_closed(points, steps=12):
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
    left = [(BASE_W - x, y) for x, y in reversed(right_half[1:-1])]
    return right_half + left


def mirror(points):
    return [(BASE_W - x, y) for x, y in points]


def sc(points):
    return [(x * SS, y * SS) for x, y in points]


def r(v):
    return int(v * SS)


def sc_rect(x, y, w, h):
    return pygame.Rect(r(x), r(y), r(w), r(h))


def circle(surf, color, center, radius, width=0):
    pygame.draw.circle(surf, color, (r(center[0]), r(center[1])), r(radius), r(width) if width else 0)


def arc(surf, color, center, radius, start, stop, width):
    rect = sc_rect(center[0] - radius, center[1] - radius, radius * 2, radius * 2)
    pygame.draw.arc(surf, color, rect, start, stop, r(width))


def new_layer():
    return pygame.Surface((BASE_W * SS, BASE_H * SS), pygame.SRCALPHA)


def silhouette(points):
    layer = new_layer()
    pygame.draw.polygon(layer, (255, 255, 255, 255), sc(points))
    return layer


def soft_light(color, holes, blur=8):
    """Capa de sombreado suave: `color` en todas partes salvo en las elipses `holes`."""
    small = pygame.Surface((BASE_W // blur, BASE_H // blur), pygame.SRCALPHA)
    small.fill(color)
    for x, y, w, h in holes:
        pygame.draw.ellipse(small, (0, 0, 0, 0), (x / blur, y / blur, w / blur, h / blur))
    small = pygame.transform.gaussian_blur(small, 6)
    return pygame.transform.smoothscale(small, (BASE_W * SS, BASE_H * SS))


def soft_spot(color, ellipse, blur=8):
    """Mancha suave de `color` (para brillos) sobre fondo transparente."""
    small = pygame.Surface((BASE_W // blur, BASE_H // blur), pygame.SRCALPHA)
    x, y, w, h = ellipse
    pygame.draw.ellipse(small, color, (x / blur, y / blur, w / blur, h / blur))
    small = pygame.transform.gaussian_blur(small, 6)
    return pygame.transform.smoothscale(small, (BASE_W * SS, BASE_H * SS))


def clip_to(layer, shape):
    """Recorta `layer` a la silueta `shape` multiplicando su alfa."""
    layer.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return layer


def shape_fill(shape, color):
    layer = shape.copy()
    layer.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
    return layer


def finish(surf):
    return pygame.transform.smoothscale(surf, (BASE_W, BASE_H))


# ---------------------------------------------------------------- calavera

SKULL_OUTLINE = smooth_closed(symmetric([
    (400, 40), (575, 75), (680, 180), (715, 330), (695, 455), (668, 520),
    (672, 585), (628, 650), (592, 700), (592, 800), (560, 885), (480, 935), (400, 945),
]), 8)


def draw_tooth(surf, cx, top, w, h, fill, edge, upper):
    rect = sc_rect(cx - w / 2, top, w, h)
    rad = r(w * 0.45)
    corners = ({"border_bottom_left_radius": rad, "border_bottom_right_radius": rad} if upper
               else {"border_top_left_radius": rad, "border_top_right_radius": rad})
    pygame.draw.rect(surf, fill, rect, **corners)
    pygame.draw.rect(surf, edge, rect, r(2), **corners)


def draw_skull():
    bone = (238, 233, 218)
    shade = (196, 188, 170)
    dark = (16, 14, 12)
    shape = silhouette(SKULL_OUTLINE)
    surf = shape_fill(shape, bone)

    # sombreado en los bordes y bajo los pómulos
    shading = soft_light((95, 85, 70, 110), [(150, 60, 500, 500), (290, 540, 220, 380)])
    surf.blit(clip_to(shading, shape), (0, 0))

    # grieta en el cráneo
    pygame.draw.lines(surf, (80, 72, 62), False,
                      sc([(545, 82), (522, 140), (550, 188), (524, 240), (538, 275)]), r(4))

    # cuencas de los ojos y arco superciliar
    eye = [(425, 335), (515, 312), (600, 330), (640, 392), (618, 462), (548, 492), (472, 478), (430, 432)]
    brow = [(418, 316), (515, 290), (614, 310), (655, 360)]
    cheek = [(560, 520), (615, 548), (645, 600)]
    for side in (lambda p: p, mirror):
        pygame.draw.polygon(surf, dark, sc(smooth_closed(side(eye))))
        pygame.draw.lines(surf, shade, False, sc(side(brow)), r(6))
        pygame.draw.lines(surf, shade, False, sc(side(cheek)), r(5))

    # cavidad nasal (corazón invertido)
    nose = [(400, 512), (424, 548), (446, 604), (432, 630), (414, 626), (400, 612)]
    pygame.draw.polygon(surf, dark, sc(smooth_closed(symmetric(nose), 6)))

    # boca y dientes
    pygame.draw.ellipse(surf, dark, sc_rect(262, 738, 276, 44))
    widths = [27, 26, 25, 23, 21, 19]
    x = 0
    for i, w in enumerate(widths):
        for side in (1, -1):
            cx = 400 + side * (x + w / 2)
            draw_tooth(surf, cx, 692, w - 2, 60 - i * 4, bone, shade, upper=True)
            draw_tooth(surf, cx, 770, w - 2, 50 - i * 4, bone, shade, upper=False)
        x += w

    # mandíbula
    jaw = [(560, 705), (572, 800), (546, 868), (468, 912)]
    for pts in (jaw, mirror(jaw)):
        pygame.draw.lines(surf, shade, False, sc(pts), r(4))

    pygame.draw.lines(surf, (70, 66, 58), True, sc(SKULL_OUTLINE), r(4))
    return finish(surf), shape


# ---------------------------------------------------------------- máscara de gas

MASK_OUTLINE = smooth_closed(symmetric([
    (400, 282), (520, 278), (628, 312), (680, 398), (684, 500), (658, 598),
    (604, 712), (536, 822), (466, 885), (400, 898),
]), 8)

LENSES = [(282, 405), (518, 405)]
LENS_R = 100
CANISTER = (400, 705)


def draw_strap(surf, start, end, width, color, stitch):
    pygame.draw.line(surf, color, sc([start])[0], sc([end])[0], r(width))
    # costura discontinua por el centro de la correa
    steps = int(math.dist(start, end) // 18)
    for i in range(0, steps, 2):
        a = [lerp(start[k], end[k], i / steps) for k in (0, 1)]
        b = [lerp(start[k], end[k], (i + 1) / steps) for k in (0, 1)]
        pygame.draw.line(surf, stitch, sc([a])[0], sc([b])[0], r(2))


def draw_gas_mask(skull_shape):
    rubber = (40, 43, 38)
    rubber_hi = (74, 78, 66)
    rubber_dark = (20, 22, 19)
    metal = (128, 130, 120)
    metal_hi = (205, 206, 196)
    metal_dark = (62, 64, 58)
    olive = (78, 86, 60)
    olive_dark = (50, 56, 38)

    surf = new_layer()

    # correas del arnés, recortadas a la silueta de la calavera
    straps = new_layer()
    strap, stitch = (58, 52, 42), (110, 100, 82)
    draw_strap(straps, (400, 300), (400, 150), 56, strap, stitch)
    for side in (lambda p: p, lambda p: (BASE_W - p[0], p[1])):
        draw_strap(straps, side((400, 160)), side((640, 20)), 48, strap, stitch)
        draw_strap(straps, side((640, 340)), side((780, 250)), 50, strap, stitch)
        draw_strap(straps, side((650, 610)), side((790, 560)), 50, strap, stitch)
    pygame.draw.rect(straps, metal, sc_rect(372, 150, 56, 36), border_radius=r(6))
    pygame.draw.rect(straps, metal_dark, sc_rect(372, 150, 56, 36), r(3), border_radius=r(6))
    surf.blit(clip_to(straps, skull_shape), (0, 0))

    # pieza facial de goma
    face = silhouette(MASK_OUTLINE)
    surf.blit(shape_fill(face, rubber), (0, 0))
    surf.blit(clip_to(soft_spot((rubber_hi + (150,)), (150, 300, 300, 330)), face), (0, 0))
    surf.blit(clip_to(soft_light((0, 0, 0, 110), [(150, 300, 500, 520)]), face), (0, 0))
    pygame.draw.lines(surf, rubber_dark, True, sc(MASK_OUTLINE), r(8))
    seam = [(lerp(400, x, 0.93), lerp(580, y, 0.93)) for x, y in MASK_OUTLINE]
    pygame.draw.lines(surf, rubber_hi, True, sc(seam), r(2))
    for x, y in seam[::12]:
        circle(surf, metal, (x, y), 5)

    # pliegue del puente de la nariz
    pygame.draw.lines(surf, rubber_dark, False, sc([(400, 330), (392, 420), (400, 500)]), r(5))

    # cuerpo del respirador (morro)
    snout = smooth_closed(symmetric([(400, 505), (450, 512), (505, 580), (545, 690), (400, 740)]), 8)
    pygame.draw.polygon(surf, rubber_dark, sc(snout))
    for i, y in enumerate(range(540, 680, 28)):
        half = 46 + i * 22
        pygame.draw.line(surf, rubber_hi, sc([(400 - half, y)])[0], sc([(400 + half, y)])[0], r(3))

    # válvulas laterales de exhalación
    for cx in (238, 562):
        circle(surf, rubber_dark, (cx, 650), 42)
        circle(surf, metal_dark, (cx, 650), 34)
        for k in range(-2, 3):
            pygame.draw.line(surf, rubber_dark, sc([(cx - 26, 650 + k * 11)])[0],
                             sc([(cx + 26, 650 + k * 11)])[0], r(4))
        circle(surf, metal, (cx, 650), 34, 4)

    # filtro (bote) frontal
    cx, cy = CANISTER
    circle(surf, (0, 0, 0, 120), (cx, cy + 12), 132)
    circle(surf, metal_dark, CANISTER, 126)
    circle(surf, olive, CANISTER, 118)
    for rad in (102, 84):
        circle(surf, olive_dark, CANISTER, rad, 5)
        arc(surf, (120, 130, 92), CANISTER, rad - 4, math.radians(100), math.radians(190), 3)
    circle(surf, metal, CANISTER, 60)
    circle(surf, metal_dark, CANISTER, 60, 4)
    circle(surf, rubber_dark, CANISTER, 7)
    for ring, count in ((22, 6), (40, 12)):
        for k in range(count):
            a = 2 * math.pi * k / count
            circle(surf, rubber_dark, (cx + ring * math.cos(a), cy + ring * math.sin(a)), 6)
    arc(surf, metal_hi, CANISTER, 120, math.radians(95), math.radians(175), 4)

    # visores
    for center in LENSES:
        circle(surf, rubber_dark, center, LENS_R + 16)
        circle(surf, metal_dark, center, LENS_R + 10)
        circle(surf, metal, center, LENS_R + 5)
        arc(surf, metal_hi, center, LENS_R + 4, math.radians(95), math.radians(200), 5)
        circle(surf, metal_dark, center, LENS_R - 6)
        # el cristal es semitransparente: se intuyen las cuencas de la calavera
        circle(surf, (60, 100, 72, 150), center, LENS_R - 12)
        for k in range(10):
            a = 2 * math.pi * k / 10 + 0.3
            pos = (center[0] + (LENS_R + 2) * math.cos(a), center[1] + (LENS_R + 2) * math.sin(a))
            circle(surf, metal_hi, pos, 5)
            circle(surf, metal_dark, pos, 2)
        glare = new_layer()
        arc(glare, (255, 255, 255, 110), (center[0] - 6, center[1] - 6), LENS_R - 28,
            math.radians(105), math.radians(165), 9)
        circle(glare, (255, 255, 255, 90), (center[0] + 40, center[1] + 38), 7)
        surf.blit(glare, (0, 0))

    return finish(surf)


# ---------------------------------------------------------------- gas

def make_puff_sprite(size=64):
    """Mancha radial: RGB de GAS_COLOR (borde) a GAS_LIGHT (centro) y alfa hasta GAS_MAX_ALPHA."""
    sprite = pygame.Surface((size, size), pygame.SRCALPHA)
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            d = clamp01(math.hypot(x - c, y - c) / c)
            k = (1 - d) ** 2
            rgb = [round(lerp(GAS_COLOR[i], GAS_LIGHT[i], k)) for i in range(3)]
            sprite.set_at((x, y), (*rgb, round(GAS_MAX_ALPHA * smoothstep(1 - d))))
    return sprite


class Puff:
    def __init__(self, rng):
        self.x = rng.uniform(-0.1, 1.1)
        self.t0 = rng.uniform(T_GAS_START - 0.5, DURATION + 1.0)
        self.speed = rng.uniform(0.10, 0.22)   # alturas de pantalla por segundo
        self.radius = rng.uniform(0.12, 0.30)  # relativo a la altura de pantalla
        self.phase = rng.uniform(0, math.tau)
        self.life = rng.uniform(2.5, 4.5)


# ---------------------------------------------------------------- escena

class Intro:
    def __init__(self, size, seed=7):
        self.w, self.h = size
        self.skull, skull_shape = draw_skull()
        self.mask = draw_gas_mask(skull_shape)

        # composición final: la calavera ocupa ~2/3 de la altura y deja sitio al texto
        self.final_h = self.h * 0.66
        self.final_scale = self.final_h / BASE_H
        self.anchor = (self.w / 2, self.h * 0.05 + self.final_h / 2)

        self.gas_div = 4  # el gas se calcula a 1/4 de resolución y se suaviza al escalar
        self.gas_layer = pygame.Surface((self.w // self.gas_div, self.h // self.gas_div), pygame.SRCALPHA)
        self.puff_sprite = make_puff_sprite()
        rng = random.Random(seed)
        self.puffs = [Puff(rng) for _ in range(70)]

        font_size = round(self.h * 0.075)
        self.font = pygame.font.SysFont("impact,arialblack,helveticaneue,arial", font_size)
        self.glyphs = [(self.font.render(ch, True, (255, 255, 255)),
                        self.font.render(ch, True, (0, 0, 0))) for ch in TEXT]
        self._scaled = {}

    # -- helpers
    def scaled(self, name, surf, scale):
        size = (max(1, round(BASE_W * scale)), max(1, round(BASE_H * scale)))
        key = (name, size)
        if key not in self._scaled:
            if len(self._scaled) > 8:
                self._scaled.clear()
            self._scaled[key] = pygame.transform.smoothscale(surf, size)
        return self._scaled[key]

    def blit_centered(self, screen, surf, center, alpha=255):
        surf.set_alpha(round(alpha))
        screen.blit(surf, surf.get_rect(center=(round(center[0]), round(center[1]))))
        surf.set_alpha(None)

    # -- render
    def render(self, screen, t):
        screen.fill((0, 0, 0))
        unit = self.h / 720

        # 1. punto blanco
        dot_alpha = progress(t, 0.0, T_DOT_IN) * (1 - progress(t, T_ZOOM_START, T_ZOOM_START + 0.5))
        if dot_alpha > 0:
            pulse = 1 + 0.25 * math.sin(t * 7)
            dot = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(dot, (255, 255, 255, round(255 * dot_alpha)), (20, 20), 4 * unit * pulse)
            screen.blit(dot, dot.get_rect(center=(self.w // 2, self.h // 2)))

        # 2. zoom de la calavera (interpolación logarítmica: sensación de acercamiento)
        p = smoothstep(progress(t, T_ZOOM_START, T_ZOOM_END))
        start_scale = 8 * unit / BASE_H
        scale = math.exp(lerp(math.log(start_scale), math.log(self.final_scale), p))
        center = [lerp(self.w / 2, self.anchor[0], p), lerp(self.h / 2, self.anchor[1], p)]

        # temblor al impactar la máscara
        shake = progress(t, T_MASK_END, T_SHAKE_END)
        if 0 < shake < 1:
            amp = 16 * unit * (1 - shake) ** 2
            center[0] += amp * math.sin(t * 95)
            center[1] += amp * math.cos(t * 73)

        skull_alpha = 255 * progress(t, T_ZOOM_START, T_ZOOM_START + 0.5)
        if skull_alpha > 0:
            self.blit_centered(screen, self.scaled("skull", self.skull, scale), center, skull_alpha)

        # 3. la máscara cae desde delante de la cámara y se ajusta a la cara
        m = progress(t, T_MASK_START, T_MASK_END)
        if m > 0:
            mask_scale = scale * lerp(2.8, 1.0, ease_in_cubic(m))
            self.blit_centered(screen, self.scaled("mask", self.mask, mask_scale), center,
                               255 * clamp01(m * 2.5))
        flash = progress(t, T_MASK_END, T_MASK_END + 0.2)
        if 0 < flash < 1:
            overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, round(70 * (1 - flash))))
            screen.blit(overlay, (0, 0))

        # 4. gas venenoso
        self.render_gas(screen, t)

        # 5. texto
        self.render_text(screen, t)

    def render_gas(self, screen, t):
        g = progress(t, T_GAS_START, T_GAS_END)
        if g <= 0:
            return
        layer = self.gas_layer
        gw, gh = layer.get_size()
        layer.fill((0, 0, 0, 0))

        # frente de gas que sube con borde ondulado
        front = lerp(gh * 1.15, -gh * 0.3, smoothstep(g))
        amp = gh * 0.045
        edge = [(0, gh)]
        for x in range(0, gw + 6, 6):
            y = front + amp * (math.sin(x * 0.05 + t * 1.7) + 0.6 * math.sin(x * 0.11 - t * 2.3))
            edge.append((x, y))
        edge.append((gw, gh))
        pygame.draw.polygon(layer, (*GAS_COLOR, GAS_MAX_ALPHA), edge)

        # volutas que suben con el gas; la mezcla MAX garantiza que el alfa nunca supera el 75 %
        for puff in self.puffs:
            age = t - puff.t0
            if not 0 < age < puff.life:
                continue
            fade = math.sin(math.pi * age / puff.life)
            size = max(2, round(puff.radius * gh * 2 * (0.7 + 0.5 * age / puff.life)))
            y = max(front, 0) + gh * 0.2 - age * puff.speed * gh
            x = puff.x * gw + math.sin(puff.phase + age * 1.3) * gh * 0.05
            sprite = pygame.transform.smoothscale(self.puff_sprite, (size, size))
            sprite.fill((255, 255, 255, round(255 * fade)), special_flags=pygame.BLEND_RGBA_MULT)
            layer.blit(sprite, sprite.get_rect(center=(round(x), round(y))),
                       special_flags=pygame.BLEND_RGBA_MAX)

        screen.blit(pygame.transform.smoothscale(layer, (self.w, self.h)), (0, 0))

    def render_text(self, screen, t):
        p = progress(t, T_TEXT_START, T_TEXT_END)
        if p <= 0:
            return
        e = ease_out_cubic(p)
        unit = self.h / 720
        spacing = lerp(34, 4, e) * unit
        width = sum(g.get_width() for g, _ in self.glyphs) + spacing * (len(self.glyphs) - 1)
        height = self.font.get_height()
        text = pygame.Surface((math.ceil(width) + 12, height + 12), pygame.SRCALPHA)
        shadow = text.copy()
        x = 6
        for white, black in self.glyphs:
            text.blit(white, (round(x), 6))
            shadow.blit(black, (round(x), 6))
            x += white.get_width() + spacing

        cy = self.anchor[1] + self.final_h / 2 + self.h * 0.085 + (1 - e) * 12 * unit
        rect = text.get_rect(center=(self.w / 2, cy))
        shadow.set_alpha(round(150 * e))
        for dx, dy in ((3, 3), (-2, 2), (2, -2), (-2, -2), (0, 4)):
            screen.blit(shadow, rect.move(dx * unit, dy * unit))
        text.set_alpha(round(255 * e))
        screen.blit(text, rect)


# ---------------------------------------------------------------- reproducción

def play_intro(screen, clock=None, skippable=True):
    """Reproduce la intro sobre `screen`. Devuelve False si el usuario cierra la ventana."""
    clock = clock or pygame.time.Clock()
    intro = Intro(screen.get_size())
    t = 0.0
    while t < DURATION:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
            if skippable and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return True
        intro.render(screen, t)
        pygame.display.flip()
        t += clock.tick(FPS) / 1000
    return True


def export_frames(screen, folder):
    os.makedirs(folder, exist_ok=True)
    intro = Intro(screen.get_size())
    total = int(DURATION * FPS)
    for i in range(total):
        intro.render(screen, i / FPS)
        pygame.image.save(screen, os.path.join(folder, f"frame_{i:04d}.png"))
        print(f"\r{i + 1}/{total}", end="", flush=True)
    print(f"\nListo. Para crear el vídeo:\n"
          f"  ffmpeg -framerate {FPS} -i {folder}/frame_%04d.png -c:v libx264 -pix_fmt yuv420p intro.mp4")


def main():
    parser = argparse.ArgumentParser(description="Intro animada de Skull With Gas Mask Co.")
    parser.add_argument("--fullscreen", action="store_true", help="pantalla completa")
    parser.add_argument("--loop", action="store_true", help="repetir hasta pulsar ESC")
    parser.add_argument("--export", metavar="CARPETA", help="guardar los fotogramas como PNG")
    args = parser.parse_args()

    if args.export:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_caption("Skull With Gas Mask Co.")
    if args.fullscreen and not args.export:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
    else:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))

    if args.export:
        export_frames(screen, args.export)
    else:
        while play_intro(screen, skippable=not args.loop) and args.loop:
            pass
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
