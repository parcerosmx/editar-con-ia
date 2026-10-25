#!/usr/bin/env python3
"""Une las tomas de un video a cámara (una por frase o por parte) como las une un editor con oído.

  .venv/bin/python herramientas/unir_tomas.py plan.json

plan.json (ejemplo en ejemplos/plan-unir.json):
  {"carpeta": "material/02-a-camara",            ← dónde están las tomas
   "salida": "proyectos/mi-video/base-v1.mp4",
   "lut": "estilo/mi-color.cube",                 ← opcional: tu color, aplicado UNA vez
   "partes": [
     {"parte": "gancho", "elegida": "toma-03.mov", "suplentes": ["toma-01.mov"]},
     {"parte": "plato",  "elegida": "toma-07.mov", "quitar": [[4.2, 5.0]], "respetar": [2.0, 2.6]},
     {"parte": "cierre", "elegida": "toma-12.mov", "encima": false}]}

  · «elegida» es la que va; «suplentes» quedan anotadas para cambiarlas con un solo movimiento (elegir la
    toma es gusto del dueño: Claude propone, no adivina)
  · «quitar»: tramos de la toma (en segundos) que se van: un tropiezo, una frase repetida
  · «respetar»: una pausa que se deja a propósito (suspenso); ahí no se cortan silencios
  · «encima»: true/false manda; si no se dice, se decide midiendo cómo cae la última palabra

Las reglas (🟡 medidas en el proyecto de CapCut de un editor, oct-2026):
  1 · cada toma ENTRA justo cuando arranca la voz y SALE cuando se apaga la última palabra (+0,03 s);
      una «s» final (siseo) se respeta: no se corta «tacos» en «taco»
  2 · dentro de la toma se quitan las pausas desde 0,08 s y quedan ~0,03 s (quitar_pausas.py)
  3 · al cambiar de toma, la siguiente se ENCIMA 0,18 s sobre la cola de la anterior (imagen y voz) para que
      no se note el corte y la palabra que va cayendo termine; o va PEGADA si la palabra corta en seco
Imprime cada unión con su segundo: hay que escucharlas (Claude no oye el tono).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

AQUI = Path(__file__).resolve().parent


def ruta(p):
    p = Path(os.path.expanduser(p))
    return p if p.is_absolute() else comun.RAIZ / p


def energia_de(f, tmp):
    import numpy as np
    x = comun.audio_16k(f, Path(tmp) / "e.wav")
    db = comun.energia(x)
    return db, float(np.percentile(db, 92)), x


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", help="el plan.json")
    a = ap.parse_args()
    import numpy as np
    comun.exigir("ffmpeg", "ffprobe", "whisper-cli")
    cfg = json.load(open(a.plan, encoding="utf-8"))
    tmp = comun.carpeta_temporal()
    C, OUT = ruta(cfg["carpeta"]), ruta(cfg["salida"])
    ENC, COLA = cfg.get("encimado", 0.18), cfg.get("cola", 0.03)
    partes = [p for p in cfg["partes"] if p.get("incluir", True)]
    segs = []
    for k, p in enumerate(partes):
        src = str(C / p["elegida"])
        if p.get("quitar"):                       # tramos fuera, antes de medir
            dur = comun.duracion(src)
            keep, t0 = [], 0.0
            for x0, x1 in sorted(p["quitar"]):
                keep.append((t0, x0))
                t0 = x1
            keep.append((t0, dur))
            f, lab = [], ""
            for i, (x0, x1) in enumerate(keep):
                f.append(f"[0:v]trim={x0}:{x1},setpts=PTS-STARTPTS[v{i}]")
                f.append(f"[0:a]atrim={x0}:{x1},asetpts=PTS-STARTPTS,afade=t=in:d=0.004,"
                         f"afade=t=out:st={max(0, x1 - x0 - 0.004):.4f}:d=0.004[a{i}]")
                lab += f"[v{i}][a{i}]"
            f.append(lab + f"concat=n={len(keep)}:v=1:a=1[v][a]")
            q2 = f"{tmp}/q{k}.mov"
            comun.ff("-i", src, "-filter_complex", ";".join(f), "-map", "[v]", "-map", "[a]",
                     "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-c:a", "pcm_s16le", q2)
            src = q2
        sp = f"{tmp}/s{k}.mp4"
        extra = ["--proteger", f"{p['respetar'][0]}-{p['respetar'][1]}:9"] if p.get("respetar") else []
        r = subprocess.run([sys.executable, str(AQUI / "quitar_pausas.py"), src, sp, "--aire", str(cfg.get("aire", 0.015)),
                            "--min", str(cfg.get("min", 0.08)), "--borde", str(cfg.get("borde", 22)), *extra],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"✗ {p['elegida']}: {r.stderr[-400:]}")
        db, ref, xx = energia_de(sp, tmp)
        v = db > ref - 22
        on = next((i for i in range(len(v) - 4) if v[i:i + 4].all()), 0) / 100
        e = len(db) - 1
        while e > 0 and db[e] < ref - cfg.get("apagado", 24):      # la última palabra, apagada a −24 dB
            e -= 1
        # una «s» final es baja pero tiene la energía arriba de 3,5 kHz: se sigue mientras sea siseo (máx. 0,25 s)
        fr16 = np.fft.rfftfreq(320, 1 / 16000)
        k2 = e + 1
        while k2 < len(db) and k2 <= e + 25 and db[k2] > ref - 42 and k2 * 160 + 320 <= len(xx):
            P = np.abs(np.fft.rfft(xx[k2 * 160:k2 * 160 + 320] * np.hanning(320))) ** 2
            if P[fr16 >= 3500].sum() / (P.sum() + 1e-12) < 0.45:
                break
            k2 += 1
        e = k2 - 1
        b = e
        while b > 0 and db[b] < ref - 12:
            b -= 1
        fin = min(len(db) / 100, e / 100 + COLA)
        segs.append(dict(f=sp, a0=on, a1=fin, cae=(e - b) / 100, parte=p.get("parte", f"parte {k + 1}"),
                         toma=p["elegida"], suplentes=p.get("suplentes", []), pausas=r.stdout.split(" pausas")[0]))
    st, uniones = [0.0], []
    for k in range(1, len(segs)):
        prev = segs[k - 1]
        pk = partes[k].get("encima")
        enc = pk if pk is not None else prev["cae"] >= 0.20
        st.append(st[-1] + (prev["a1"] - prev["a0"]) - (ENC if enc else 0.0))
        uniones.append((st[-1], enc, prev["cae"]))
    R = 30.0
    Q = lambda x: round(x * R) / R
    ins, fc, mix = [], [], ""
    for k, s in enumerate(segs):
        ins += ["-i", s["f"]]
        d = s["a1"] - s["a0"]
        fc.append(f"[{k}:v]trim={s['a0']:.4f}:{s['a1']:.4f},setpts=PTS-STARTPTS+{Q(st[k]):.4f}/TB,"
                  f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps={R:g}[v{k}]")
        fc.append(f"[{k}:a]atrim={s['a0']:.4f}:{s['a1']:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.004,"
                  f"afade=t=out:st={max(0, d - 0.006):.4f}:d=0.006,adelay={int(round(st[k] * 1000))}:all=1[a{k}]")
        mix += f"[a{k}]"
    D = st[-1] + segs[-1]["a1"] - segs[-1]["a0"]
    fc.append(f"color=c=black:s=1080x1920:r={R:g}:d={D:.3f}[b]")
    last = "b"
    for k in range(len(segs)):
        # eof_action=repeat: si una toma acaba un cuadro antes de que entre la siguiente, no se ve negro
        fc.append(f"[{last}][v{k}]overlay=0:0:eof_action=repeat:enable='gte(t,{Q(st[k]):.4f})'[o{k}]")
        last = f"o{k}"
    if cfg.get("lut"):
        fc.append(f"[{last}]lut3d=file='{ruta(cfg['lut'])}',format=yuv420p[col]")
        last = "col"
    fc.append(f"{mix}amix=inputs={len(segs)}:normalize=0:duration=longest[a]")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    comun.ff(*ins, "-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "[a]", "-t", f"{D:.3f}",
             "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", OUT)
    for k, s in enumerate(segs):
        sup = f"  (suplentes: {', '.join(s['suplentes'])})" if s["suplentes"] else ""
        print(f"{st[k]:6.2f}  {s['parte']:14s} {s['toma'][:36]:36s} voz {s['a0']:.2f}→{s['a1']:.2f} · {s['pausas']} pausas fuera{sup}")
    for t, e, c in uniones:
        print(f"  unión en {t:6.2f} s: {'ENCIMADA 0,18 s' if e else 'pegada'} (la palabra anterior cae en {c:.2f} s) ← escúchala")
    print(f"✔ {OUT} · {D:.2f} s")


if __name__ == "__main__":
    main()
