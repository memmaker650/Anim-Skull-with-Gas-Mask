# Skull with Gas Mask

Animación de entrada (intro) del logo de **Skull With Gas Mask Co.**, hecha en Python con [pygame-ce](https://pyga.me/).

1. Fondo negro con un punto blanco en el centro.
2. El punto crece hasta revelar una calavera en primer plano.
3. Una máscara de gas cae sobre la calavera.
4. Gas venenoso verde llena la pantalla (opacidad final del 75 %).
5. Aparece el texto «Skull With Gas Mask Co.» bajo la calavera.

Todo se dibuja por código (no hacen falta imágenes).

## Instalación

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Uso

```bash
.venv/bin/python intro_animacion.py                  # ventana 1280x720 (cualquier tecla la salta)
.venv/bin/python intro_animacion.py --fullscreen     # pantalla completa
.venv/bin/python intro_animacion.py --loop           # repetir hasta pulsar ESC
.venv/bin/python intro_animacion.py --export frames  # guardar los fotogramas en PNG (60 fps)
```

Con los fotogramas exportados se puede generar un vídeo:

```bash
ffmpeg -framerate 60 -i frames/frame_%04d.png -c:v libx264 -pix_fmt yuv420p intro.mp4
```

### Integrarla en otra aplicación pygame

```python
from intro_animacion import play_intro

play_intro(screen)  # devuelve False si el usuario cierra la ventana
```

Los tiempos, colores y el texto están como constantes al principio de `intro_animacion.py`.
