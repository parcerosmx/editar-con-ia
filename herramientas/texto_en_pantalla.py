#!/usr/bin/env python3
"""Pone un texto fijo sobre el video: el gancho de texto de los primeros segundos, o un letrero con un dato.

  .venv/bin/python herramientas/texto_en_pantalla.py VIDEO SALIDA.mp4 "El taco que nadie pide" [--desde 0] [--hasta 4]
        [--y 330] [--tam 72] [--fuente ruta.ttf] [--color "#FFFFFF"] [--fondo "#000000B3"] [--ancho 900] [--muestra]

  · El gancho de texto es LO ÚLTIMO que se hace, con el video ya armado (🟡 lección pagada), y va fijo en los
    primeros ~4 s. En un video con chiste, el gancho sirve al chiste: no adelanta la noticia.
  · Va dentro de la zona segura (y entre 205 y 1550 en 1920), lejos de las caras: Claude revisa con Vision que
    no tape una cara y avisa.
  · --fondo con transparencia (#RRGGBBAA) pone una caja detrás del texto; sin --fondo, letra con contorno.
  · --muestra: sólo arma los segundos del texto (+1 s) para revisarlo antes de hacer el video entero.
  · Para varios renglones, sepáralos con «|».
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

FUENTES = ["/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"]


def color(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in range(0, len(c), 2))


def envolver(d, texto, fuente, ancho):
    renglones = []
    for parte in texto.split("|"):
        linea = ""
        for w in parte.split():
            prueba = (linea + " " + w).strip()
            if d.textlength(prueba, font=fuente) <= ancho or not linea:
                linea = prueba
            else:
                renglones.append(linea)
                linea = w
        renglones.append(linea)
    return renglones


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("salida")
    ap.add_argument("texto")
    ap.add_argument("--desde", type=float, default=0.0)
    ap.add_argument("--hasta", type=float, default=4.0)
    ap.add_argument("--y", type=int, default=330, help="borde de arriba del texto, en px de 1920")
    ap.add_argument("--tam", type=int, default=72)
    ap.add_argument("--fuente")
    ap.add_argument("--color", default="#FFFFFF")
    ap.add_argument("--contorno", default="#111111")
    ap.add_argument("--fondo", help="caja detrás del texto, p. ej. #000000B3 (opcional)")
    ap.add_argument("--ancho", type=int, default=900)
    ap.add_argument("--muestra", action="store_true")
    a = ap.parse_args()
    from PIL import Image, ImageDraw, ImageFont
    fuente_ruta = a.fuente or next((f for f in FUENTES if Path(f).exists()), None)
    f = ImageFont.truetype(fuente_ruta, a.tam)
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    renglones = envolver(d, a.texto, f, a.ancho)
    alto_r = int(a.tam * 1.2)
    alto = alto_r * len(renglones)
    if a.y < 205 or a.y + alto > 1550:
        print("⚠️ el texto se sale de la zona segura (205–1550): la interfaz de la red lo puede tapar")
    if a.fondo:
        anch = max(d.textlength(r, font=f) for r in renglones)
        d.rounded_rectangle([(1080 - anch) / 2 - 28, a.y - 18, (1080 + anch) / 2 + 28, a.y + alto + 14], 22,
                            fill=color(a.fondo))
    for i, r in enumerate(renglones):
        w = d.textlength(r, font=f)
        d.text(((1080 - w) / 2, a.y + i * alto_r), r, font=f, fill=a.color,
               stroke_width=0 if a.fondo else max(3, a.tam // 12), stroke_fill=a.contorno)
    tmp = comun.carpeta_temporal()
    png = Path(tmp) / "texto.png"
    im.save(png)
    # ¿tapa una cara? se mira un cuadro en medio del tramo
    cuadro = Path(tmp) / "c.png"
    comun.ff("-ss", f"{(a.desde + a.hasta) / 2:.2f}", "-i", a.video, "-frames:v", "1", "-vf", "scale=1080:1920", cuadro)
    caras = comun.vision([cuadro]).get(str(cuadro), {}).get("caras", [])
    y0, y1 = a.y / 1920, (a.y + alto) / 1920
    if any(c[1] < y1 and c[3] > y0 for c in caras):
        print("⚠️ el texto queda encima de una cara en ese momento: muévelo con --y")
    corte = ["-ss", str(max(0, a.desde - 0.5)), "-t", str(a.hasta - a.desde + 1.5)] if a.muestra else []
    desfase = max(0, a.desde - 0.5) if a.muestra else 0
    comun.ff(*corte, "-i", a.video, "-loop", "1", "-i", png, "-filter_complex",
             f"[0:v][1:v]overlay=0:0:shortest=1:enable='between(t,{a.desde - desfase:.2f},{a.hasta - desfase:.2f})',format=yuv420p[v]",
             "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-c:a", "aac",
             "-b:a", "256k", "-movflags", "+faststart", a.salida)
    print(f"✔ {a.salida} · «{' / '.join(renglones)}» de {a.desde:g} a {a.hasta:g} s")


if __name__ == "__main__":
    main()
