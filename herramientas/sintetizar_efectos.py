#!/usr/bin/env python3
"""Hace efectos de sonido propios (sin derechos de nadie): risers que no tapan la voz, woosh y ding.

  .venv/bin/python herramientas/sintetizar_efectos.py [--carpeta material/03-musica-y-efectos]

Escribe risers/riser-NN-<nombre>.wav y efectos/{woosh,ding}-N.wav (44,1 kHz, estéreo, pico −1 dBFS).

Por qué así (🟢 medido en el espectrograma de un reel de referencia): un riser que no tapa la voz esquiva la banda
de 200 Hz a 3 kHz. Son tres capas: un retumbo grave que crece (20–150 Hz), un tono suave (~800 Hz) y un siseo de
agudos (3–10 kHz). Cada riser termina en su punto alto (el final del archivo): se recorta POR DELANTE («desde» en
mezcla.json) para que el punto alto caiga justo al terminar la frase del gancho.
"""
import argparse
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

SR = 44100


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--carpeta", default=str(comun.MATERIAL / "03-musica-y-efectos"))
    a = ap.parse_args()
    import numpy as np
    rng = np.random.default_rng(7)
    base = Path(a.carpeta)

    def banda(x, lo, hi):
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(len(x), 1 / SR)
        m = np.ones_like(f)
        if lo:
            m *= 1 / (1 + (lo / np.maximum(f, 1)) ** 8)
        if hi:
            m *= 1 / (1 + (f / hi) ** 8)
        return np.fft.irfft(X * m, len(x))

    norm = lambda x: x / (np.sqrt(np.mean(x ** 2)) + 1e-12)
    curva = lambda n, p: np.linspace(0, 1, n) ** p

    def retumbo(d, f0=38, f1=70, p=2.2):
        n = int(d * SR)
        fase = 2 * np.pi * np.cumsum(np.linspace(f0, f1, n)) / SR
        seno = np.sin(fase) + 0.35 * np.sin(2 * fase)
        ruido = norm(banda(rng.standard_normal(n), 20, 150))
        pulso = 0.75 + 0.25 * np.sin(2 * np.pi * np.cumsum(np.linspace(3, 11, n)) / SR)
        return (0.7 * seno + 0.6 * ruido) * pulso * curva(n, p)

    def siseo(d, bandas=((3000, 5500), (5500, 8500), (8500, 13000)), p=2.0):
        n = int(d * SR)
        y = np.zeros(n)
        for k, (lo, hi) in enumerate(bandas):
            env = curva(n, p) * np.clip((np.linspace(0, 1, n) - k * 0.22) / 0.5, 0, 1)
            y += norm(banda(rng.standard_normal(n), lo, hi)) * env
        return y

    def tono(d, f0=780, f1=820, p=1.2, vib=5.0):
        n = int(d * SR)
        t = np.arange(n) / SR
        fr = np.linspace(f0, f1, n) * (1 + 0.004 * np.sin(2 * np.pi * vib * t))
        fase = 2 * np.pi * np.cumsum(fr) / SR
        return (np.sin(fase) + 0.25 * np.sin(2 * fase)) * curva(n, p)

    def cierre(y, seco=0.006):
        n = int(seco * SR)
        y[-n:] *= np.linspace(1, 0, n)
        return y

    def guardar(carpeta, nombre, izq, der=None):
        der = izq if der is None else der
        stv = np.stack([izq, der], 1)
        stv *= 10 ** (-1 / 20) / (np.abs(stv).max() + 1e-12)
        n = int(0.005 * SR)
        stv[:n] *= np.linspace(0, 1, n)[:, None]
        destino = base / carpeta
        destino.mkdir(parents=True, exist_ok=True)
        r = destino / f"{nombre}.wav"
        with wave.open(str(r), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((stv * 32767).astype(np.int16).tobytes())
        print(f"{r}  {len(izq) / SR:.2f} s")

    par = lambda fn, *x, **k: (fn(*x, **k), fn(*x, **k))
    d = 1.6
    r, (s1, s2), tn = retumbo(d), par(siseo, d), tono(d)
    guardar("risers", "riser-01-referencia-1.6s", cierre(r + 0.30 * s1 + 0.20 * tn), cierre(r + 0.30 * s2 + 0.20 * tn))
    d = 2.0
    r, (s1, s2) = retumbo(d), par(siseo, d)
    guardar("risers", "riser-02-grave-y-aire-2.0s", cierre(r + 0.35 * s1), cierre(r + 0.35 * s2))
    guardar("risers", "riser-03-solo-grave-2.0s", cierre(retumbo(2.0, 34, 62, 2.6)))
    d = 2.5
    r, tn, (s1, s2) = retumbo(d), tono(d, 650, 950, 1.6, 6.5), par(siseo, d)
    guardar("risers", "riser-04-tono-que-sube-2.5s", cierre(r + 0.28 * tn + 0.22 * s1), cierre(r + 0.28 * tn + 0.22 * s2))
    # woosh: ruido que barre de grave a agudo y se va (0,5 s)
    n = int(0.5 * SR)
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    ruido = rng.standard_normal(n)
    w = np.zeros(n)
    for k, (lo, hi) in enumerate(((300, 1200), (1200, 4000), (4000, 9000))):
        w += norm(banda(ruido, lo, hi)) * np.clip(np.sin(np.linspace(0, np.pi, n) - k * 0.3), 0, 1) ** 2
    guardar("efectos", "woosh-1", w * env, np.roll(w * env, 220))
    # ding: dos senos con caída exponencial (0,9 s). Se mezcla SIEMPRE ≥ 24 dB bajo la voz
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    ding = (np.sin(2 * np.pi * 1318.5 * t) + 0.5 * np.sin(2 * np.pi * 2637 * t) + 0.2 * np.sin(2 * np.pi * 3955.5 * t)) * np.exp(-t * 6)
    guardar("efectos", "ding-1", ding)


if __name__ == "__main__":
    main()
