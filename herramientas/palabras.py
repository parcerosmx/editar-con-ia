#!/usr/bin/env python3
"""Dónde empieza y termina cada palabra, con precisión de centésimas (Whisper solo corre hasta ±0,4 s).

  .venv/bin/python herramientas/palabras.py bordes  VIDEO t1 t2 ...       qué se oye 1 s antes y 1 s después de cada punto
  .venv/bin/python herramientas/palabras.py inicio  VIDEO a b fin         busca los bajones de voz entre a y b y transcribe
                                                                         desde cada uno hasta «fin»: el primero que arranca
                                                                         con la palabra buscada es su inicio
  .venv/bin/python herramientas/palabras.py energia VIDEO a b             volumen cada 10 ms: se corta donde la voz baja sola
  .venv/bin/python herramientas/palabras.py empalme VIDEO a1:b1 a2:b2 ... arma el audio con esos tramos (fundidos de 3–4 ms)
                                                                         y lo transcribe, para probar un empalme ANTES de montarlo

Regla: si una palabra decide algo, se le pide al dueño que la escuche, con su segundo. Claude no oye el tono.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("orden", choices=["bordes", "inicio", "energia", "empalme"])
    ap.add_argument("video")
    ap.add_argument("valores", nargs="+", help="segundos o tramos, según la orden")
    a = ap.parse_args()
    import numpy as np
    comun.exigir("ffmpeg", "whisper-cli")
    tmp = comun.carpeta_temporal()
    base = Path(tmp) / "v.wav"
    x = comun.audio_16k(a.video, base)

    def db(sig, t, d=0.01):
        s = sig[int(t * 16000):int((t + d) * 16000)]
        return 20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9) if len(s) else -120

    def oye(desde=None, hasta=None, fuente=base):
        g = Path(tmp) / "t.wav"
        comun.audio_16k(fuente, g, desde, hasta)
        return comun.whisper_texto(g)

    if a.orden == "bordes":
        for t in map(float, a.valores):
            print(f"{t:6.2f}  antes: «{oye(max(0, t - 1), t)}»   después: «{oye(t, t + 1)}»")
    elif a.orden == "inicio":
        i0, i1, fin = map(float, a.valores[:3])
        ts = np.arange(i0, i1, 0.01)
        e = np.array([db(x, t, 0.02) for t in ts])
        for i in range(2, len(e) - 2):
            if e[i] == e[i - 2:i + 3].min() and e[i] < -30:
                print(f"{ts[i]:.2f} → «{oye(round(ts[i], 2), fin)}»")
    elif a.orden == "energia":
        i0, i1 = map(float, a.valores[:2])
        print(" ".join(f"{t:.2f}:{db(x, t):.0f}" for t in np.arange(i0, i1, 0.01)))
    else:
        tramos = [tuple(map(float, p.split(":"))) for p in a.valores]
        fc, lab = [], ""
        for k, (s0, s1) in enumerate(tramos):
            fc.append(f"[0:a]atrim={s0}:{s1},asetpts=PTS-STARTPTS,afade=t=in:d=0.003,"
                      f"afade=t=out:st={s1 - s0 - 0.004:.4f}:d=0.004[a{k}]")
            lab += f"[a{k}]"
        o = Path(tmp) / "e.wav"
        comun.ff("-i", base, "-filter_complex", ";".join(fc) + ";" + lab + f"concat=n={len(tramos)}:v=0:a=1", o)
        print("se oye: «" + oye(fuente=o) + "»")
        y = comun.audio_16k(o, Path(tmp) / "e2.wav")
        acc = 0.0
        for s0, s1 in tramos[:-1]:
            acc += s1 - s0
            print(f"  unión en {acc:.2f}: " + " ".join(f"{t:.2f}:{db(y, t):.0f}"
                                                      for t in np.arange(max(0, acc - 0.06), acc + 0.06, 0.01)))


if __name__ == "__main__":
    main()
