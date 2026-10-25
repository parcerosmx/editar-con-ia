#!/usr/bin/env python3
"""Hoja de cuadros: un cuadro por cada segundo que pidas, con la hora encima. Es la forma de VER un momento
del video (Claude no lo puede reproducir): ¿entró el texto? ¿tapa una cara? ¿cae bajo la interfaz de la red?

  .venv/bin/python herramientas/hoja_cuadros.py VIDEO 1.5 2.0 3.2 ... [--salida hoja.jpg] [--cols 6] [--ancho 270]
        [--zona-segura] [--muestra DESDE HASTA]

  --zona-segura  dibuja las franjas que tapa la interfaz de TikTok/Reels (arriba ~200 px y abajo ~370 de 1920)
  --muestra      además corta ese tramo con sonido (muestra.mp4 junto a la hoja) para mandarlo a revisar
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("tiempos", nargs="+", help="segundos (1.5, 12, …)")
    ap.add_argument("--salida", default="hoja.jpg")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--ancho", type=int, default=270)
    ap.add_argument("--zona-segura", action="store_true")
    ap.add_argument("--muestra", nargs=2, type=float, metavar=("DESDE", "HASTA"))
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    comun.exigir("ffmpeg")
    tmp = comun.carpeta_temporal()
    ims = []
    for t in a.tiempos:
        f = Path(tmp) / f"{t}.png"
        comun.ff("-ss", t, "-i", a.video, "-frames:v", "1", "-vf", f"scale={a.ancho}:-2", f)
        ims.append((t, Image.open(f).convert("RGB")))
    w, h = ims[0][1].size
    filas = -(-len(ims) // a.cols)
    hoja = Image.new("RGB", (w * min(a.cols, len(ims)), h * filas))
    for i, (t, im) in enumerate(ims):
        d = ImageDraw.Draw(im, "RGBA")
        if a.zona_segura:
            d.rectangle((0, 0, w, int(h * 205 / 1920)), fill=(255, 0, 0, 70))
            d.rectangle((0, int(h * 1550 / 1920), w, h), fill=(255, 0, 0, 70))
        d.rectangle((0, 0, 8 * len(t) + 22, 22), fill="black")
        d.text((6, 5), f"{t} s", fill="yellow")
        hoja.paste(im, ((i % a.cols) * w, (i // a.cols) * h))
    hoja.save(a.salida, quality=88)
    print(f"✔ {a.salida}  ({len(ims)} cuadros)")
    if a.muestra:
        m = str(Path(a.salida).with_name("muestra.mp4"))
        comun.ff("-ss", a.muestra[0], "-t", a.muestra[1] - a.muestra[0], "-i", a.video, "-c:v", "libx264", "-preset",
                 "veryfast", "-crf", "23", "-c:a", "aac", "-movflags", "+faststart", m)
        print(f"✔ {m}")


if __name__ == "__main__":
    main()
