"""Carga de las imágenes del logo desde `resources/`.

La "calavera" es la ilustración del logo (calavera con su máscara), recortada de su
fondo gris y sin el texto. GasMask.png es la misma máscara a otra escala: se coloca de
modo que al caer encaje exactamente sobre la del logo.

Ambas se devuelven en un lienzo común de ART_W × BASE_H para dibujarse con el mismo centro.
"""

from collections import deque
from pathlib import Path

import pygame

from .drawing import BASE_H

RESOURCES = Path(__file__).parent / "resources"
SKULL_FILE = "calavera_SKwGM.png"
MASK_FILE = "GasMask.png"

ART_W = 1000

# Recorte del logo: filas por debajo de LOGO_CROP_H (el texto) se descartan.
LOGO_CROP_H = 718
# Fondo: se elimina por relleno desde los bordes con píxeles grises claros (>= BG_MIN) que
# cambian poco de un vecino a otro (BG_STEP); así se va también la sombra degradada del
# suelo pero el relleno se detiene en el contorno negro de la máscara.
BG_MIN = 70
BG_STEP = 5
SPECK_MAX = 60  # manchitas sueltas de menos píxeles que esto se borran

# Posición de GasMask.png dentro del logo original (medida superponiendo ambas imágenes).
MASK_IN_LOGO_SCALE = 0.395
MASK_IN_LOGO_POS = (42, 87)
# GasMask.png trae una sombra de suelo semitransparente bajo la máscara: se elimina.
MASK_SHADOW_FROM = 1390  # fila (en píxeles de la imagen original)
MASK_SHADOW_ALPHA = 110

LOGO_SCALE = BASE_H / LOGO_CROP_H


def canvas():
    return pygame.Surface((ART_W, BASE_H), pygame.SRCALPHA)


def logo_origin(logo_width):
    """Esquina superior izquierda del logo (de ancho original `logo_width`) en el lienzo."""
    return (ART_W - round(logo_width * LOGO_SCALE)) // 2, 0


def components(w, h, inside):
    """Regiones conexas (vecindad 4) de los píxeles donde `inside(x, y)` es cierto."""
    seen = [[False] * w for _ in range(h)]
    for y0 in range(h):
        for x0 in range(w):
            if seen[y0][x0] or not inside(x0, y0):
                continue
            seen[y0][x0] = True
            region, queue = [], deque([(x0, y0)])
            while queue:
                x, y = queue.popleft()
                region.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and inside(nx, ny):
                        seen[ny][nx] = True
                        queue.append((nx, ny))
            yield region


def cut_background(image):
    """Copia RGBA de `image` con el fondo (conectado a los bordes) transparente."""
    w, h = image.get_width(), min(image.get_height(), LOGO_CROP_H)
    px = [[tuple(image.get_at((x, y)))[:3] for x in range(w)] for y in range(h)]
    bg = [[False] * w for _ in range(h)]
    queue = deque([(x, y) for x in range(w) for y in (0, h - 1)] +
                  [(x, y) for y in range(h) for x in (0, w - 1)])
    for x, y in queue:
        bg[y][x] = True
    while queue:
        x, y = queue.popleft()
        c = px[y][x]
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not bg[ny][nx]:
                n = px[ny][nx]
                if min(n) >= BG_MIN and max(abs(a - b) for a, b in zip(n, c)) <= BG_STEP:
                    bg[ny][nx] = True
                    queue.append((nx, ny))
    for region in components(w, h, lambda x, y: not bg[y][x]):
        if len(region) < SPECK_MAX:
            for x, y in region:
                bg[y][x] = True

    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.blit(image, (0, 0))
    for y in range(h):
        for x in range(w):
            if bg[y][x]:
                out.set_at((x, y), (0, 0, 0, 0))
    return out


def load_skull():
    logo = cut_background(pygame.image.load(RESOURCES / SKULL_FILE))
    origin = logo_origin(logo.get_width())
    logo = pygame.transform.smoothscale(
        logo, (round(logo.get_width() * LOGO_SCALE), round(logo.get_height() * LOGO_SCALE)))
    surf = canvas()
    surf.blit(logo, origin)
    return surf


def load_mask():
    image = pygame.image.load(RESOURCES / MASK_FILE)
    w, h = image.get_size()
    for y in range(MASK_SHADOW_FROM, h):
        for x in range(w):
            if image.get_at((x, y)).a < MASK_SHADOW_ALPHA:
                image.set_at((x, y), (0, 0, 0, 0))
    scale = MASK_IN_LOGO_SCALE * LOGO_SCALE
    scaled = pygame.transform.smoothscale(image, (round(w * scale), round(h * scale)))
    ox, oy = logo_origin(pygame.image.load(RESOURCES / SKULL_FILE).get_width())
    surf = canvas()
    surf.blit(scaled, (ox + round(MASK_IN_LOGO_POS[0] * LOGO_SCALE), oy + round(MASK_IN_LOGO_POS[1] * LOGO_SCALE)))
    return surf
