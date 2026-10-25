#!/usr/bin/env python3
"""Una página para revisar tocando botones en vez de escribir. Se abre en el navegador de la Mac.

  .venv/bin/python herramientas/storyboard.py version  VIDEO CARPETA [--cortes 2.1,3.4,...] [--titulo T] [--ronda N] [--dudas dudas.txt]
  .venv/bin/python herramientas/storyboard.py opciones opciones.json CARPETA [--titulo T] [--ronda N] [--dudas dudas.txt]

  version   parte el video en tramos (en cada cambio de toma, o en --cortes) y pone cada tramo con su clip y tres
            botones: Se queda · Cambiar · Quitar, más una nota opcional.
  opciones  las tomas de apoyo candidatas para cada idea del guion, 2 s cada una en bucle; el dueño toca las que
            le gustan. opciones.json (ejemplo en ejemplos/opciones.json):
              {"ideas": [{"id": "queso", "titulo": "El queso que se estira",
                          "ops": [["material/01-tomas-de-apoyo/IMG_0412.MOV", 3.2, "queso de cerca"], ...]}]}
  --dudas   un .txt con una duda por línea (lo que Whisper oyó dudoso, lo que no se pudo verificar): van ARRIBA.

Al terminar, el dueño toca «Copiar mis respuestas» y las pega en el chat con Claude: un solo pegado.
Abrir:  open CARPETA/index.html
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

AQUI = Path(__file__).resolve().parent
V = "scale=360:640:force_original_aspect_ratio=increase,crop=360:640,setsar=1,format=yuv420p"


def ruta(p):
    p = Path(os.path.expanduser(p))
    return p if p.is_absolute() else comun.RAIZ / p


def cortes_auto(video, dur):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(video), "-vf", "scale=180:-2,select='gt(scene,0.3)',showinfo",
                        "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    cs = []
    for t in sorted(float(x) for x in re.findall(r"pts_time:([0-9.]+)", r)):
        if 0.3 < t < dur - 0.3 and (not cs or t - cs[-1] > 0.4):
            cs.append(t)
    return cs


def version(video, S, op):
    video = ruta(video)
    total = comun.duracion(video)
    cs = [float(c) for c in op.cortes.split(",")] if op.cortes else cortes_auto(video, total)
    bordes = [0.0] + cs + [total]
    (S / "c").mkdir(parents=True, exist_ok=True)
    tramos = []
    for n, (a, b) in enumerate(zip(bordes, bordes[1:]), 1):
        k = f"{n:02d}"
        a0, b0 = max(0, a - 0.2), min(total, b + 0.2)
        comun.ff("-ss", f"{a0:.3f}", "-t", f"{b0 - a0:.3f}", "-i", video, "-vf", V, "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "30", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", S / "c" / f"{k}.mp4")
        comun.ff("-ss", f"{(a + b) / 2:.3f}", "-i", video, "-frames:v", "1", "-vf", V, "-q:v", "5", S / "c" / f"{k}.jpg")
        tramos.append({"id": f"t{k}", "n": n, "desde": round(a, 2), "hasta": round(b, 2),
                       "clip": f"c/{k}.mp4", "poster": f"c/{k}.jpg"})
    return {"modo": "version", "tramos": tramos, "chips": [f"{total:.1f} s", f"{len(tramos)} tramos"]}


def opciones(cfg_f, S, op):
    cfg = json.load(open(cfg_f, encoding="utf-8"))
    ideas = []
    for idea in cfg["ideas"]:
        d = S / "o" / idea["id"]
        d.mkdir(parents=True, exist_ok=True)
        ops = []
        for n, o in enumerate(idea["ops"], 1):
            src, tin, txt = o[:3]
            x = o[3] if len(o) > 3 else 0.5          # encuadre de una toma horizontal (0 izquierda – 1 derecha)
            f = ruta(src)
            pre, fi = comun.entrada(f)
            vf = (f"{fi},scale=360:640:force_original_aspect_ratio=increase,crop=360:640:(iw-360)*{x}:(ih-640)/2,"
                  "setsar=1,format=yuv420p")
            comun.ff(*pre, "-ss", str(tin), "-t", "2", "-i", f, "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
                     "-crf", "30", "-movflags", "+faststart", d / f"{n:02d}.mp4")
            comun.ff("-i", d / f"{n:02d}.mp4", "-frames:v", "1", "-q:v", "5", d / f"{n:02d}.jpg")
            rel = f"o/{idea['id']}/{n:02d}"
            ops.append({"n": n, "desc": txt, "clip": rel + ".mp4", "poster": rel + ".jpg", "archivo": str(src), "t": tin})
        ideas.append({"id": idea["id"], "titulo": idea["titulo"], "ops": ops})
    return {"modo": "opciones", "ideas": ideas,
            "chips": [f"{len(ideas)} ideas", f"{sum(len(i['ops']) for i in ideas)} opciones"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modo", choices=["version", "opciones"])
    ap.add_argument("entrada", help="el VIDEO (version) o el opciones.json (opciones)")
    ap.add_argument("carpeta", help="dónde dejar la página (p. ej. proyectos/mi-video/revision-1)")
    ap.add_argument("--cortes", help="version: segundos de corte separados por coma (si no, se detectan)")
    ap.add_argument("--titulo")
    ap.add_argument("--ronda", type=int, default=1)
    ap.add_argument("--dudas", help=".txt con una duda por línea")
    a = ap.parse_args()
    comun.exigir("ffmpeg", "ffprobe")
    S = ruta(a.carpeta).resolve()
    S.mkdir(parents=True, exist_ok=True)
    datos = version(a.entrada, S, a) if a.modo == "version" else opciones(a.entrada, S, a)
    dudas = [l.strip() for l in Path(a.dudas).read_text(encoding="utf-8").splitlines() if l.strip()] if a.dudas else []
    titulo = (a.titulo or Path(a.entrada).stem).replace("<", "")
    datos.update(titulo=titulo, ronda=a.ronda, dudas=dudas)
    html = (AQUI / "storyboard.html").read_text(encoding="utf-8")
    html = html.replace("__TITULO__", titulo).replace("/*DATOS*/null", json.dumps(datos, ensure_ascii=False).replace("</", "<\\/"))
    (S / "index.html").write_text(html, encoding="utf-8")
    print(f"✔ {S / 'index.html'}\n  ábrela con:  open \"{S / 'index.html'}\"")


if __name__ == "__main__":
    main()
