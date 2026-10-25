#!/usr/bin/env python3
"""Deja el video listo para publicar: lo verifica, guarda la versión de calidad y una copia ligera para el celular.

  .venv/bin/python herramientas/entregar.py VIDEO NOMBRE [--comparar version-anterior.mp4]

  1 · verifica: 1080×1920 (vertical), duración, que tenga audio, H.264/AAC, y el volumen (−14 LUFS ± 1,5)
  2 · guarda la calidad en proyectos/<pieza>/NOMBRE.mp4 (H.264 ~16 Mbps, AAC 256k): la que se sube a la red
  3 · y una copia ligera (≤ 30 MB) en proyectos/<pieza>/NOMBRE_ligero.mp4 para mandarla por AirDrop o WhatsApp
  4 · --comparar: dice si la imagen y el audio son idénticos a otra versión (¿el cambio movió algo?)
NOMBRE: «<pieza>_v3» mientras se itera, «<pieza>_final» al cerrar. <pieza> es NOMBRE sin _vN ni _final.

⛔ Esto NO publica nada. Publicar lo hace el dueño, desde su celular, cuando lo apruebe.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402


def md5(ruta, mapa):
    return subprocess.run([comun.ffmpeg(), "-v", "error", "-i", str(ruta), "-map", mapa, "-f", "md5", "-"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()


def lufs(ruta):
    r = subprocess.run([comun.ffmpeg(), "-v", "info", "-i", str(ruta), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    return float(i[-1]) if i else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("nombre")
    ap.add_argument("--comparar")
    a = ap.parse_args()
    comun.exigir("ffmpeg", "ffprobe")
    pieza = re.sub(r"_(v\d+\w*|final)$", "", a.nombre)
    carpeta = comun.proyecto(pieza)
    calidad = carpeta / f"{a.nombre}.mp4"
    ligero = carpeta / f"{a.nombre}_ligero.mp4"
    s = comun.sonda(a.video)
    tipos = {x["codec_type"]: x for x in s["streams"]}
    v = tipos.get("video", {})
    ok_formato = (v.get("width"), v.get("height")) == (1080, 1920)
    if not ok_formato:
        print(f"⚠️ el video es {v.get('width')}x{v.get('height')}: se pasa a 1080×1920 (vertical) recortando al centro")
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p"
    comun.ff("-i", a.video, "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-b:v", "16M", "-maxrate", "20M",
             "-bufsize", "32M", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", calidad)
    sc = comun.sonda(calidad)
    dur = float(sc["format"]["duration"])
    dur0 = float(s["format"]["duration"])
    tc = {x["codec_type"]: x for x in sc["streams"]}
    L = lufs(calidad)
    print(f"{calidad.name}: {dur:.2f} s · {int(sc['format']['size']) / 1e6:.1f} MB · "
          f"{tc['video']['width']}x{tc['video']['height']} {tc['video']['codec_name']} + {tc.get('audio', {}).get('codec_name', 'SIN AUDIO')}"
          + (f" · {L:.1f} LUFS" if L is not None else ""))
    problemas = []
    if abs(dur - dur0) > 0.15:
        problemas.append("la duración cambió")
    if "audio" not in tc:
        problemas.append("no tiene audio")
    if L is not None and abs(L + 14) > 1.5:
        problemas.append(f"el volumen está en {L:.1f} LUFS (las redes usan −14: pásalo por mezclar.py)")
    if dur > 90:
        problemas.append("dura más de 90 s (un reel de 30–60 s retiene mejor)")
    print("✅ verificado" if not problemas else "⚠️ revisar: " + "; ".join(problemas))
    kbps = int(min(3800, max(800, (29e6 * 8 / max(dur, 1) - 128e3) / 1000)))
    comun.ff("-i", calidad, "-vf", "scale=720:1280", "-c:v", "libx264", "-preset", "medium", "-b:v", f"{kbps}k",
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", ligero)
    print(f"✔ calidad: {calidad}\n✔ ligero para el celular: {ligero} ({ligero.stat().st_size / 1e6:.1f} MB)")
    if a.comparar:
        iguales = md5(calidad, "0:v") == md5(a.comparar, "0:v") and md5(calidad, "0:a") == md5(a.comparar, "0:a")
        print(f"{'✔ IDÉNTICO' if iguales else '≠ distinto'} a {Path(a.comparar).name} (imagen y audio)")
    print("⛔ No se publicó nada: súbelo tú cuando lo apruebes.")


if __name__ == "__main__":
    main()
