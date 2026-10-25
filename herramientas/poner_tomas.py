#!/usr/bin/env python3
"""Pega las tomas de apoyo que eligió el dueño encima de la base a cámara. La voz no se toca.

  .venv/bin/python herramientas/poner_tomas.py tomas.json SALIDA.mp4

tomas.json:
  {"base": "proyectos/mi-video/base-v1.mp4",
   "lut": null,                                    ← tu color para las tomas de apoyo (opcional, una sola vez)
   "tomas": [{"archivo": "material/01-tomas-de-apoyo/IMG_0412.MOV", "desde": 3.2, "en": 2.93, "dura": 0.8,
              "x": 0.5, "zoom": 1.0, "dice": "queso"}, ...]}

  · «en»: segundo de la BASE donde entra. Úsalo en un salto de quitar_pausas.py (el borde exacto entre palabras)
    y con la palabra que la toma muestra.
  · «desde»: segundo del archivo donde la acción YA está pasando.
  · «dura»: lo de tu hoja de estilo (ejemplo: mediana 0,8 s; nunca menos de ~0,75 s salvo la ráfaga del arranque).
  · Cuenta por cuadros: avisa si dos cambios quedan a menos de 0,3 s (parpadeo) o si una toma dura menos de 0,5 s.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402


def ruta(p):
    p = Path(os.path.expanduser(p))
    return p if p.is_absolute() else comun.RAIZ / p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tomas")
    ap.add_argument("salida")
    a = ap.parse_args()
    comun.exigir("ffmpeg", "ffprobe")
    cfg = json.load(open(a.tomas, encoding="utf-8"))
    base = ruta(cfg["base"])
    R, _ = comun.fps(base)
    Q = lambda t: round(t * R) / R
    s = comun.sonda(base)
    v = next(x for x in s["streams"] if x["codec_type"] == "video")
    W, H = v["width"], v["height"]
    tomas = sorted(cfg["tomas"], key=lambda t: t["en"])
    bordes = sorted({Q(t["en"]) for t in tomas} | {Q(t["en"] + t["dura"]) for t in tomas})
    for b0, b1 in zip(bordes, bordes[1:]):
        if 0 < b1 - b0 < 0.3:
            print(f"⚠️ dos cambios de imagen a {b1 - b0:.2f} s ({b0:.2f} y {b1:.2f}): se verá como parpadeo")
    for t in tomas:
        if t["dura"] < 0.5:
            print(f"⚠️ la toma de {t['en']:.2f} s dura {t['dura']:.2f} s: marea")
    lut = f",lut3d=file='{ruta(cfg['lut'])}'" if cfg.get("lut") else ""
    ins, fc, last = ["-i", str(base)], [], "0:v"
    for k, t in enumerate(tomas):
        f = ruta(t["archivo"])
        pre, fi = comun.entrada(f)
        en, d = Q(t["en"]), Q(t["dura"])
        z, x = t.get("zoom", 1.0), t.get("x", 0.5)
        ins += [*pre, "-ss", f"{t.get('desde', 0):.3f}", "-t", f"{d + 0.2:.3f}", "-i", str(f)]
        fc.append(f"[{k + 1}:v]{fi},fps={R:.5f},scale={int(W * z)}:{int(H * z)}:force_original_aspect_ratio=increase,"
                  f"crop={W}:{H}:(iw-{W})*{x}:(ih-{H})/2,setsar=1{lut},format=yuv420p,setpts=PTS-STARTPTS+{en:.4f}/TB[t{k}]")
        fc.append(f"[{last}][t{k}]overlay=0:0:eof_action=pass:enable='between(t,{en:.4f},{en + d - 0.5 / R:.4f})'[o{k}]")
        last = f"o{k}"
    comun.ff(*ins, "-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "0:a?", "-c:v", "libx264",
             "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", a.salida)
    dur = comun.duracion(base)
    apoyo = sum(Q(t["dura"]) for t in tomas)
    print(f"✔ {a.salida} · {len(tomas)} tomas de apoyo · {100 * apoyo / dur:.0f} % del video es apoyo, "
          f"{100 - 100 * apoyo / dur:.0f} % a cámara")


if __name__ == "__main__":
    main()
