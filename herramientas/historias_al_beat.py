#!/usr/bin/env python3
"""Arma una historia de Instagram (1080×1920, ~15–20 s): tomas cortadas AL BEAT de una canción y un texto fijo arriba.

  .venv/bin/python herramientas/historias_al_beat.py historia.json [--hoja]

historia.json (ejemplo en ejemplos/historia.json):
  {"nombre": "ya-abrimos",
   "tomas": [{"archivo": "material/01-tomas-de-apoyo/IMG_0412.MOV", "t": 3.2, "beats": 4, "x": 0.5, "zoom": 1.0}, ...],
   "cancion": {"archivo": "material/03-musica-y-efectos/musica/cancion.mp3", "desde": 12.0},
   "texto": {"lineas": ["Ya abrimos", "hoy hay arepas"], "y": 300, "tam": 78},
   "cierre": {"imagen": "material/00-finales/mi-logo.png", "beats": 4, "lineas": ["Lun a sáb · 1 a 10 pm"]},
   "lut": "estilo/mi-color.cube"}

  · «t» es el segundo donde la acción YA está pasando (el queso se estira, el jugo cae), nunca el «antes»
  · cada toma dura «beats» golpes de la canción (o «seg», que se redondea a golpes enteros)
  · se mide el pulso de la canción y la música arranca EN un golpe: cada corte cae en un beat
  · si una toma tiene un corte adentro, se corre la entrada para no meter un parpadeo
  · la interfaz de las historias tapa ~250 px arriba y ~330 abajo: el texto va desde y=270
  · audio: sólo la canción, a −14 LUFS, con fundido de salida
La canción tiene que ser libre de derechos o comprada; si la historia va a llevar la música de Instagram,
arma sin canción (quita «cancion» y pon "bpm": 120) y ponla al subirla.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

W, H, FPS = 1080, 1920, 30
FUENTES = ["/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"]


def ruta(p):
    p = Path(os.path.expanduser(p))
    return p if p.is_absolute() else comun.RAIZ / p


def pulso(archivo, desde, bpm_max=150, largo=40):
    """Tempo y fase de la canción (flujo espectral + autocorrelación). Devuelve (bpm, segundos por golpe, fase)."""
    import numpy as np
    sr, hop = 22050, 512
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(desde), "-t", str(largo), "-i", str(archivo), "-ac", "1",
                          "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    y = np.frombuffer(pcm, np.float32)
    n = (len(y) - 2048) // hop
    fr = np.stack([y[i * hop:i * hop + 2048] * np.hanning(2048) for i in range(n)])
    S = np.log1p(30 * np.abs(np.fft.rfft(fr, axis=1)))
    env = np.maximum(0, np.diff(S, axis=0)).sum(1)
    env = (env - env.mean()) / (env.std() + 1e-9)
    fps = sr / hop
    ac = np.correlate(env, env, "full")[len(env) - 1:]
    lags = np.arange(len(ac))
    bpm = 60 * fps / np.maximum(lags, 1)
    ok = (bpm >= 70) & (bpm <= bpm_max)
    peso = np.exp(-0.5 * (np.log2(bpm / 115) / 0.9) ** 2)        # prefiere tempos de baile (~115)
    lag = int(lags[ok][np.argmax((ac * peso)[ok])])
    per = lag / fps
    fases = [env[np.arange(p, len(env), lag)].sum() for p in range(lag)]
    return 60 / per, per, int(np.argmax(fases)) / fps


def cortes_en(f, t, d):
    pre, fi = comun.entrada(f)
    r = subprocess.run(["ffmpeg", "-v", "info", *pre, "-ss", f"{t:.3f}", "-t", f"{d:.3f}", "-i", str(f), "-vf",
                        f"{fi},scale=160:-2,select='gt(scene,0.25)',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return [t + float(x) for x in re.findall(r"pts_time:([0-9.]+)", r) if 0.05 < float(x) < d - 0.05]


def ventana_limpia(f, t, d, dur):
    for _ in range(3):
        cs = cortes_en(f, t, d)
        if not cs:
            return t
        t2 = cs[-1] + 0.08
        t = t2 if t2 + d <= dur - 0.05 else max(0, cs[0] - 0.08 - d)
    return t


def capa_texto(lineas, y, tam, extra=None):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if extra is not None:
        im.alpha_composite(extra)
    if not lineas:
        return im
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(next(x for x in FUENTES if Path(x).exists()), tam)
    for i, l in enumerate(lineas):
        w = d.textlength(l, font=f)
        x0, y0 = (W - w) / 2, y + i * int(tam * 1.35)
        d.rounded_rectangle([x0 - 22, y0 - 10, x0 + w + 22, y0 + tam * 1.15], 16, fill=(255, 255, 255, 235))
        d.text((x0, y0), l, font=f, fill=(20, 20, 20))
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--hoja", action="store_true", help="además, hoja de cuadros del resultado")
    a = ap.parse_args()
    import numpy as np
    from PIL import Image
    comun.exigir("ffmpeg", "ffprobe")
    sp = json.load(open(a.spec, encoding="utf-8"))
    nombre = sp.get("nombre", Path(a.spec).stem)
    carpeta = comun.proyecto("historias") / nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    tmp = comun.carpeta_temporal()
    can = sp.get("cancion")
    if can:
        arch = ruta(can["archivo"])
        bpm, per, fase = pulso(arch, can.get("desde", 0), sp.get("bpm_max", 150))
        desde = can.get("desde", 0) + fase
    else:
        bpm = sp.get("bpm", 120)
        per, desde = 60 / bpm, 0
    nb = lambda x: x["beats"] if "beats" in x else max(1, round(x.get("seg", 2.0) / per))
    cierre = sp.get("cierre")
    beats = [nb(t) for t in sp["tomas"]] + ([nb(cierre)] if cierre else [])
    marcas = np.cumsum([0] + beats) * per
    frames = np.round(marcas * FPS).astype(int)
    dur = frames[-1] / FPS
    print(f"{nombre}: {bpm:.0f} bpm, un golpe cada {per:.3f} s · {dur:.1f} s")
    lut = f",lut3d=file='{ruta(sp['lut'])}'" if sp.get("lut") else ""
    tomas = list(sp["tomas"]) + ([cierre.get("toma", sp["tomas"][-1])] if cierre else [])
    segs = []
    for i, tm in enumerate(tomas):
        f = ruta(tm["archivo"])
        nfr = int(frames[i + 1] - frames[i])
        vel = tm.get("vel", 1.0)
        d_src = nfr / FPS * vel
        dur_t = comun.duracion(f)
        if d_src > dur_t - 0.15:
            vel = (dur_t - 0.15) / (nfr / FPS)
            d_src = nfr / FPS * vel
            print(f"   ⚠️ {f.name} es corta: va a {vel:.2f}×")
        t = ventana_limpia(f, min(max(0.0, tm.get("t", 0.0)), max(0, dur_t - d_src - 0.05)), d_src, dur_t)
        z, x, y = tm.get("zoom", 1.0), tm.get("x", 0.5), tm.get("y", 0.5)
        pre, fi = comun.entrada(f)
        o = Path(tmp) / f"s{i:02d}.mp4"
        comun.ff(*pre, "-ss", f"{t:.3f}", "-i", f, "-vf",
                 f"{fi},setpts=(PTS-STARTPTS)/{vel},fps={FPS},scale={int(W * z)}:{int(H * z)}:force_original_aspect_ratio=increase,"
                 f"crop={W}:{H}:(iw-{W})*{x}:(ih-{H})*{y}{lut},format=yuv420p",
                 "-frames:v", nfr, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-r", FPS, o)
        segs.append(o)
        print(f"   {marcas[i]:5.2f}s  {f.name[:30]:30s} entra en {t:5.2f}  {nfr / FPS:.2f}s")
    lista = Path(tmp) / "lista.txt"
    lista.write_text("".join(f"file '{s}'\n" for s in segs))
    base = Path(tmp) / "base.mp4"
    comun.ff("-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", base)
    tx = sp.get("texto") or {}
    capa_texto(tx.get("lineas", []), tx.get("y", 300), tx.get("tam", 78)).save(Path(tmp) / "texto.png")
    extra = None
    if cierre and cierre.get("imagen"):
        logo = Image.open(ruta(cierre["imagen"])).convert("RGBA")
        lw = cierre.get("ancho", 460)
        logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
        extra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        extra.alpha_composite(logo, ((W - lw) // 2, 1500 - logo.height - 40 * len(cierre.get("lineas", []))))
    capa_texto((cierre or {}).get("lineas", []), 1460 - 0, 54, extra).save(Path(tmp) / "cierre.png")
    t_c = marcas[-2] if cierre else dur
    vf = (f"[0:v][1:v]overlay=0:0:shortest=1[v1];[2:v]format=rgba,fade=t=in:st={t_c:.3f}:d=0.25:alpha=1[c];"
          f"[v1][c]overlay=0:0:enable='gte(t,{t_c:.3f})',format=yuv420p[v]")
    comun.ff("-i", base, "-loop", "1", "-framerate", FPS, "-t", f"{dur:.3f}", "-i", Path(tmp) / "texto.png",
             "-loop", "1", "-framerate", FPS, "-t", f"{dur:.3f}", "-i", Path(tmp) / "cierre.png",
             "-filter_complex", vf, "-map", "[v]", "-t", f"{dur:.3f}", "-r", FPS, "-c:v", "libx264", "-preset", "medium",
             "-crf", "17", "-pix_fmt", "yuv420p", Path(tmp) / "v.mp4")
    out = carpeta / f"{nombre}.mp4"
    if can:
        fo = min(1.5, beats[-1] * per * 0.5)
        comun.ff("-ss", f"{desde:.3f}", "-i", arch, "-vn", "-af",
                 f"atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,afade=t=out:st={dur - fo:.3f}:d={fo:.3f},"
                 "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-t", f"{dur:.3f}", "-c:a", "aac", "-b:a", "192k",
                 Path(tmp) / "a.m4a")
        comun.ff("-i", Path(tmp) / "v.mp4", "-i", Path(tmp) / "a.m4a", "-map", "0:v", "-map", "1:a", "-c", "copy",
                 "-shortest", "-movflags", "+faststart", out)
    else:
        comun.ff("-i", Path(tmp) / "v.mp4", "-c", "copy", "-movflags", "+faststart", out)
    print(f"✔ {out}")
    if a.hoja:
        hoja = carpeta / f"{nombre}__hoja.jpg"
        comun.ff("-i", out, "-vf", "fps=1,scale=216:384,tile=7x3", "-frames:v", "1", hoja)
        print(f"✔ {hoja}")


if __name__ == "__main__":
    main()
