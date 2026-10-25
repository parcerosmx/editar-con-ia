#!/usr/bin/env python3
"""Mezcla efectos de sonido y música sobre un video sin que nada tape la voz, y deja el volumen de las redes.

  .venv/bin/python herramientas/mezclar.py mezcla.json SALIDA.mp4 [--aun-asi]

mezcla.json (ejemplo en ejemplos/mezcla.json):
  {"video": "proyectos/mi-video/con-subtitulos.mp4",   ← su audio es la voz
   "margen_db": 10,                                     ← cada efecto queda AL MENOS esto bajo la voz en su tramo
   "efectos": [{"archivo": "material/03-musica-y-efectos/risers/riser-01-referencia-1.6s.wav", "t": 0.0, "tipo": "riser"},
               {"archivo": "material/03-musica-y-efectos/efectos/woosh-1.wav", "t": 3.9, "nota": "cambio de toma"},
               {"archivo": "material/03-musica-y-efectos/efectos/ding-1.wav", "t": 12.4, "tipo": "ding"}],
   "musica": {"archivo": "material/03-musica-y-efectos/musica/cancion.mp3", "desde": 2.9, "t_in": 0.0, "t_out": 29.8,
              "bajo_voz_db": 18, "fade_in": 1.6, "curva": "exp", "fade_out": 1.0,
              "pausas": [{"a": 23.4, "b": 27.6, "db": -24}]},       ← la música se va mientras respira un chiste
   "lufs_final": -14}

Reglas que el código hace cumplir (🟡 lo que le funcionó a un restaurante; cámbialas en tu hoja de estilo):
  · 🔴 Dings y pings SIEMPRE ≥ 24 dB bajo la voz, aunque el json pida otra cosa: aturden el oído.
  · 🔴 Nunca dos risers pegados: si entre el final de uno y el inicio del otro hay menos de 3 s, se detiene
    (con --aun-asi sigue, si el dueño lo decidió). Si hay más de uno, el segundo queda 3 dB más bajo que el
    primero, y avisa si es el mismo archivo (tiene que ser de otro tipo).
  · Música 18 dB bajo la voz (21 en historias, 12 con voz en off continua). Efectos 10 dB.
  · Final a −14 LUFS (una voz a −21 suena ~5 dB más bajo que el video de al lado en el feed).
  · «tipo» se deduce del nombre del archivo si no se pone (riser, ding, ping, woosh…).
Claude no oye: el informe dice dónde suena cada cosa y cuánto pesa; si «suena bien» lo decide el dueño.
La música: libre de derechos o comprada (Pixabay, Mixkit, la biblioteca de la red social). Tres para elegir, siempre.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

DING_DB = 24             # un ding o ping nunca queda a menos de esto bajo la voz
SEPARACION_RISERS = 3.0  # segundos mínimos entre el final de un riser y el inicio del siguiente
BAJA_SEGUNDO_RISER = 3.0


def ruta(p):
    p = Path(os.path.expanduser(p))
    return p if p.is_absolute() else comun.RAIZ / p


def tipo_de(e):
    if e.get("tipo"):
        return e["tipo"].lower()
    nombre = Path(e["archivo"]).name.lower()
    for t in ("riser", "ding", "ping", "woosh", "whoosh", "swish", "pop"):
        if t in nombre:
            return "ding" if t == "ping" else t
    return "efecto"


def revisar_risers(efectos, largos):
    """Devuelve (errores, avisos) de la regla «nunca dos risers pegados»."""
    rs = sorted([(e["t"], e["t"] + largos[i], e, i) for i, e in enumerate(efectos) if tipo_de(e) == "riser"],
                key=lambda r: r[0])
    errores, avisos = [], []
    for (a0, a1, ea, _), (b0, b1, eb, _) in zip(rs, rs[1:]):
        hueco = b0 - a1
        if hueco < SEPARACION_RISERS:
            errores.append(f"dos risers pegados: uno termina en {a1:.2f} s y el otro empieza en {b0:.2f} s "
                           f"({hueco:.2f} s entre ellos; mínimo {SEPARACION_RISERS:g} s)")
        if Path(ea["archivo"]).name == Path(eb["archivo"]).name:
            avisos.append(f"los risers de {a0:.2f} s y {b0:.2f} s son el mismo archivo: el segundo debe ser de otro tipo")
    return errores, avisos, [r[3] for r in rs]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mezcla")
    ap.add_argument("salida")
    ap.add_argument("--aun-asi", action="store_true", help="seguir aunque haya dos risers pegados (sólo si el dueño lo decidió)")
    a = ap.parse_args()
    import numpy as np
    comun.exigir("ffmpeg", "ffprobe")
    cfg = json.load(open(a.mezcla, encoding="utf-8"))
    tmp = comun.carpeta_temporal()
    V = ruta(cfg["video"])
    M = cfg.get("margen_db", 10)
    db = lambda s: 20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9) if len(s) else -120
    voz = comun.audio_16k(V, Path(tmp) / "voz.wav")
    efectos = cfg.get("efectos", [])
    sonidos, largos = [], []
    for k, e in enumerate(efectos):
        f = ruta(e["archivo"])
        if not f.exists():
            sys.exit(f"✗ No existe {f}")
        s = comun.audio_16k(f, Path(tmp) / f"e{k}.wav", e.get("desde"))
        if e.get("dur"):
            s = s[:int(e["dur"] * 16000)]
        sonidos.append(s)
        largos.append(len(s) / 16000)
    errores, avisos, risers = revisar_risers(efectos, largos)
    for x in avisos:
        print("⚠️ " + x)
    if errores:
        for x in errores:
            print("⛔ " + x)
        if not a.aun_asi:
            sys.exit("✗ No se mezcló. Separa los risers (o quita uno). Si el dueño lo quiere así: --aun-asi")
    inputs, fc, labs, informe = ["-i", str(V)], [], ["[0:a]"], []
    nivel_primer_riser = None
    for k, (e, s) in enumerate(zip(efectos, sonidos)):
        f = ruta(e["archivo"])
        t0, t1 = e["t"], e["t"] + len(s) / 16000
        activo = s[np.abs(s) > np.abs(s).max() * 0.05] if len(s) and np.abs(s).max() > 0 else s
        nivel = db(activo) + 20 * np.log10(e.get("vol", 1.0))
        v = db(voz[int(t0 * 16000):int(t1 * 16000)])
        tipo = tipo_de(e)
        mg = e.get("margen_db", M)
        if tipo == "ding":
            mg = max(mg, DING_DB)
        g = e.get("vol", 1.0) * min(1.0, 10 ** ((v - mg - nivel) / 20))
        final = db(activo) + 20 * np.log10(max(g, 1e-6))
        if tipo == "riser":
            if nivel_primer_riser is None:
                nivel_primer_riser = final
            elif final > nivel_primer_riser - BAJA_SEGUNDO_RISER:
                baja = final - (nivel_primer_riser - BAJA_SEGUNDO_RISER)
                g *= 10 ** (-baja / 20)
                final -= baja
        informe.append(f"{t0:6.2f}s  {tipo:7s} {f.name[:26]:26s} vol→{g:.2f}  queda {v - final:4.1f} dB bajo la voz  {e.get('nota', '')}")
        inputs += (["-ss", str(e["desde"])] if e.get("desde") else []) + ["-i", str(f)]
        fc.append(f"[{k + 1}:a]aresample=48000,aformat=channel_layouts=stereo,volume={g:.4f}"
                  + (f",atrim=0:{e['dur']},afade=t=out:st={max(0, e['dur'] - 0.3):.3f}:d=0.3" if e.get("dur") else "")
                  + f",adelay={int(t0 * 1000)}:all=1[e{k}]")
        labs.append(f"[e{k}]")
    m = cfg.get("musica")
    if m:
        f = ruta(m["archivo"])
        dur = m["t_out"] - m["t_in"]
        s = comun.audio_16k(f, Path(tmp) / "m.wav", m.get("desde", 0), m.get("desde", 0) + dur)
        v = db(voz[int(m["t_in"] * 16000):int(m["t_out"] * 16000)])
        bajo = m.get("bajo_voz_db", 18)
        g = 10 ** ((v - bajo - db(s)) / 20)
        informe.append(f"{m['t_in']:6.2f}s  música  {f.name[:26]:26s} desde {m.get('desde', 0)} s · queda {bajo} dB bajo la voz")
        pausas = ""
        for p in m.get("pausas", []):
            r = p.get("rampa", 0.25)
            G = 10 ** (p.get("db", -24) / 20)
            p0, p1 = p["a"] - m["t_in"] - r, p["b"] - m["t_in"] + r
            pausas += f"volume='1-{1 - G:.4f}*clip(min((t-{p0:.3f})/{r},({p1:.3f}-t)/{r}),0,1)':eval=frame,"
        k = len(labs)
        inputs += ["-ss", str(m.get("desde", 0)), "-t", f"{dur:.3f}", "-i", str(f)]
        fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,volume={g:.4f},"
                  f"afade=t=in:d={m.get('fade_in', 0.4)}:curve={m.get('curva', 'tri')},"
                  f"afade=t=out:st={max(0, dur - m.get('fade_out', 1.0)):.3f}:d={m.get('fade_out', 1.0)},{pausas}"
                  f"adelay={int(m['t_in'] * 1000)}:all=1[mu]")
        labs.append("[mu]")
    lufs = cfg.get("lufs_final", -14)
    norm = f",loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000" if lufs is not None else ""
    fc.append("".join(labs) + f"amix=inputs={len(labs)}:normalize=0:duration=first,alimiter=limit=0.95:level=false{norm}[a]")
    comun.ff(*inputs, "-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[a]", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", a.salida)
    r = subprocess.run(["ffmpeg", "-i", a.salida, "-af", "loudnorm=print_format=summary", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    tot = [l.strip() for l in r.splitlines() if "Input Integrated" in l or "Input True Peak" in l]
    print("\n".join(informe))
    print("total: " + " · ".join(tot))
    print(f"✔ {a.salida} — escúchalo: Claude mide, pero no oye")


if __name__ == "__main__":
    main()
