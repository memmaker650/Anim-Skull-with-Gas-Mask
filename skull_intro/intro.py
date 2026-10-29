"""Escena de la intro: línea de tiempo, gas, texto y reproducción."""

import functools
import math
import random
from dataclasses import dataclass
from pathlib import Path

import pygame

from .art import load_mask, load_skull
from .drawing import BASE_H, clamp01, ease_in_cubic, ease_out_cubic, lerp, smoothstep

FPS = 60
DEFAULT_TEXT = "Skull with Gas Mask Studio"
FULL_DURATION = 9.0
QUICK_DURATION = 3.0
QUICK_THRESHOLD = 6.0  # por debajo de esta duración se usa el guion corto

GAS_MAX_ALPHA = round(255 * 0.75)  # opacidad final del gas: 75 %
GAS_DARK = (34, 120, 28)    # fondo de la masa de gas
GAS_LIGHT = (110, 214, 70)  # centro iluminado de cada nube

# Momentos de cada fase como fracción de la duración total. En ambos guiones la calavera
# aparece ya en primer plano; el largo se recrea más en cada fase.
FULL_SCRIPT = dict(
    skull_in=(0.0, 0.14), mask=(0.24, 0.31), shake_end=0.36, gas=(0.38, 0.68), text=(0.64, 0.82),
)
# Guion corto: la máscara cae enseguida y el gas entra de golpe.
QUICK_SCRIPT = dict(
    skull_in=(0.0, 0.08), mask=(0.08, 0.28), shake_end=0.38, gas=(0.32, 0.46), text=(0.42, 0.62),
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
    skull_in: tuple
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
    """Calavera y máscara (se cargan una sola vez por proceso)."""
    return load_skull(), load_mask()


def make_puff_sprite(size=96):
    """Bola de nube: núcleo opaco (hasta GAS_MAX_ALPHA) con borde suave, iluminada desde
    arriba (GAS_LIGHT en la parte alta, GAS_DARK abajo y en el borde)."""
    sprite = pygame.Surface((size, size), pygame.SRCALPHA)
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            d = clamp01(math.hypot(x - c, y - c) / c)
            top = clamp01(0.5 - (y - c) / c * 0.6)        # 1 arriba, 0 abajo
            k = (1 - d) ** 0.8 * top
            rgb = [round(lerp(GAS_DARK[i], GAS_LIGHT[i], k)) for i in range(3)]
            sprite.set_at((x, y), (*rgb, round(GAS_MAX_ALPHA * smoothstep(clamp01((1 - d) / 0.45)))))
    return sprite


class Cloud:
    """Nube del frente de gas. Las de la base cabecean sobre el frente y tapan su borde;
    las demás nacen en él, suben, crecen y se disuelven en bucle."""

    def __init__(self, rng, x, base):
        self.x = x                                # fracción del ancho
        self.base = base
        self.radius = rng.uniform(0.16, 0.26) if base else rng.uniform(0.10, 0.20)  # × alto
        self.period = rng.uniform(1.8, 3.2)       # segundos por ciclo de subida
        self.phase = rng.random()
        self.rise = rng.uniform(0.20, 0.38)       # altura que sube en un ciclo (× alto)
        self.sway = rng.uniform(0, math.tau)


class Wisp:
    """Voluta más clara dentro de la masa de gas: le da textura mientras sube."""

    def __init__(self, rng):
        self.x = rng.uniform(-0.05, 1.05)
        self.phase = rng.random()
        self.speed = rng.uniform(0.05, 0.12)      # alturas por segundo
        self.radius = rng.uniform(0.16, 0.30)
        self.sway = rng.uniform(0, math.tau)


class SkullIntro:
    """Intro animada del logo, lista para incrustar en cualquier bucle de pygame.

    Uso típico dentro de tu propio bucle:

        intro = SkullIntro(duration=3)
        while intro.update(dt):      # dt en segundos
            intro.draw(screen)

    O de forma bloqueante con `intro.play(screen)`.

    `duration` son los segundos totales. Con `mode="auto"` las duraciones por debajo
    de QUICK_THRESHOLD usan el guion corto; `mode` puede forzarse
    a "full" o "quick". Se adapta al tamaño de la superficie en la que se dibuja.
    """

    def __init__(self, duration=FULL_DURATION, mode="auto", text=DEFAULT_TEXT, seed=7):
        self.timeline = Timeline.build(duration, mode)
        self.text = text
        self.elapsed = 0.0
        self.skull, self.mask = artwork()
        self.puff_sprite = make_puff_sprite()
        self.gas_fade = pygame.Surface((1, 64), pygame.SRCALPHA)
        for y in range(64):
            self.gas_fade.set_at((0, y), (*GAS_DARK, round(GAS_MAX_ALPHA * smoothstep(y / 63))))
        rng = random.Random(seed)
        n = 16
        self.clouds = ([Cloud(rng, (i + rng.uniform(0.2, 0.8)) / n * 1.2 - 0.1, True) for i in range(n)]
                       + [Cloud(rng, rng.uniform(-0.1, 1.1), False) for _ in range(34)])
        self.wisps = [Wisp(rng) for _ in range(26)]
        self._sprites = {}
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
        size = (max(1, round(surf.get_width() * scale)), max(1, round(surf.get_height() * scale)))
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

        # 1. la calavera aparece ya en primer plano, a su tamaño final
        scale = self.final_scale
        center = list(self.anchor)

        # temblor al impactar la máscara
        shake = progress(t, (tl.mask[1], tl.shake_end))
        if 0 < shake < 1:
            amp = 16 * unit * (1 - shake) ** 2
            center[0] += amp * math.sin(t * 95)
            center[1] += amp * math.cos(t * 73)

        skull_alpha = 255 * progress(t, tl.skull_in)
        if skull_alpha > 0:
            self._blit_centered(screen, self._scaled_art("skull", self.skull, scale), center, skull_alpha)

        # 2. la máscara cae desde delante de la cámara y se ajusta a la cara
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

        # 3. gas venenoso y 4. texto
        self._render_gas(screen, t)
        self._render_text(screen, t)

    def _puff(self, size, alpha=1.0):
        """Sprite de nube a `size` px (cacheado) con su opacidad multiplicada por `alpha`."""
        size = max(2, int(size) // 2 * 2)
        if size not in self._sprites:
            self._sprites[size] = pygame.transform.smoothscale(self.puff_sprite, (size, size))
        sprite = self._sprites[size]
        if alpha < 1:
            sprite = sprite.copy()
            sprite.fill((255, 255, 255, round(255 * alpha)), special_flags=pygame.BLEND_RGBA_MULT)
        return sprite

    def _render_gas(self, screen, t):
        g = progress(t, self.timeline.gas)
        if g <= 0:
            return
        layer = self.gas_layer
        gw, gh = layer.get_size()
        layer.fill((*GAS_DARK, 0))
        # Todo se mezcla con MAX: el alfa nunca pasa del 75 % y las nubes solo aclaran el color.
        blend = pygame.BLEND_RGBA_MAX

        def put(sprite, x, y):
            layer.blit(sprite, sprite.get_rect(center=(round(x), round(y))), special_flags=blend)

        # masa de gas: sube desde abajo hasta cubrir la pantalla
        front = lerp(gh * 1.35, -gh * 0.6, smoothstep(g))
        fade_h = max(1, round(gh * 0.22))  # el borde superior se funde bajo las nubes de la base
        top = round(front)
        if top < gh:
            if top + fade_h > 0:
                put(pygame.transform.smoothscale(self.gas_fade, (gw, fade_h)), gw / 2, top + fade_h / 2)
            if top + fade_h < gh:
                layer.fill((*GAS_DARK, GAS_MAX_ALPHA), (0, max(0, top + fade_h), gw, gh))

        # volutas claras dentro de la masa, subiendo despacio
        for w in self.wisps:
            y = gh * (1.2 - ((t * w.speed + w.phase) % 1.0) * 1.6)
            r = w.radius * gh
            inside = clamp01((y - front) / r)          # se apagan al llegar al frente
            if inside > 0:
                put(self._puff(r * 2, 0.45 * inside), w.x * gw + math.sin(t * 0.7 + w.sway) * gh * 0.04, y)

        # frente de nubes: bocanadas que suben, crecen y se disuelven
        for c in self.clouds:
            sway = math.sin(t * 0.9 + c.sway) * gh * 0.03
            if c.base:
                r = c.radius * gh * (1 + 0.12 * math.sin(t * 1.3 + c.sway))
                put(self._puff(r * 2), c.x * gw + sway, front + gh * 0.02 + math.cos(t * 1.1 + c.sway) * gh * 0.02)
                continue
            age = (t / c.period + c.phase) % 1.0
            r = c.radius * gh * (0.6 + 0.7 * age)
            y = front - age * c.rise * gh
            put(self._puff(r * 2, min(1.0, 3 * age) * (1 - age) ** 1.5), c.x * gw + sway * (1 + age), y)

        screen.blit(pygame.transform.smoothscale(layer, (self.w, self.h)), (0, 0))

    def _render_text(self, screen, t):
        p = progress(t, self.timeline.text)
        if p <= 0:
            return
        e = ease_out_cubic(p)
        unit = self.unit
        spacing = lerp(22, 3, e) * unit
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
