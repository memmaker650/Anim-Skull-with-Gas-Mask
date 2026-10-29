"""Lanzador de la intro: python -m skull_intro [opciones]  (o python skull_intro)"""

import argparse
import os
import sys

import pygame

if not __package__:
    # ejecutado como `python skull_intro`: hace importable el paquete desde su carpeta padre
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skull_intro.intro import FPS, FULL_DURATION, QUICK_DURATION, SkullIntro

WIDTH, HEIGHT = 1280, 720


def export_frames(screen, intro, folder):
    os.makedirs(folder, exist_ok=True)
    total = int(intro.duration * FPS)
    for i in range(total):
        intro.render(screen, i / FPS)
        pygame.image.save(screen, os.path.join(folder, f"frame_{i:04d}.png"))
        print(f"\r{i + 1}/{total}", end="", flush=True)
    print(f"\nListo. Para crear el vídeo:\n"
          f"  ffmpeg -framerate {FPS} -i {folder}/frame_%04d.png -c:v libx264 -pix_fmt yuv420p intro.mp4")


def main():
    parser = argparse.ArgumentParser(prog="python -m skull_intro",
                                     description="Intro animada de Skull With Gas Mask Co.")
    parser.add_argument("--duration", type=float, default=FULL_DURATION,
                        help=f"duración en segundos (por defecto {FULL_DURATION:g})")
    parser.add_argument("--quick", action="store_true",
                        help=f"versión corta de {QUICK_DURATION:g} s (aperturas sucesivas)")
    parser.add_argument("--mode", choices=("auto", "full", "quick"), default="auto",
                        help="guion: auto (según la duración), full o quick")
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

    duration = QUICK_DURATION if args.quick else args.duration
    intro = SkullIntro(duration=duration, mode=args.mode)
    if args.export:
        export_frames(screen, intro, args.export)
    else:
        while intro.play(screen, skippable=not args.loop) and args.loop:
            pass
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
