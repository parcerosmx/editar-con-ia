#!/usr/bin/env python3
"""Aprende TU color: compara un video sin color contra el mismo video con el color que tú le pusiste
(en CapCut, en el celular, donde sea) y lo deja como un LUT (.cube) que ffmpeg aplica igual a todo.

  .venv/bin/python herramientas/aprender_color.py ANTES.mp4 DESPUES.mp4 [--salida estilo/mi-color.cube]

Cómo se prepara (el dueño hace sólo esto): toma 5–10 clips variados (comida, caras, el local), júntalos
en un solo video, expórtalo SIN color (ANTES) y luego con tu color, sin mover ni recortar nada (DESPUES).
Los dos tienen que durar lo mismo: así cada cuadro de uno tiene su par exacto en el otro.

Qué hace: toma ~40 pares de cuadros, separa 1 de cada 4 para probar, ajusta una curva de color
RGB→RGB (polinomio de 3.er grado), mide el error en los cuadros que NO vio y escribe el LUT 33³.
También calcula cuánto enfoque (unsharp) agregaste. Imprime el filtro listo para ffmpeg.

Lo aprendido con un restaurante (🟢 medido): el «color inteligente» de CapCut resultó ser UN preset
global, no un ajuste toma por toma (error 7,7/255 contra 17,5 sin corregir). Por eso un LUT alcanza.
⚠️ Un LUT sirve para la luz con la que se aprendió: con sol directo puede quemar. Se aplica UNA vez;
nunca se apilan filtros de color encima (la comida se pasa a rojo).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

W, H = 270, 480


def cuadro(f, t, tmp):
    import numpy as np
    from PIL import Image
    o = Path(tmp) / "f.png"
    pre, fi = comun.entrada(f)
    comun.ff(*pre, "-ss", f"{t:.3f}", "-i", f, "-frames:v", "1", "-vf", f"{fi},scale={W}:{H}", o)
    return np.asarray(Image.open(o).convert("RGB")).astype(float) / 255


def rasgos(a):
    import numpy as np
    r, g, b = a[:, 0], a[:, 1], a[:, 2]
    return np.stack([np.ones_like(r), r, g, b, r * r, g * g, b * b, r * g, r * b, g * b, r ** 3, g ** 3, b ** 3,
                     r * r * g, r * r * b, g * g * r, g * g * b, b * b * r, b * b * g, r * g * b], 1)


def ajustar(O, C, idx, rng):
    import numpy as np
    A, B = O[idx].reshape(-1, 3), C[idx].reshape(-1, 3)
    k = rng.choice(len(A), min(len(A), 300000), replace=False)
    return np.linalg.lstsq(rasgos(A[k]), B[k], rcond=None)[0]


def error(M, O, C, idx):
    import numpy as np
    return float(np.abs(np.clip(rasgos(O[idx].reshape(-1, 3)) @ M, 0, 1) - C[idx].reshape(-1, 3)).mean() * 255)


def escribir_cube(M, ruta, n=33):
    import numpy as np
    g = np.linspace(0, 1, n)
    lineas = [f"LUT_3D_SIZE {n}"]
    for b in g:
        for gg in g:
            for v in np.clip(rasgos(np.stack([g, np.full(n, gg), np.full(n, b)], 1)) @ M, 0, 1):
                lineas.append(f"{v[0]:.5f} {v[1]:.5f} {v[2]:.5f}")
    Path(ruta).write_text("\n".join(lineas) + "\n", encoding="utf-8")


def detalle(f, vf, dur):
    import numpy as np
    import subprocess
    o = subprocess.run([comun.ffmpeg(), "-v", "error", "-ss", str(dur * 0.2), "-t", str(min(12, dur * 0.6)), "-i", str(f),
                        "-vf", vf + ",scale=540:960,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    a = np.frombuffer(o, np.uint8).reshape(-1, 960, 540).astype(float)
    return np.abs(np.diff(a, axis=1)).mean() + np.abs(np.diff(a, axis=2)).mean()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("antes", help="el video sin color")
    p.add_argument("despues", help="el MISMO video con tu color (misma duración)")
    p.add_argument("--salida", default=str(comun.ESTILO / "mi-color.cube"), help="dónde guardar el LUT")
    p.add_argument("--cuadros", type=int, default=40, help="cuántos pares de cuadros usar (40)")
    a = p.parse_args()
    import numpy as np
    comun.exigir("ffmpeg", "ffprobe")
    d0, d1 = comun.duracion(a.antes), comun.duracion(a.despues)
    if abs(d0 - d1) > 0.5:
        sys.exit(f"✗ No duran lo mismo ({d0:.1f} s y {d1:.1f} s). Exporta los dos sin mover ni recortar nada.")
    tmp = comun.carpeta_temporal()
    ts = np.linspace(0.3, min(d0, d1) - 0.3, a.cuadros)
    O = np.array([cuadro(a.antes, t, tmp) for t in ts])
    C = np.array([cuadro(a.despues, t, tmp) for t in ts])
    rng = np.random.default_rng(1)
    prueba = np.zeros(len(ts), bool)
    prueba[::4] = True
    M = ajustar(O, C, ~prueba, rng)
    e_nv = error(M, O, C, prueba)
    e0 = float(np.abs(O[prueba] - C[prueba]).mean() * 255)
    M = ajustar(O, C, np.ones(len(ts), bool), rng)
    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    escribir_cube(M, salida)
    ref = detalle(a.despues, "null", d1)
    mejor = (9.0, 0.0)
    for amt in (0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8):
        vf = f"lut3d=file='{comun.ruta_filtro(salida)}'" + (f",unsharp=5:5:{amt}:5:5:0" if amt else "")
        mejor = min(mejor, (abs(detalle(a.antes, vf, d0) / ref - 1), amt))
    la, lb = O.mean(-1), C.mean(-1)
    cambio = {
        "luz": round(float(lb.mean() - la.mean()), 3),
        "contraste": round(float(lb.std() - la.std()), 3),
        "saturacion": round(float((C.max(-1) - C.min(-1)).mean() - (O.max(-1) - O.min(-1)).mean()), 3),
        "calidez": round(float((C[..., 0] - C[..., 2]).mean() - (O[..., 0] - O[..., 2]).mean()), 3),
    }
    filtro = f"lut3d=file='{comun.ruta_filtro(salida)}'" + (f",unsharp=5:5:{mejor[1]}:5:5:0" if mejor[1] else "")
    info = {"lut": str(salida), "unsharp": mejor[1], "error_sin_corregir": round(e0, 1),
            "error_con_tu_color_en_cuadros_no_vistos": round(e_nv, 1), "cambio": cambio, "filtro_ffmpeg": filtro}
    salida.with_suffix(".json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"sin corregir {e0:.1f}/255 · con tu color aprendido, en cuadros que no vio: {e_nv:.1f}/255")
    print("cambio (+ = más):", " · ".join(f"{k} {v:+.3f}" for k, v in cambio.items()))
    if e_nv > e0 * 0.7:
        print("⚠️ El color aprendido no explica bien tu edición: quizá cambiaste el color toma por toma. "
              "Mejor aplica tu color en tu app y aquí no se toca.")
    print(f"✔ {salida}\n  filtro para ffmpeg: {filtro}")


if __name__ == "__main__":
    main()
