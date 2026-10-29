# Skull with Gas Mask

Animación de entrada (intro) del logo de **Skull With Gas Mask Co.**, hecha en Python con [pygame-ce](https://pyga.me/).
Todo se dibuja por código (no hacen falta imágenes).

**Versión larga** (por defecto 13 s, pensada para la primera apertura):
fondo negro con un punto blanco → el punto crece hasta revelar una calavera → cae la máscara de gas →
el gas verde llena la pantalla (75 % de opacidad) → aparece «Skull With Gas Mask Co.».

**Versión corta** (por defecto 3 s, para las aperturas siguientes): la calavera aparece ya a tamaño final,
cae la máscara, el gas entra de golpe y aparece el nombre.

## Instalación

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Probarla

```bash
.venv/bin/python -m skull_intro                  # versión larga, ventana 1280x720
.venv/bin/python -m skull_intro --quick          # versión corta (3 s)
.venv/bin/python -m skull_intro --duration 8     # cualquier duración
.venv/bin/python -m skull_intro --fullscreen --loop
.venv/bin/python -m skull_intro --export frames  # fotogramas PNG a 60 fps
```

Las duraciones por debajo de 6 s usan automáticamente el guion corto; se puede forzar con `--mode full|quick`.

## Integrarla en tu aplicación

```python
from skull_intro import SkullIntro, intro_for_launch

# Bloqueante: larga la primera vez que se abre la app, corta las siguientes
intro_for_launch("mi_app", first=13, later=3).play(screen)

# O dentro de tu propio bucle / animación
intro = SkullIntro(duration=3)
while intro.update(dt):          # dt en segundos
    intro.draw(screen)           # o intro.draw(una_subsuperficie)
```

- `SkullIntro(duration, mode="auto", text="Skull With Gas Mask Co.")`
- `render(surface, t)` dibuja el instante `t` de forma determinista (sirve para sincronizarla con otras animaciones).
- `skip()` salta al final; `finished` indica si ha terminado.
- `is_first_launch(app_name)` devuelve `True` solo la primera vez (guarda un marcador en `~/.<app_name>/`).
