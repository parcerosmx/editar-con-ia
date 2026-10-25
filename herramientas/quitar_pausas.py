#!/usr/bin/env python3
"""Quita las pausas de pensar de una toma a cámara: cero espacios muertos entre palabras.

  .venv/bin/python herramientas/quitar_pausas.py VIDEO SALIDA.mp4 [--desde 0.4] [--hasta 37.4]
        [--min 0.20] [--aire 0.03] [--borde 28] [--proteger 3.0-6.5:0.4] [--lut estilo/mi-color.cube]

  · recorta [desde, hasta] (el arranque y el final muertos)
  · busca silencios (16 dB bajo la voz, ≥0,10 s) que caen ENTRE dos palabras (Whisper dice dónde están las
    palabras). Los de adentro de una palabra son consonantes (p, t, c) y no se cortan
  · corta los de ≥ --min, dejando --aire a cada lado (0,03 → ~0,06 s entre palabras: «la voz nunca se calla»)
  · --borde 28: cada corte se encoge hasta que sus dos orillas caigan en silencio de verdad, para no comerse
    el final suave de una palabra (lección pagada: «te comiste alguna palabra»)
  · --proteger a-b:min: en ese tramo sólo se cortan silencios de al menos «min» (una pausa a propósito)
  · escribe SALIDA.json con «saltos»: dónde quedó cada corte en el video nuevo. Son el borde exacto entre
    dos palabras, mejor que los tiempos de Whisper (que corren hasta ±0,4 s): ahí se pegan las tomas de apoyo.
Los cortes se notan como un brinco en la imagen; las tomas de apoyo los tapan.
Nunca se corta con la voz a todo volumen: los cortes van en silencio, con fundidos de 3–4 ms.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402


def silencios(db, ref, bajo=16, minimo=10):
    low = db < ref - bajo
    out, i, n = [], 0, len(db)
    while i < n:
        if low[i]:
            j = i
            while j < n and low[j]:
                j += 1
            if j - i >= minimo:
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("salida")
    ap.add_argument("--desde", type=float, default=0.0, help="primer segundo que se usa")
    ap.add_argument("--hasta", type=float, help="último segundo que se usa")
    ap.add_argument("--min", type=float, default=0.20, help="silencio mínimo que se corta, en s (0,20)")
    ap.add_argument("--aire", type=float, default=0.03, help="aire que queda a cada lado del corte, en s (0,03)")
    ap.add_argument("--borde", type=float, default=28, help="dB bajo la voz que cuenta como silencio en las orillas (28; 0 = no revisar)")
    ap.add_argument("--proteger", default="", help="«a-b:min,…» segundos del video original donde sólo se cortan silencios ≥ min")
    ap.add_argument("--lut", help="un .cube para aplicar el color de una vez (opcional)")
    a = ap.parse_args()
    import numpy as np
    comun.exigir("ffmpeg", "ffprobe", "whisper-cli")
    tmp = comun.carpeta_temporal()
    D = comun.duracion(a.video)
    h = a.hasta or D
    wav = Path(tmp) / "a.wav"
    x = comun.audio_16k(a.video, wav, a.desde, h)
    db = comun.energia(x)
    n = len(db)
    ref = float(np.median(db[db > np.percentile(db, 40)]))
    sil = silencios(db, ref)
    palabras = comun.whisper_palabras(wav)
    bordes_palabra = [palabras[k][1] for k in range(len(palabras) - 1)]
    prot = []
    for it in filter(None, a.proteger.split(",")):
        r, m = (it.split(":") + ["9"])[:2]
        p0, p1 = map(float, r.split("-"))
        prot.append((p0, p1, float(m)))
    cortes = []
    for s0, s1 in sil:
        if s1 - s0 < a.min or s0 < 0.05 or s1 > h - a.desde - 0.05:      # ni el arranque ni la cola
            continue
        if any(p0 <= a.desde + s0 <= p1 and s1 - s0 < pm for p0, p1, pm in prot):
            continue
        if any(s0 - 0.25 <= b <= s1 + 0.25 for b in bordes_palabra):
            cortes.append((s0 + a.aire, s1 - a.aire))
    if a.borde:
        nivel = lambda t: db[min(n - 1, max(0, int(round(t * 100))))]
        seguros = []
        for c0, c1 in cortes:
            while c0 < c1 and max(nivel(c0), nivel(c0 - 0.01)) > ref - a.borde:
                c0 += 0.01
            while c1 > c0 and max(nivel(c1), nivel(c1 + 0.01)) > ref - a.borde:
                c1 -= 0.01
            if c1 - c0 >= 0.05:
                seguros.append((c0, c1))
        cortes = seguros
    R, fr = comun.fps(a.video)
    q = lambda t: round(t * R) / R
    tramos, t = [], a.desde
    for c0, c1 in cortes:
        tramos.append((q(t), q(a.desde + c0)))
        t = a.desde + c1
    tramos.append((q(t), q(h)))
    pre, fi = comun.entrada(a.video)
    fc = [f"[0:v]{fi},format=yuv420p,split={len(tramos)}" + "".join(f"[i{k}]" for k in range(len(tramos)))]
    lab = ""
    for k, (s0, s1) in enumerate(tramos):
        d = s1 - s0
        fc.append(f"[i{k}]trim={s0:.4f}:{s1:.4f},setpts=PTS-STARTPTS[v{k}]")
        fc.append(f"[0:a]atrim={s0:.4f}:{s1:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.003,"
                  f"afade=t=out:st={max(0, d - 0.004):.4f}:d=0.004[a{k}]")
        lab += f"[v{k}][a{k}]"
    color = f",lut3d=file='{comun.ruta_filtro(os.path.abspath(a.lut))}'" if a.lut else ""
    fc.append(lab + f"concat=n={len(tramos)}:v=1:a=1[vc][a]")
    fc.append(f"[vc]format=yuv420p{color}[v]")
    comun.ff(*pre, "-i", a.video, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", a.salida)
    saltos, acc = [], 0.0
    for k in range(len(tramos) - 1):
        acc += tramos[k][1] - tramos[k][0]
        saltos.append(round(acc, 3))
    Path(os.path.splitext(a.salida)[0] + ".json").write_text(encoding="utf-8", data=json.dumps(
        {"fuente": a.video, "tramos_fuente": tramos, "saltos": saltos, "fps": fr,
         "nota": "saltos = borde exacto entre dos palabras en la SALIDA; ahí se pegan los cambios de toma"}, indent=1))
    quitado = sum(c1 - c0 for c0, c1 in cortes)
    print(f"{len(cortes)} pausas cortadas, {quitado:.2f} s menos · dura {acc + tramos[-1][1] - tramos[-1][0]:.2f} s")
    if saltos:
        print("saltos en: " + ", ".join(f"{s:.2f}" for s in saltos))


if __name__ == "__main__":
    main()
