#!/usr/bin/env python3
"""Hace un video de prueba de unos segundos, sin material de nadie: tres «tomas» de colores con cortes,
un texto en pantalla y una voz de la Mac (comando `say`) diciendo una frase con pausas. Si la Mac no
tiene voz en español, pone un tono.

  .venv/bin/python herramientas/video_de_prueba.py SALIDA.mp4 [--sin-voz]

Lo usa herramientas/chequeo.sh para probar que todo funciona. No se sube al repo.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

FRASE = "Hola. Esto es una prueba. [[slnc 700]] Hoy hicimos arepas, tacos y café de olla."


def voz(destino, tmp):
    """Voz en español con `say` (viene con la Mac). Devuelve True si salió."""
    for nombre in ("Paulina", "Mónica", "Eddy (Spanish (Mexico))", "Flo (Spanish (Mexico))"):
        aiff = Path(tmp) / "voz.aiff"
        r = subprocess.run(["say", "-v", nombre, "-o", str(aiff), FRASE], capture_output=True)
        if r.returncode == 0 and aiff.exists() and aiff.stat().st_size > 10000:
            comun.ff("-i", aiff, "-ar", "48000", "-ac", "1", destino)
            return True
    return False


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("salida")
    p.add_argument("--sin-voz", action="store_true", help="sólo un tono, sin voz")
    a = p.parse_args()
    from PIL import Image, ImageDraw, ImageFont
    tmp = comun.carpeta_temporal()
    wav = Path(tmp) / "audio.wav"
    con_voz = not a.sin_voz and voz(wav, tmp)
    if not con_voz:
        comun.ff("-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-ar", "48000", "-ac", "1", wav)
    dur = max(4.0, comun.duracion(wav) + 0.4)
    # el texto en pantalla, dibujado con Pillow (el ffmpeg de Homebrew no trae drawtext)
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fuente = None
    for f in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if Path(f).exists():
            fuente = ImageFont.truetype(f, 64)
            break
    texto = "VIDEO DE PRUEBA"
    w = d.textlength(texto, font=fuente) if fuente else 400
    d.text(((1080 - w) / 2, 1300), texto, font=fuente, fill="white", stroke_width=6, stroke_fill="black")
    png = Path(tmp) / "texto.png"
    im.save(png)
    t1, t2 = round(dur * 0.4, 2), round(dur * 0.7, 2)
    # tres «tomas» con imagen distinta (patrones de prueba de ffmpeg), para que haya cortes que medir
    fondo = (f"testsrc2=s=1080x1920:r=30:d={t1}[a];smptebars=s=1080x1920:r=30:d={t2 - t1:.2f}[b];"
             f"rgbtestsrc=s=1080x1920:r=30:d={dur - t2:.2f}[c];"
             f"[a][b][c]concat=n=3:v=1:a=0,setsar=1[f];[f][1:v]overlay=0:0,format=yuv420p[v]")
    comun.ff("-f", "lavfi", "-i", "nullsrc=s=16x16:d=0.1", "-loop", "1", "-t", f"{dur:.2f}", "-i", png, "-i", wav,
             "-filter_complex", fondo, "-map", "[v]", "-map", "2:a", "-t", f"{dur:.2f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k", a.salida)
    print(f"✔ {a.salida} · {dur:.1f} s · {'con voz de la Mac' if con_voz else 'con tono (sin voz)'}")


if __name__ == "__main__":
    main()
