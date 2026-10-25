#!/usr/bin/env python3
"""Revisa una base a cámara (o un video ya armado) ANTES de mandarla al dueño. Imprime ✅ / ⚠️ por punto.

  .venv/bin/python herramientas/verificar_base.py VIDEO [--guion hablado.txt]

  1 · VOZ       transcribe todo y busca restos de rodaje: «listo», «¿ya?», «dale», conteos, «otra vez»…
  2 · GUION     con --guion: qué palabras del guion no se oyen en el video (¿se comió alguna?)
  3 · HUECOS    silencios de más de 0,25 s entre palabras (espacios muertos)
  4 · VOLUMEN   LUFS, pico, y el nivel de cada tercio (¿se cansa la voz?)
  5 · PARPADEOS dos cambios de imagen a menos de 0,3 s (un cuadro suelto se ve como parpadeo)
  6 · NEGROS    cuadros negros
  7 · BORDES    cuánto aire queda antes de la primera palabra y después de la última
Lo que no puede revisar: el tono. Cada unión se le pide al dueño que la escuche, con su segundo.
"""
import argparse
import difflib
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

RESTOS = ["listo", "¿ya?", "dale", "dos, tres", "una, dos", "uno, dos", "otra vez", "vamos otra", "corte",
          "hasta ahí", "graba", "ya quedó"]


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-zñ0-9%]+", t)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--guion", help=".txt con sólo lo que se dice")
    a = ap.parse_args()
    import numpy as np
    comun.exigir("ffmpeg", "ffprobe", "whisper-cli")
    tmp = comun.carpeta_temporal()
    f = a.video
    wav = Path(tmp) / "a.wav"
    x = comun.audio_16k(f, wav)
    dur = comun.duracion(f)
    txt = comun.whisper_texto(wav)
    print(f"duración {dur:.2f} s\nse oye: «{txt}»")
    malas = [w for w in RESTOS if w in txt.lower()]
    print(("⚠️ posibles restos de rodaje: " + ", ".join(malas)) if malas else "✅ sin restos de rodaje («listo», «ya», conteos…)")
    if a.guion:
        esperado = norm(Path(a.guion).read_text(encoding="utf-8"))
        oido = norm(txt)
        sm = difflib.SequenceMatcher(None, esperado, oido, autojunk=False)
        faltan = [" ".join(esperado[i1:i2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("delete", "replace")]
        print(f"guion: {sm.ratio() * 100:.0f} % igual")
        print(("⚠️ del guion no se oye: " + " · ".join(f"«{w}»" for w in faltan)) if faltan else "✅ se oye todo el guion")
    db = comun.energia(x)
    ref = np.percentile(db, 90)
    q = db < ref - 24
    huecos, i = [], 0
    while i < len(q):
        if q[i]:
            j = i
            while j < len(q) and q[j]:
                j += 1
            huecos.append((i / 100, j / 100))
            i = j
        else:
            i += 1
    voz = np.where(~q)[0]
    v0, v1 = (voz[0] / 100, voz[-1] / 100) if len(voz) else (0, dur)
    dentro = [(h0, h1) for h0, h1 in huecos if h0 > v0 + 0.05 and h1 < v1 - 0.05 and h1 - h0 > 0.25]
    print(("⚠️ huecos de más de 0,25 s: " + " ".join(f"{h0:.2f}-{h1:.2f}" for h0, h1 in dentro)) if dentro
          else "✅ sin huecos de más de 0,25 s entre palabras")
    print(f"bordes: la voz arranca en {v0:.2f} s y se apaga en {v1:.2f} s (quedan {dur - v1:.2f} s al final)")
    r = subprocess.run([comun.ffmpeg(), "-v", "info", "-i", f, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    P = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    partes = [s[s > ref - 20] for s in np.array_split(db, 3)]
    ter = [10 * np.log10(np.mean(10 ** (s / 10))) if len(s) else -99 for s in partes]
    if I:
        print(f"volumen {I[-1]} LUFS, pico {P[-1] if P else '?'} dBFS · voz por tercios "
              f"{ter[0]:.1f} / {ter[1]:.1f} / {ter[2]:.1f} dB" + (" ⚠️ se cansa" if ter[0] - ter[2] > 3 else " ✅ pareja"))
    r = subprocess.run([comun.ffmpeg(), "-v", "info", "-i", f, "-vf", "scdet=threshold=8", "-an", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    cs = [float(m) for m in re.findall(r"lavfi.scd.time:\s*([\d.]+)", r)]
    cerca = [(c0, c1) for c0, c1 in zip(cs, cs[1:]) if c1 - c0 < 0.3]
    print(f"cambios de imagen ({len(cs)}): {' '.join(f'{c:.2f}' for c in cs[:60])}")
    print(("⚠️ parpadeo: " + " ".join(f"{c0:.2f}/{c1:.2f}" for c0, c1 in cerca)) if cerca
          else "✅ sin parpadeos (ningún par de cambios a menos de 0,3 s)")
    r = subprocess.run([comun.ffmpeg(), "-v", "info", "-i", f, "-vf", "blackdetect=d=0.03:pix_th=0.06", "-an", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    negros = re.findall(r"black_start:([\d.]+)", r)
    print(("⚠️ cuadros negros en: " + " ".join(negros)) if negros else "✅ sin cuadros negros")


if __name__ == "__main__":
    main()
