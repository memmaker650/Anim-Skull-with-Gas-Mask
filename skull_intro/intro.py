"""Escena de la intro: línea de tiempo, gas, texto y reproducción."""

import functools
import math
import random
from dataclasses import dataclass
from pathlib import Path

import pygame

from .drawing import BASE_H, BASE_W, clamp01, ease_in_cubic, ease_out_cubic, lerp, smoothstep
from .gas_mask import draw_gas_mask
from .skull import draw_skull

FPS = 60
DEFAULT_TEXT = "Skull With Gas Mask Co."
FULL_DURATION = 13.0
QUICK_DURATION = 3.0
QUICK_THRESHOLD = 6.0  # por debajo de esta duración se usa el guion corto

GAS_MAX_ALPHA = round(255 * 0.75)  # opacidad final del gas: 75 %
GAS_COLOR = (52, 160, 38)
GAS_LIGHT = (100, 210, 66)

# Momentos de cada fase como fracción de la duración total.
FULL_SCRIPT = dict(
    dot_in=0.06, skull_in=(0.077, 0.115), zoom=(0.077, 0.354), mask=(0.385, 0.442),
    shake_end=0.473, gas=(0.492, 0.738), text=(0.708, 0.838),
)
# Guion corto: la calavera ya está a tamaño final, la máscara cae y el gas entra de golpe.
QUICK_SCRIPT = dict(
    dot_in=0.0, skull_in=(0.0, 0.08), zoom=(0.0, 0.0), mask=(0.08, 0.28),
    shake_end=0.38, gas=(0.32, 0.46), text=(0.42, 0.62),
)


def progress(t, span):
    start, end = span
    if end <= start:
        return 1.0 if t >= end else 0.0
    return clamp01((t - start) / (end - start))


@dataclass(frozen=True)
class Timeline:
    duration: float
    quick: bool
    dot_in: float
    skull_in: tuple
    zoom: tuple
    mask: tuple
    shake_end: float
    gas: tuple
    text: tuple

    @classmethod
    def build(cls, duration, mode="auto"):
        if mode not in ("auto", "full", "quick"):
            raise ValueError("mode debe ser 'auto', 'full' o 'quick'")
        quick = mode == "quick" or (mode == "auto" and duration < QUICK_THRESHOLD)
        script = QUICK_SCRIPT if quick else FULL_SCRIPT
        scaled = {k: tuple(v * duration for v in val) if isinstance(val, tuple) else val * duration
                  for k, val in script.items()}
        return cls(duration=duration, quick=quick, **scaled)


@functools.cache
def artwork():
    """Calavera y máscara (se dibujan una sola vez por proceso)."""
    skull, skull_shape = draw_skull()
    return skull, draw_gas_mask(skull_shape)


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
    def __init__(self, rng, timeline):
        self.x = rng.uniform(-0.1, 1.1)
        self.t0 = rng.uniform(timeline.gas[0] - 0.5, timeline.duration + 1.0)
        self.speed = rng.uniform(0.10, 0.22)   # alturas de pantalla por segundo
        self.radius = rng.uniform(0.12, 0.30)  # relativo a la altura de pantalla
        self.phase = rng.uniform(0, math.tau)
        self.life = rng.uniform(2.5, 4.5)


class SkullIntro:
    """Intro animada del logo, lista para incrustar en cualquier bucle de pygame.

    Uso típico dentro de tu propio bucle:

        intro = SkullIntro(duration=3)
        while intro.update(dt):      # dt en segundos
            intro.draw(screen)

    O de forma bloqueante con `intro.play(screen)`.

    `duration` son los segundos totales. Con `mode="auto"` las duraciones por debajo
    de QUICK_THRESHOLD usan el guion corto (sin punto ni zoom); `mode` puede forzarse
    a "full" o "quick". Se adapta al tamaño de la superficie en la que se dibuja.
    """

    def __init__(self, duration=FULL_DURATION, mode="auto", text=DEFAULT_TEXT, seed=7):
        self.timeline = Timeline.build(duration, mode)
        self.text = text
        self.elapsed = 0.0
        self.skull, self.mask = artwork()
        self.puff_sprite = make_puff_sprite()
        rng = random.Random(seed)
        self.puffs = [Puff(rng, self.timeline) for _ in range(70)]
        self._size = None
        self._scaled = {}

    @property
    def duration(self):
        return self.timeline.duration

    @property
    def finished(self):
        return self.elapsed >= self.timeline.duration

    def update(self, dt):
        """Avanza la animación `dt` segundos. Devuelve False cuando ha terminado."""
        self.elapsed += dt
        return not self.finished

    def skip(self):
        self.elapsed = self.timeline.duration

    def draw(self, surface):
        self.render(surface, min(self.elapsed, self.timeline.duration))

    def play(self, screen, clock=None, skippable=True):
        """Reproduce la intro de forma bloqueante. Devuelve False si se cierra la ventana."""
        clock = clock or pygame.time.Clock()
        self.elapsed = 0.0
        while not self.finished:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return False
                if skippable and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    return True
            self.draw(screen)
            pygame.display.flip()
            self.update(clock.tick(FPS) / 1000)
        return True

    # ------------------------------------------------------------ composición

    def _layout(self, size):
        if size == self._size:
            return
        self._size = size
        self.w, self.h = size
        # composición final: el logo ocupa ~70 % de la altura y deja sitio al texto
        self.final_h = self.h * 0.70
        self.final_scale = self.final_h / BASE_H
        self.anchor = (self.w / 2, self.h * 0.03 + self.final_h / 2)
        self.unit = self.h / 720
        self.gas_layer = pygame.Surface((max(1, self.w // 4), max(1, self.h // 4)), pygame.SRCALPHA)
        self.font = pygame.font.SysFont("impact,arialblack,helveticaneue,arial", round(self.h * 0.075))
        self.glyphs = [(self.font.render(ch, True, (255, 255, 255)),
                        self.font.render(ch, True, (0, 0, 0))) for ch in self.text]
        self._scaled.clear()

    def _scaled_art(self, name, surf, scale):
        size = (max(1, round(BASE_W * scale)), max(1, round(BASE_H * scale)))
        key = (name, size)
        if key not in self._scaled:
            if len(self._scaled) > 8:
                self._scaled.clear()
            self._scaled[key] = pygame.transform.smoothscale(surf, size)
        return self._scaled[key]

    @staticmethod
    def _blit_centered(screen, surf, center, alpha=255):
        surf.set_alpha(round(alpha))
        screen.blit(surf, surf.get_rect(center=(round(center[0]), round(center[1]))))
        surf.set_alpha(None)

    def render(self, screen, t):
        """Dibuja el fotograma del instante `t` (en segundos). Es determinista."""
        tl = self.timeline
        self._layout(screen.get_size())
        screen.fill((0, 0, 0))
        unit = self.unit

        # 1. punto blanco (solo en el guion largo)
        if tl.dot_in > 0:
            dot_alpha = clamp01(t / tl.dot_in) * (1 - progress(t, tl.skull_in))
            if dot_alpha > 0:
                pulse = 1 + 0.25 * math.sin(t * 7)
                dot = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(dot, (255, 255, 255, round(255 * dot_alpha)), (20, 20), 4 * unit * pulse)
                screen.blit(dot, dot.get_rect(center=(self.w // 2, self.h // 2)))

        # 2. zoom de la calavera (interpolación logarítmica: sensación de acercamiento)
        p = smoothstep(progress(t, tl.zoom))
        start_scale = 8 * unit / BASE_H
        scale = math.exp(lerp(math.log(start_scale), math.log(self.final_scale), p))
        center = [lerp(self.w / 2, self.anchor[0], p), lerp(self.h / 2, self.anchor[1], p)]

        # temblor al impactar la máscara
        shake = progress(t, (tl.mask[1], tl.shake_end))
        if 0 < shake < 1:
            amp = 16 * unit * (1 - shake) ** 2
            center[0] += amp * math.sin(t * 95)
            center[1] += amp * math.cos(t * 73)

        skull_alpha = 255 * progress(t, tl.skull_in)
        if skull_alpha > 0:
            self._blit_centered(screen, self._scaled_art("skull", self.skull, scale), center, skull_alpha)

        # 3. la máscara cae desde delante de la cámara y se ajusta a la cara
        m = progress(t, tl.mask)
        if m > 0:
            mask_scale = scale * lerp(2.8, 1.0, ease_in_cubic(m))
            self._blit_centered(screen, self._scaled_art("mask", self.mask, mask_scale), center,
                                255 * clamp01(m * 2.5))
        flash = progress(t, (tl.mask[1], tl.mask[1] + 0.2))
        if 0 < flash < 1:
            overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, round(70 * (1 - flash))))
            screen.blit(overlay, (0, 0))

        # 4. gas venenoso y 5. texto
        self._render_gas(screen, t)
        self._render_text(screen, t)

    def _render_gas(self, screen, t):
        g = progress(t, self.timeline.gas)
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
            edge.append((x, front + amp * (math.sin(x * 0.05 + t * 1.7) + 0.6 * math.sin(x * 0.11 - t * 2.3))))
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
            layer.blit(sprite, sprite.get_rect(center=(round(x), round(y))), special_flags=pygame.BLEND_RGBA_MAX)

        screen.blit(pygame.transform.smoothscale(layer, (self.w, self.h)), (0, 0))

    def _render_text(self, screen, t):
        p = progress(t, self.timeline.text)
        if p <= 0:
            return
        e = ease_out_cubic(p)
        unit = self.unit
        spacing = lerp(34, 4, e) * unit
        width = sum(g.get_width() for g, _ in self.glyphs) + spacing * (len(self.glyphs) - 1)
        text = pygame.Surface((math.ceil(width) + 12, self.font.get_height() + 12), pygame.SRCALPHA)
        shadow = text.copy()
        x = 6
        for white, black in self.glyphs:
            text.blit(white, (round(x), 6))
            shadow.blit(black, (round(x), 6))
            x += white.get_width() + spacing

        cy = self.anchor[1] + self.final_h / 2 + self.h * 0.09 + (1 - e) * 12 * unit
        rect = text.get_rect(center=(self.w / 2, cy))
        shadow.set_alpha(round(150 * e))
        for dx, dy in ((3, 3), (-2, 2), (2, -2), (-2, -2), (0, 4)):
            screen.blit(shadow, rect.move(dx * unit, dy * unit))
        text.set_alpha(round(255 * e))
        screen.blit(text, rect)


def is_first_launch(app_name="skull_with_gas_mask", marker_dir=None):
    """True la primera vez que se llama para `app_name`; deja un fichero marcador.

    El marcador se guarda en `marker_dir` (por defecto ~/.<app_name>/).
    """
    folder = Path(marker_dir) if marker_dir else Path.home() / f".{app_name}"
    marker = folder / "intro_seen"
    if marker.exists():
        return False
    folder.mkdir(parents=True, exist_ok=True)
    marker.touch()
    return True


def intro_for_launch(app_name="skull_with_gas_mask", first=FULL_DURATION, later=QUICK_DURATION, **kwargs):
    """Intro larga la primera vez que se abre la aplicación y corta en las siguientes."""
    return SkullIntro(duration=first if is_first_launch(app_name) else later, **kwargs)
