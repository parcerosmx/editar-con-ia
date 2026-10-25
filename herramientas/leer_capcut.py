#!/usr/bin/env python3
"""Lee un proyecto de CapCut de esta Mac SIN tocarlo y cuenta cómo montaste las tomas: así Claude aprende
tu criterio de tu propio proyecto, no de una descripción.

  .venv/bin/python herramientas/leer_capcut.py [nombre-del-proyecto] [--json salida.json] [--carpeta RUTA]

Sin nombre: el proyecto que modificaste más recientemente.
Por cada pista y cada pieza: archivo, tramo usado (entrada→salida), dónde va en la línea de tiempo, si va
pegada, encimada o con hueco respecto a la anterior, velocidad, volumen, fundidos, y qué ajustes de CapCut
tiene prendidos (color inteligente, mejora de voz, LUT…). Al final, un resumen: duración mediana de las
piezas y cuánto encimas al cambiar de toma.

Nunca escribe en la carpeta de CapCut (CapCut 10 rechaza borradores tocados por otras herramientas).
Probado con CapCut 9.5 para Mac; otra versión puede guardar distinto.
"""
import argparse
import glob
import json
import os
import statistics as st
import sys
from pathlib import Path

CAPCUT = (Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "CapCut" / "User Data" / "Projects"
          / "com.lveditor.draft" if os.name == "nt"     # Windows (sin probar: puede guardar distinto)
          else Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft")


def info(p):
    fs = [f for f in [os.path.join(p, "draft_info.json")] + glob.glob(os.path.join(p, "Timelines", "*", "draft_info.json"))
          if os.path.exists(f)]
    return max(fs, key=os.path.getmtime) if fs else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("nombre", nargs="?", help="nombre (o parte del nombre) del proyecto en CapCut")
    ap.add_argument("--json", help="guardar el resumen en este archivo")
    ap.add_argument("--carpeta", default=str(CAPCUT), help="carpeta de proyectos de CapCut")
    a = ap.parse_args()
    D = a.carpeta
    if not os.path.isdir(D):
        sys.exit(f"✗ No encontré la carpeta de proyectos de CapCut ({D}). ¿Está instalado CapCut de escritorio?")
    cands = [p for p in glob.glob(os.path.join(D, "*")) if os.path.isdir(p) and info(p)]
    nombres = {}
    try:
        for d in json.load(open(os.path.join(D, "root_meta_info.json"), encoding="utf-8")).get("all_draft_store", []):
            nombres[os.path.basename(d.get("draft_fold_path", ""))] = d.get("draft_name", "")
    except Exception:
        pass
    if a.nombre:
        q = a.nombre.lower()
        cands = [p for p in cands if q in nombres.get(os.path.basename(p), "").lower() or q in os.path.basename(p).lower()]
    if not cands:
        sys.exit("✗ No encontré ese proyecto en CapCut.")
    p = max(cands, key=lambda x: os.path.getmtime(info(x)))
    f = info(p)
    j = json.load(open(f, encoding="utf-8"))
    S = lambda us: us / 1e6
    mat = {}
    for k, v in j.get("materials", {}).items():
        if isinstance(v, list):
            for m in v:
                if isinstance(m, dict) and "id" in m:
                    mat[m["id"]] = (k, m)
    titulo = nombres.get(os.path.basename(p)) or j.get("name") or os.path.basename(p)
    print(f"Proyecto «{titulo}» · {S(j['duration']):.2f} s · {j.get('fps')} fps")
    out = {"proyecto": titulo, "duracion": S(j["duration"]), "pistas": []}
    largos, encimados = [], []
    for ti, t in enumerate(j.get("tracks", [])):
        segs = sorted(t["segments"], key=lambda s: s["target_timerange"]["start"])
        print(f"\n— pista {ti} ({t['type']}), {len(segs)} piezas")
        P = {"tipo": t["type"], "piezas": []}
        fin_ant = None
        for s in segs:
            k, m = mat.get(s["material_id"], ("?", {}))
            nom = m.get("material_name") or os.path.basename(m.get("path", "")) or m.get("name") or (
                m.get("content", "")[:40] if k == "texts" else k)
            tg = s["target_timerange"]
            sr = s.get("source_timerange") or {"start": 0, "duration": 0}
            t0, t1 = S(tg["start"]), S(tg["start"] + tg["duration"])
            a0, a1 = S(sr["start"]), S(sr["start"] + sr["duration"])
            if fin_ant is None:
                junta = ""
            elif t0 < fin_ant - 1e-3:
                junta = f"encima {fin_ant - t0:.2f} s"
                encimados.append(round(fin_ant - t0, 2))
            elif t0 > fin_ant + 1e-3:
                junta = f"hueco {t0 - fin_ant:.2f} s"
            else:
                junta = "pegada"
            if t["type"] == "video":
                largos.append(t1 - t0)
            extras = []
            for r in s.get("extra_material_refs", []):
                kk, mm = mat.get(r, ("?", {}))
                if kk == "audio_fades" and (mm.get("fade_in_duration") or mm.get("fade_out_duration")):
                    extras.append(f"fundido {S(mm.get('fade_in_duration', 0)):.2f}/{S(mm.get('fade_out_duration', 0)):.2f}")
                elif kk not in ("?", "vocal_separations", "speeds", "canvases", "sound_channel_mappings",
                                "material_colors", "placeholder_infos", "audio_fades"):
                    extras.append(kk)
            for fl in ("enable_smart_color_adjust", "enable_lut", "enable_color_curves", "enable_color_correct_adjust"):
                if s.get(fl):
                    extras.append(fl.replace("enable_", ""))
            v, sp = s.get("volume", 1), s.get("speed", 1)
            print(f"  {t0:6.2f}→{t1:6.2f}  [{junta:>14}]  {nom[:46]:46s} usa {a0:6.2f}→{a1:6.2f}"
                  + (f"  vel {sp:g}" if sp != 1 else "") + (f"  vol {v:.2f}" if v != 1 else "")
                  + ("  " + ", ".join(extras) if extras else ""))
            P["piezas"].append(dict(t0=t0, t1=t1, junta=junta, archivo=os.path.basename(m.get("path", nom)),
                                    entrada=a0, salida=a1, velocidad=sp, volumen=v, extras=extras))
            fin_ant = t1
        out["pistas"].append(P)
    if largos:
        print(f"\nResumen: {len(largos)} piezas de video · mediana {st.median(largos):.2f} s"
              + (f" · encimas {st.median(encimados):.2f} s al cambiar de toma ({len(encimados)} veces)" if encimados else ""))
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print("→", a.json)


if __name__ == "__main__":
    main()
