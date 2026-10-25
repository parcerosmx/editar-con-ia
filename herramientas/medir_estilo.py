#!/usr/bin/env python3
"""Mide el estilo de edición de uno o varios videos: lo que sí se puede contar con números.

  .venv/bin/python herramientas/medir_estilo.py VIDEO [VIDEO ...] [--json salida.json] [--hojas carpeta]

Por cada video:
  · RITMO      cuántos cortes hay y cuánto dura cada toma (mediana, la más corta, la más larga, la ráfaga del arranque)
  · CARA       qué parte del video sale una cara grande a cámara (Vision de macOS, en el cuadro del medio de cada toma)
  · VOZ        palabras por minuto, en qué segundo arranca la voz, las pausas entre frases, y si hay un fondo
               continuo (música o ruido) y a cuántos dB queda debajo de la voz
  · TEXTO      en qué parte del video hay texto en pantalla, a qué altura, de qué tamaño, si va en mayúsculas,
               y el texto de los primeros 4 s (el gancho de texto)
  · SONIDO     volumen final (LUFS) y pico
  · COLOR      luz, contraste, saturación y calidez promedio de las tomas
Y al final, la mediana de todos: eso es «tu estilo» en números.

Además deja, por video, una hoja con el cuadro del medio de cada toma, su segundo, cuánto dura y si la
contó como CARA o APOYO. Claude la mira para corregir lo que Vision no vio bien.

Lo que NO mide (se mira en las hojas o se le pregunta al dueño): la fuente de los subtítulos, si la música
«queda bien», el tono de la voz, qué tan antojable es la comida.
"""
import argparse
import json
import re
import statistics as st
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

CARA_MIN = 0.10        # una cara cuenta como «a cámara» si su caja mide al menos 10 % del alto del cuadro
UMBRAL_CORTE = 0.30    # 0–1: cuánto cambia la imagen para contarlo como corte (el mismo que /revisar-video)
MAX_TOMAS = 150        # para no mandar cientos de cuadros a Vision
INVENTADAS = ("suscr", "subtítulos", "subtitulos", "gracias por ver", "amara.org", "like y")


def mediana(v, nd=2):
    return round(st.median(v), nd) if v else None


def pct(v, q):
    if not v:
        return None
    s = sorted(v)
    return round(s[min(len(s) - 1, int(round(q * (len(s) - 1))))], 2)


def cortes(video, dur):
    """Segundos donde cambia el plano (filtro de escenas de ffmpeg sobre el video chico)."""
    pre, fi = comun.entrada(video)
    r = subprocess.run(["ffmpeg", "-v", "info", *pre, "-i", str(video), "-vf",
                        f"{fi},scale=180:-2,select='gt(scene,{UMBRAL_CORTE})',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    ts = sorted(float(x) for x in re.findall(r"pts_time:([0-9.]+)", r))
    limpios = []
    for t in ts:                                        # dos «cortes» a menos de 0,2 s son el mismo
        if 0.15 < t < dur - 0.15 and (not limpios or t - limpios[-1] > 0.2):
            limpios.append(t)
    return limpios


def cuadro(video, t, destino, ancho=360):
    pre, fi = comun.entrada(video)
    comun.ff(*pre, "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", f"{fi},scale={ancho}:-2", destino)
    return destino


def color(rutas):
    """Luz, contraste, saturación y calidez (0–255), promediados en los cuadros."""
    import numpy as np
    from PIL import Image
    luz, con, sat, cal = [], [], [], []
    for r in rutas:
        a = np.asarray(Image.open(r).convert("RGB")).astype(float)
        y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
        luz.append(y.mean()); con.append(y.std())
        sat.append((a.max(-1) - a.min(-1)).mean()); cal.append((a[..., 0] - a[..., 2]).mean())
    f = lambda v: round(float(np.mean(v)), 1) if v else None
    return {"luz": f(luz), "contraste": f(con), "saturacion": f(sat), "calidez": f(cal)}


def tonos_texto(ruta, caja):
    """Los dos tonos de la letra (aprox.): el claro y el oscuro dentro de la caja del texto.
    Con letra de contorno, uno es el relleno y el otro el contorno; se confirma mirando la hoja."""
    import numpy as np
    from PIL import Image
    im = Image.open(ruta).convert("RGB")
    w, h = im.size
    x0, y0, x1, y1 = int(caja[0] * w), int(caja[1] * h), int(caja[2] * w), int(caja[3] * h)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    a = np.asarray(im.crop((x0, y0, x1, y1))).reshape(-1, 3).astype(float)
    y = a @ [0.2126, 0.7152, 0.0722]
    hexa = lambda g: "#%02X%02X%02X" % tuple(int(v) for v in g.mean(0))
    return f"{hexa(a[y >= np.percentile(y, 85)])} / {hexa(a[y <= np.percentile(y, 15)])}"


def voz(video, tmp):
    """Palabras por minuto, arranque de la voz, pausas entre frases y el fondo bajo la voz."""
    import numpy as np
    wav = Path(tmp) / "a.wav"
    x = comun.audio_16k(video, wav)
    if not len(x):
        return {}
    db = comun.energia(x)
    if not len(db):
        return {}
    ref = float(np.percentile(db, 90))                     # la voz a volumen normal
    habla = db > ref - 20
    # pausas: tramos de ≥ 60 ms bajo ref−20 dB entre dos tramos con voz
    pausas, i, n = [], 0, len(db)
    while i < n:
        if not habla[i]:
            j = i
            while j < n and not habla[j]:
                j += 1
            if i > 0 and j < n and j - i >= 6:
                pausas.append((j - i) / 100)
            i = j
        else:
            i += 1
    fondo = float(np.percentile(db, 10))
    palabras = comun.whisper_palabras(wav)
    # Whisper inventa frases sobre música o silencio («Suscríbete», «Gracias por ver el video»): se quitan
    texto = " ".join(p[2] for p in palabras).lower()
    inventadas = [f for f in INVENTADAS if f in texto]
    con_voz = [p for p in palabras if re.search(r"\w", p[2])]
    if inventadas and len(con_voz) < 12:
        con_voz = []
    dur = len(x) / 16000
    habladas = [p for p in con_voz if p[1] - p[0] > 0]
    ppm = round(len(habladas) / (dur / 60)) if dur > 0 and habladas else 0
    inicio = round(habladas[0][0], 2) if habladas else None
    primeras = " ".join(p[2] for p in habladas if p[0] < 4.0)
    return {
        "palabras_por_minuto": ppm,
        "voz_arranca_en_s": inicio,
        "lo_que_dice_en_4s": primeras.strip(),
        "pausa_mediana_s": mediana(pausas),
        "pausa_mas_larga_s": round(max(pausas), 2) if pausas else 0,
        "pausas_de_mas_de_0_3s": sum(1 for p in pausas if p > 0.3),
        "fondo_bajo_la_voz_db": round(ref - fondo, 1),
        "hay_fondo_continuo": bool(ref - fondo < 30),
        "sin_voz_clara": not con_voz,
        "nota": ("No se oye voz clara (puede ser sólo música; Whisper inventa frases sobre música)." if not con_voz else"Hay un fondo continuo (música o ruido) a ~{:.0f} dB bajo la voz: las pausas medidas son aproximadas."
                 .format(ref - fondo) if ref - fondo < 30 else "Fondo casi en silencio: las pausas son confiables."),
    }


def volumen(video):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(video), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return {"lufs": float(i[-1]) if i else None, "pico_dbfs": float(p[-1]) if p else None}


def hoja(cuadros, destino):
    """Cuadro del medio de cada toma con su segundo, su duración y CARA/APOYO, 8 por fila."""
    from PIL import Image, ImageDraw
    if not cuadros:
        return None
    ims = [(Image.open(c["ruta"]).convert("RGB"), c) for c in cuadros]
    w = 180
    h = int(ims[0][0].height * w / ims[0][0].width)
    cols = 8
    filas = -(-len(ims) // cols)
    lienzo = Image.new("RGB", (w * min(cols, len(ims)), (h + 26) * filas), "white")
    d = ImageDraw.Draw(lienzo)
    for k, (im, c) in enumerate(ims):
        x, y = (k % cols) * w, (k // cols) * (h + 26)
        lienzo.paste(im.resize((w, h)), (x, y))
        etiqueta = f"{c['desde']:.1f}s {c['dura']:.1f}s {'CARA' if c['cara'] else 'apoyo'}"
        d.rectangle((x, y + h, x + w, y + h + 26), fill="black" if c["cara"] else "#444")
        d.text((x + 6, y + h + 7), etiqueta, fill="yellow" if c["cara"] else "white")
    lienzo.save(destino, quality=85)
    return str(destino)


def medir(video, carpeta_hojas):
    video = Path(video).expanduser().resolve()
    tmp = comun.carpeta_temporal()
    s = comun.sonda(video)
    dur = float(s["format"]["duration"])
    v = next((x for x in s["streams"] if x["codec_type"] == "video"), None)
    if not v:
        sys.exit(f"✗ {video.name} no tiene video.")
    cs = cortes(video, dur)
    bordes = [0.0] + cs + [dur]
    tomas = [(a, b) for a, b in zip(bordes, bordes[1:]) if b - a > 0.05]
    largos = [round(b - a, 2) for a, b in tomas]
    # cuadros del medio de cada toma (hasta MAX_TOMAS) para caras y color
    paso = max(1, -(-len(tomas) // MAX_TOMAS))
    elegidas = tomas[::paso]
    rutas = [cuadro(video, (a + b) / 2, Path(tmp) / f"m{k:03d}.png") for k, (a, b) in enumerate(elegidas)]
    # un cuadro por segundo para el texto en pantalla
    segs = [t + 0.5 for t in range(int(dur))][:90]
    rutas_txt = [cuadro(video, t, Path(tmp) / f"s{k:03d}.png", 540) for k, t in enumerate(segs)]
    vis = comun.vision(rutas + rutas_txt)
    cuadros, t_cara = [], 0.0
    for (a, b), r in zip(elegidas, rutas):
        caras = vis.get(str(r), {}).get("caras", [])
        grande = any(c[3] - c[1] >= CARA_MIN for c in caras)
        cuadros.append({"ruta": r, "desde": a, "dura": b - a, "cara": grande})
        if grande:
            t_cara += (b - a) * paso
    # texto en pantalla
    con_texto, alturas, centros, mayus, palabras_bloque, colores, gancho = 0, [], [], [], [], [], []
    for t, r in zip(segs, rutas_txt):
        txt = [x for x in vis.get(str(r), {}).get("textos", []) if len(x["t"].strip()) >= 2]
        if not txt:
            continue
        con_texto += 1
        for x in txt:
            c = x["caja"]
            alturas.append((c[3] - c[1]) * 1920)
            centros.append((c[1] + c[3]) / 2 * 1920)
            letras = [ch for ch in x["t"] if ch.isalpha()]
            if letras:
                mayus.append(sum(ch.isupper() for ch in letras) / len(letras))
            palabras_bloque.append(len(x["t"].split()))
            col = tonos_texto(r, c)
            if col:
                colores.append(col)
            if t < 4:
                gancho.append(x["t"])
    vista = bool(vis)
    medidas = {
        "video": video.name,
        "duracion_s": round(dur, 1),
        "formato": f"{v.get('width')}x{v.get('height')}",
        "ritmo": {
            "tomas": len(tomas),
            "toma_mediana_s": mediana(largos),
            "toma_corta_p10_s": pct(largos, 0.10),
            "toma_larga_p90_s": pct(largos, 0.90),
            "cortes_por_10s": round(len(cs) / dur * 10, 1) if dur else 0,
            "cortes_en_los_primeros_3s": sum(1 for c in cs if c < 3),
        },
        "cara": {
            "porcentaje_a_camara": round(100 * t_cara / dur) if vista and dur else None,
            "arranca_con_cara": cuadros[0]["cara"] if vista and cuadros else None,
            "nota": None if vista else "Vision de macOS no respondió: la cara se mide mirando la hoja.",
        },
        "texto": {
            "porcentaje_con_texto": round(100 * con_texto / len(segs)) if vista and segs else None,
            "altura_letra_px_en_1920": round(st.median(alturas)) if alturas else None,
            "centro_vertical_px_en_1920": round(st.median(centros)) if centros else None,
            "mayusculas": (None if not mayus else ("casi todo en MAYÚSCULAS" if st.median(mayus) > 0.8 else
                           "mezcla" if st.median(mayus) > 0.3 else "minúsculas normales")),
            "palabras_por_bloque": mediana(palabras_bloque, 1),
            "tonos_letra_claro_oscuro": st.mode(colores) if colores else None,
            "texto_en_los_primeros_4s": " / ".join(dict.fromkeys(gancho)) or None,
        },
        "voz": voz(video, tmp),
        "sonido": volumen(video),
        "color": color(rutas),
    }
    if carpeta_hojas:
        Path(carpeta_hojas).mkdir(parents=True, exist_ok=True)
        medidas["hoja"] = hoja(cuadros, Path(carpeta_hojas) / f"tomas-{video.stem[:40]}.jpg")
    return medidas


def resumen(todas):
    """La mediana de cada número entre todos los videos."""
    def junta(sec, k):
        vals = [m[sec].get(k) for m in todas if isinstance(m.get(sec), dict)]
        vals = [x for x in vals if isinstance(x, (int, float)) and not isinstance(x, bool)]
        return mediana(vals) if vals else None
    r = {}
    for sec in ("ritmo", "cara", "texto", "voz", "sonido", "color"):
        claves = {k for m in todas for k, x in (m.get(sec) or {}).items()
                  if isinstance(x, (int, float)) and not isinstance(x, bool)}
        r[sec] = {k: junta(sec, k) for k in sorted(claves)}
    r["duracion_s"] = mediana([m["duracion_s"] for m in todas], 1)
    return r


def imprimir(m):
    print(f"\n━━ {m['video']} · {m['duracion_s']} s · {m['formato']}")
    for sec in ("ritmo", "cara", "texto", "voz", "sonido", "color"):
        datos = {k: x for k, x in (m.get(sec) or {}).items() if x is not None}
        if datos:
            print(f"  {sec.upper():7} " + " · ".join(f"{k.replace('_', ' ')}: {x}" for k, x in datos.items()))
    if m.get("hoja"):
        print(f"  HOJA    {m['hoja']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("videos", nargs="+", help="archivos de video (para un link, primero /revisar-video lo baja)")
    p.add_argument("--json", help="dónde guardar las medidas (por defecto proyectos/_estilo/medidas.json)")
    p.add_argument("--hojas", help="carpeta para las hojas de tomas (por defecto proyectos/_estilo/)")
    a = p.parse_args()
    comun.exigir("ffmpeg", "ffprobe", "whisper-cli")
    carpeta = Path(a.hojas) if a.hojas else comun.proyecto("_estilo")
    todas = []
    for v in a.videos:
        print(f"· midiendo {Path(v).name}…", flush=True)
        m = medir(v, carpeta)
        imprimir(m)
        todas.append(m)
    salida = {"videos": todas}
    if len(todas) > 1:
        salida["mediana_de_todos"] = resumen(todas)
        print("\n━━ MEDIANA DE LOS", len(todas), "VIDEOS (tu estilo en números)")
        for sec, datos in salida["mediana_de_todos"].items():
            if isinstance(datos, dict):
                datos = {k: x for k, x in datos.items() if x is not None}
                print(f"  {sec.upper():7} " + " · ".join(f"{k.replace('_', ' ')}: {x}" for k, x in datos.items()))
            else:
                print(f"  {sec}: {datos}")
    destino = Path(a.json) if a.json else carpeta / "medidas.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"\n✔ {destino}")


if __name__ == "__main__":
    main()
