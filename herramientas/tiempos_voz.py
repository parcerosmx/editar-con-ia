#!/usr/bin/env python3
"""El segundo de cada palabra, con su margen de error, para los subtítulos y los efectos.

  .venv/bin/python herramientas/tiempos_voz.py VIDEO [--ini 0] [--fin 45.0] [--prompt "arepas, tacos"]
        [--desplazar 0.6] [--json palabras.json]

Whisper NO da tiempos exactos por palabra: con la ventana corrida 0,6 s, la misma palabra se mueve hasta ±0,4 s
(🟢 medido: una palabra salió en 17,86, 18,07 y 18,21). Por eso:
  1 · corre Whisper TRES veces (la ventana empieza en ini−d, ini e ini+d) y por cada palabra da la mediana y el rango;
  2 · si el rango pasa de 0,3 s la marca con «?»: no fiarse; decidir con la energía o pidiendo que la escuchen;
  3 · imprime la energía cada 0,1 s: el hueco entre barras largas es la pausa entre palabras.
--json guarda [{"w": palabra, "t0": segundo}] para subtitulos.py. Se revisa a mano antes (nombres propios, el «o no»
de un error de dicción que no se subtitula). Sobre una canción no sirve palabra por palabra: subtítulos por verso.
"""
import argparse
import json
import re
import statistics
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in t if unicodedata.category(c) != "Mn"))


def correr(video, ini, fin, prompt, tmp):
    wav = Path(tmp) / f"v-{ini:.2f}.wav"
    audio = comun.audio_16k(video, wav, ini, fin)
    pal = [{"w": w, "t0": ini + a} for a, b, w in comun.whisper_palabras(wav, prompt=prompt or None)]
    return pal, audio


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--ini", type=float, default=0.0, help="segundo donde empieza (mejor al inicio de una frase)")
    ap.add_argument("--fin", type=float, help="segundo donde termina (por defecto, el final)")
    ap.add_argument("--prompt", default="", help="palabras que Whisper debe reconocer (platos, nombres)")
    ap.add_argument("--desplazar", type=float, default=0.6, help="cuánto se corre la ventana en las otras dos pasadas")
    ap.add_argument("--json", help="guardar las palabras con su segundo")
    a = ap.parse_args()
    import numpy as np
    comun.exigir("ffmpeg", "whisper-cli")
    fin = a.fin or comun.duracion(a.video)
    tmp = comun.carpeta_temporal()
    principal, audio = correr(a.video, a.ini, fin, a.prompt, tmp)
    otras = [correr(a.video, max(0, a.ini + k * a.desplazar), fin, a.prompt, tmp)[0] for k in (-1, 1)]
    salida = []
    print("PALABRA          mediana  rango(min–max)")
    for p in principal:
        tiempos = [p["t0"]]
        for lista in otras:
            cand = [q["t0"] for q in lista if norm(q["w"]) == norm(p["w"]) and abs(q["t0"] - p["t0"]) < 1.0]
            if cand:
                tiempos.append(min(cand, key=lambda t: abs(t - p["t0"])))
        med = statistics.median(tiempos)
        dudosa = "  ?" if max(tiempos) - min(tiempos) > 0.3 or len(tiempos) < 3 else ""
        print(f"{p['w']:<16} {med:7.2f}  {min(tiempos):.2f}–{max(tiempos):.2f}{dudosa}")
        salida.append({"w": p["w"], "t0": round(med, 2)})
    print("\nENERGÍA cada 0,1 s (dB): el hueco entre barras largas = pausa entre palabras")
    for i in range(int((fin - a.ini) * 10)):
        seg = audio[i * 1600:(i + 1) * 1600]
        if not len(seg):
            break
        db = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9)
        print(f"  {a.ini + i / 10:6.1f} {db:6.1f} {'#' * int(max(0, (db + 60) / 2))}")
    if a.json:
        Path(a.json).write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n✔ {a.json} ({len(salida)} palabras) — revísalo a mano antes de hacer los subtítulos")


if __name__ == "__main__":
    main()
