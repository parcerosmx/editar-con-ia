#!/usr/bin/env python3
"""Subtítulos palabra por palabra, dibujados con Pillow, y un .srt para CapCut o para la red.

  .venv/bin/python herramientas/subtitulos.py palabras.json CARPETA --video VIDEO [--salida CON_SUBS.mp4]
        [--fuente ruta.ttf] [--tam 60] [--color "#FFFFFF"] [--resaltar "#FFD84D"] [--contorno "#111111"]
        [--y 1250] [--maxw 760] [--max-palabras 4] [--mayusculas] [--pop 0] [--grandes 30,31]
        [--cortes 9.5,17.0] [--sin-subtitulo 0-3.5,20-22]

palabras.json: [{"w": "Hoy", "t0": 0.42}, ...] (de tiempos_voz.py, revisado a mano).
Escribe CARPETA/cap/00000.png … (una banda transparente por cuadro) y CARPETA/subtitulos.srt; con --salida,
además pega los subtítulos sobre el video.

Los valores por defecto salen de lo que le funcionó a un restaurante (🟡, ver estilo/ejemplo-mao.md); los tuyos
van en estilo/hoja-de-estilo.md y se pasan aquí:
  · 60 px, sin rebote (--pop 0), dentro de la zona segura (TikTok tapa ~200 px arriba y ~370 abajo en 1920)
  · máximo 4 palabras y 760 px por bloque; un bloque nunca termina en «de», «la», «que»…
  · --grandes: palabras que van más grandes DENTRO del subtítulo (el dato clave), en vez de un letrero aparte
  · --sin-subtitulo: tramos sin subtítulo (mientras hay un letrero o un logo: nunca tres letreros a la vez)
  · --resaltar: la palabra que se dice va de otro color (por defecto no: «entre más natural, mejor»)
El texto lo pone siempre un script, nunca un modelo de imagen (los modelos escriben mal).
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

FUENTES = ["/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"]
PALABRAS_FUNCION = {"de", "la", "el", "los", "las", "que", "y", "a", "al", "del", "con", "en", "se", "un", "una",
                    "lo", "es", "no", "nos", "va", "su", "sus", "por", "para", "mi", "tu"}
ANCHO, ALTO, K = 1080, 360, 2


def tramos(txt):
    out = []
    for it in filter(None, (txt or "").split(",")):
        a, b = it.split("-")
        out.append((float(a), float(b)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("palabras")
    ap.add_argument("carpeta")
    ap.add_argument("--video", required=True, help="el video (da la duración y los cuadros por segundo)")
    ap.add_argument("--salida", help="pegar los subtítulos sobre el video y guardarlo aquí")
    ap.add_argument("--fuente", help="archivo .ttf/.otf (por defecto una redonda y gruesa de la Mac)")
    ap.add_argument("--tam", type=int, default=60)
    ap.add_argument("--color", default="#FFFFFF")
    ap.add_argument("--resaltar", help="color de la palabra que se está diciendo (opcional)")
    ap.add_argument("--contorno", default="#111111")
    ap.add_argument("--grosor", type=int, default=6, help="grosor del contorno en px")
    ap.add_argument("--y", type=int, default=1250, help="altura del centro del subtítulo en 1920 (zona segura: 205–1550)")
    ap.add_argument("--maxw", type=int, default=760)
    ap.add_argument("--max-palabras", type=int, default=4)
    ap.add_argument("--mayusculas", action="store_true")
    ap.add_argument("--pop", type=float, default=0.0, help="segundos de rebote al entrar cada bloque (0 = sin rebote)")
    ap.add_argument("--grandes", default="", help="palabras que van más grandes, separadas por coma")
    ap.add_argument("--escala-grande", type=float, default=1.5)
    ap.add_argument("--cortes", default="", help="segundos donde empieza otra oración: un bloque nunca la cruza")
    ap.add_argument("--sin-subtitulo", default="", help="tramos a-b,c-d sin subtítulo")
    a = ap.parse_args()
    from PIL import Image, ImageDraw, ImageFont
    if not (205 <= a.y - a.tam // 2 and a.y + a.tam // 2 <= 1550):
        print("⚠️ el subtítulo queda fuera de la zona segura (y entre 205 y 1550): la interfaz de la red lo puede tapar")
    fuente = a.fuente or next((f for f in FUENTES if Path(f).exists()), None)
    if not fuente:
        sys.exit("✗ No encontré una fuente. Pasa una con --fuente ruta.ttf")
    dur = comun.duracion(a.video)
    fps, _ = comun.fps(a.video)
    vis = (lambda w: w.upper()) if a.mayusculas else (lambda w: w)
    grandes = {g.strip().upper() for g in a.grandes.split(",") if g.strip()}
    cortes = [float(c) for c in a.cortes.split(",") if c.strip()]
    mudos = tramos(a.sin_subtitulo)
    pal = [p for p in json.load(open(a.palabras, encoding="utf-8")) if not any(m0 <= p["t0"] < m1 for m0, m1 in mudos)]
    f1 = ImageFont.truetype(fuente, a.tam)
    fK = ImageFont.truetype(fuente, a.tam * K)
    fG = ImageFont.truetype(fuente, int(a.tam * K * a.escala_grande))
    for i, p in enumerate(pal):
        sig = pal[i + 1]["t0"] if i + 1 < len(pal) else p["t0"] + 0.6
        p["t1"] = min(sig, p["t0"] + 0.6)
    ancho = lambda ws: f1.getlength(" ".join(vis(p["w"]) for p in ws))
    es_funcion = lambda p: p["w"].lower().strip(",.?!;¿¡") in PALABRAS_FUNCION
    bloques, cur = [], []
    for p in pal:
        if cur and any(cur[-1]["t0"] < c <= p["t0"] for c in cortes):
            bloques.append(cur)
            cur = []
        elif cur and (len(cur) >= a.max_palabras or ancho(cur + [p]) > a.maxw or p["t0"] - cur[-1]["t0"] > 0.9):
            resto = []
            while len(cur) >= 2 and es_funcion(cur[-1]):
                resto.insert(0, cur.pop())
            bloques.append(cur)
            cur = resto
        cur.append(p)
        if p["w"][-1:] in ",.?!;" and len(cur) >= 2:
            bloques.append(cur)
            cur = []
    if cur:
        bloques.append(cur)
    tiempos = []
    for i, b in enumerate(bloques):
        ini, fin = b[0]["t0"] - 0.04, b[-1]["t1"] + 0.10
        if i + 1 < len(bloques):
            fin = min(fin, bloques[i + 1][0]["t0"] - 0.04)
        fin = min([fin] + [m0 for m0, m1 in mudos if b[-1]["t0"] < m0 < fin])
        tiempos.append((max(0, ini), fin))

    def banda(bloque, activo, esc):
        im = Image.new("RGBA", (ANCHO * K, ALTO * K), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        ws = [vis(p["w"]) for p in bloque]
        fs = [fG if w.upper().strip(",.!?¡¿") in grandes else fK for w in ws]
        esp = fK.getlength(" ")
        anchos = [f.getlength(w) for f, w in zip(fs, ws)]
        x = (ANCHO * K - (sum(anchos) + esp * (len(ws) - 1))) / 2
        base = ALTO * K / 2 + a.tam * K * 0.36
        for j, (w, an, f) in enumerate(zip(ws, anchos, fs)):
            col = a.resaltar if (a.resaltar and j == activo) else a.color
            d.text((x, base), w, font=f, fill=col, anchor="ls", stroke_width=a.grosor * K, stroke_fill=a.contorno)
            x += an + esp
        if esc != 1:
            r = im.resize((int(im.width * esc), int(im.height * esc)), Image.LANCZOS)
            im = Image.new("RGBA", im.size, (0, 0, 0, 0))
            im.alpha_composite(r, ((im.width - r.width) // 2, (im.height - r.height) // 2))
        return im.resize((ANCHO, ALTO), Image.LANCZOS)

    carpeta = Path(a.carpeta)
    (carpeta / "cap").mkdir(parents=True, exist_ok=True)
    for viejo in (carpeta / "cap").glob("*.png"):
        viejo.unlink()
    cache, total = {}, int(math.ceil(dur * fps))
    for n in range(total):
        t = n / fps
        k = next((i for i, (x0, x1) in enumerate(tiempos) if x0 <= t < x1), None)
        if k is None:
            clave = "vacio"
        else:
            b = bloques[k]
            activo = max([j for j, p in enumerate(b) if p["t0"] <= t] or [0]) if a.resaltar else -1
            u = 1.0 if a.pop <= 0 else min(1.0, (t - tiempos[k][0]) / a.pop)
            clave = (k, activo, 1.0 if u >= 1 else round(0.86 + 0.14 * (1 - (1 - u) ** 3), 2))
        destino = carpeta / "cap" / f"{n:05d}.png"
        if clave in cache:
            os.link(cache[clave], destino)
        else:
            (banda(bloques[clave[0]], clave[1], clave[2]) if clave != "vacio"
             else Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))).save(destino)
            cache[clave] = destino

    def srt_t(s):
        ms = int(round(s * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    with open(carpeta / "subtitulos.srt", "w", encoding="utf-8") as f:
        for i, (b, (x0, x1)) in enumerate(zip(bloques, tiempos), start=1):
            f.write(f"{i}\n{srt_t(x0)} --> {srt_t(x1)}\n{' '.join(p['w'] for p in b)}\n\n")
    print(f"{len(bloques)} bloques · {total} cuadros · {carpeta / 'subtitulos.srt'}")
    for b, (x0, x1) in zip(bloques, tiempos):
        print(f"{x0:6.2f}–{x1:5.2f}  {' '.join(vis(p['w']) for p in b)}")
    if a.salida:
        y0 = a.y - ALTO // 2
        comun.ff("-i", a.video, "-framerate", f"{fps}", "-i", carpeta / "cap" / "%05d.png", "-filter_complex",
                 f"[0:v][1:v]overlay=0:{y0}:eof_action=pass,format=yuv420p[v]", "-map", "[v]", "-map", "0:a?",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-c:a", "copy", "-movflags", "+faststart", a.salida)
        print(f"✔ {a.salida}")


if __name__ == "__main__":
    main()
