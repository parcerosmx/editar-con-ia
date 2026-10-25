#!/usr/bin/env python3
"""
revisar.py — convierte un video en lo que Claude sí puede leer.

═══════════════════════════════════════════════════════════════════════════
POR QUÉ EXISTE
═══════════════════════════════════════════════════════════════════════════

Claude no abre video ni audio: lee texto e imágenes. Este script saca las dos
cosas, todo en esta computadora (Mac o Windows) y sin mandar nada a ningún servicio:

  · lo que se dice, con su segundo   → whisper.cpp, modelo large-v3-turbo
  · lo que se ve                     → ffmpeg: un cuadro por intervalo y otro en
                                       cada cambio de plano, más hojas de
                                       contacto de 12 cuadros con la hora encima
  · cómo suena                       → volumen (LUFS), pico, silencios, ritmo

y lo junta en `informe.md` con una línea de tiempo: cada cuadro al lado de lo
que se está diciendo en ese segundo. Con `--guion`, marca palabra por palabra
qué se dijo igual, qué cambió, qué se agregó y qué se omitió.

Uso:
    revisar.py <archivo | link | ultimo> [--guion hablado.txt] [--cada 1] [--idioma es]
    revisar.py denso <carpeta-o-archivo> <desde> <hasta> [--cada 0.2]
    revisar.py verificar

Todo queda en proyectos/_revisiones/<fecha>-<nombre>-<huella>/ (dentro de la carpeta
del proyecto, que no se sube al repo; REVISIONES=<carpeta> lo cambia). El mismo
archivo no se procesa dos veces: se reusa lo hecho (`--rehacer` para empezar de
cero). Sólo librería estándar; Pillow es opcional y sólo pone la hora encima de
cada cuadro en las hojas.
"""
import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

# La carpeta del proyecto: .claude/skills/revisar-video/revisar.py → tres niveles arriba.
RAIZ = Path(__file__).resolve().parents[3]
CACHE = Path(os.environ["REVISIONES"]).expanduser() if os.environ.get("REVISIONES") else RAIZ / "proyectos" / "_revisiones"
# Dónde están los programas y el modelo (Mac o Windows): lo sabe herramientas/comun.py.
sys.path.insert(0, str(RAIZ / "herramientas"))
import comun  # noqa: E402

MODELO = comun.modelo_whisper(salir=False) or comun.HERRAMIENTAS / "modelos" / comun.NOMBRE_MODELO
URL_MODELO = comun.URL_MODELO
VOCABULARIO = Path(__file__).resolve().parent / "vocabulario.txt"

EXT_VIDEO = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".3gp"}
EXT_AUDIO = {".m4a", ".mp3", ".wav", ".aac", ".ogg", ".opus", ".flac", ".aif", ".aiff"}
# Donde cae lo que llega por AirDrop o se baja del navegador.
DONDE_BUSCAR = ([RAIZ / "material" / c for c in ("02-a-camara", "01-tomas-de-apoyo", "04-referentes")]
                + [Path.home() / "Downloads", Path.home() / "Desktop", Path.home() / "Movies", Path.home() / "Videos"])

POR_HOJA = 12
MAX_CUADROS = 96      # en videos largos el intervalo se estira para no pasar de aquí
UMBRAL_ESCENA = 0.3   # 0–1: cuánto tiene que cambiar la imagen para contar como plano nuevo

# Frases que Whisper inventa sobre música o silencio. Nadie las dijo.
ALUCINACIONES = ("amara org", "subtitulos realizados por", "subtitulos por la comunidad",
                 "subtitulado por", "suscribete", "no olvides suscribirte", "gracias por ver")
MULETILLAS = {"eh", "em", "ehm", "mm", "mmm", "ah", "este", "pues", "bueno", "osea"}


def herramienta(nombre):
    """Encuentra un programa aunque Homebrew o winget no estén en el PATH del proceso."""
    return comun.herramienta(nombre)


FFMPEG, FFPROBE = herramienta("ffmpeg"), herramienta("ffprobe")


def aviso(texto):
    print(texto, file=sys.stderr, flush=True)


def correr(cmd, cwd=None):
    cmd = [str(c) for c in cmd]
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit(f"✗ Falló {Path(cmd[0]).name}:\n{r.stderr.strip()[-1500:]}")
    return r


# ── tiempo y texto ─────────────────────────────────────────────────────────

def reloj(segundos):
    total = round(max(0.0, float(segundos)), 1)
    m, s = divmod(total, 60)
    return f"{int(m)}:{s:04.1f}"


def a_segundos(texto):
    """«12.5», «0:12.5» o «1:02» → segundos."""
    total = 0.0
    for parte in str(texto).replace(",", ".").split(":"):
        total = total * 60 + float(parte)
    return total


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def normalizar(texto):
    """Minúsculas, sin tildes ni puntuación. Para comparar, nunca para mostrar."""
    return " ".join(re.sub(r"[^\w]+", " ", sin_tildes(texto.lower())).split())


def recortar(texto, largo):
    texto = texto.replace("|", "\\|")
    return texto if len(texto) <= largo else texto[: largo - 1].rstrip() + "…"


def hace(segundos):
    s = int(segundos)
    if s < 90:
        return f"{s} s"
    if s < 5400:
        return f"{s // 60} min"
    if s < 172800:
        return f"{s // 3600} h"
    return f"{s // 86400} días"


# ── de dónde sale el video ─────────────────────────────────────────────────

def bajar(url):
    ytdlp = herramienta("yt-dlp")
    if not ytdlp:
        sys.exit(f"✗ Falta yt-dlp. Corre:  {comun.INSTALAR}")
    destino = CACHE / "_descargas"
    destino.mkdir(parents=True, exist_ok=True)
    aviso("· bajando…")
    r = subprocess.run(
        [ytdlp, "--no-playlist", "--no-progress", "--no-simulate",
         "-f", "bv*+ba/b", "--merge-output-format", "mp4", "--write-info-json",
         "--ffmpeg-location", str(Path(FFMPEG).parent),
         "-o", str(destino / "%(extractor)s-%(id)s.%(ext)s"),
         "--print", "after_move:filepath", url],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        error = r.stderr.strip()
        if re.search(r"log ?in|cookies|private|sign in|authenticat", error, re.I):
            sys.exit("✗ Ese link pide sesión (Instagram suele pedirla). No se usan las cookies "
                     "del navegador: que lo bajen desde la app y pasen el archivo.\n\n" + error[-600:])
        sys.exit("✗ yt-dlp no pudo bajarlo:\n" + error[-1200:])
    return Path([l for l in r.stdout.splitlines() if l.strip()][-1].strip())


def datos_de_origen(video):
    """Autor, fecha y cifras del post, si el video vino de un link."""
    info = video.with_suffix(".info.json")
    if not info.exists():
        return None
    j = json.loads(info.read_text(encoding="utf-8", errors="replace"))
    fecha = j.get("upload_date")
    return {
        "link": j.get("webpage_url"),
        "autor": j.get("uploader") or j.get("channel") or j.get("uploader_id"),
        "publicado": f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:]}" if fecha else None,
        "descripcion": (j.get("description") or j.get("title") or "")[:600],
        "vistas": j.get("view_count"), "likes": j.get("like_count"),
        "comentarios": j.get("comment_count"), "compartidos": j.get("repost_count"),
    }


def ultimo():
    candidatos, bloqueadas = [], []
    for carpeta in DONDE_BUSCAR:
        try:
            candidatos += [p for p in carpeta.iterdir()
                           if p.is_file() and p.suffix.lower() in EXT_VIDEO | EXT_AUDIO]
        except PermissionError:
            bloqueadas.append(carpeta.name)
        except FileNotFoundError:
            pass
    if bloqueadas:
        aviso(f"· macOS no dejó leer {', '.join(bloqueadas)}: se autoriza en Ajustes del Sistema → "
              "Privacidad y seguridad → Archivos y carpetas")
    if not candidatos:
        sys.exit("✗ No hay videos en material/, Descargas, Escritorio ni Películas.")
    elegido = max(candidatos, key=lambda p: p.stat().st_mtime)
    edad = dt.datetime.now().timestamp() - elegido.stat().st_mtime
    aviso(f"· tomé el más reciente: {elegido}  (hace {hace(edad)})")
    return elegido


def resolver(fuente):
    if re.match(r"^https?://", fuente.strip()):
        return bajar(fuente.strip())
    if sin_tildes(fuente.strip().lower()) == "ultimo":
        return ultimo()
    ruta = Path(fuente).expanduser()
    if ruta.is_dir() and (ruta / "datos.json").exists():
        return Path(json.loads((ruta / "datos.json").read_text(encoding="utf-8"))["fuente"])
    if not ruta.is_file():
        sys.exit(f"✗ No existe: {ruta}")
    return ruta.resolve()


def huella(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()[:10]


def carpeta_de(ruta, rehacer=False):
    """Una carpeta por archivo, identificada por su contenido: renombrarlo no la duplica."""
    h = huella(ruta)
    previas = sorted(CACHE.glob(f"*-{h}"))
    if previas and not rehacer:
        return previas[-1]
    for vieja in previas:
        shutil.rmtree(vieja)
    nombre = re.sub(r"[^a-z0-9]+", "-", sin_tildes(ruta.stem.lower())).strip("-")[:40] or "video"
    carpeta = CACHE / f"{dt.date.today():%Y-%m-%d}-{nombre}-{h}"
    carpeta.mkdir(parents=True)
    return carpeta


# ── mirar el archivo ───────────────────────────────────────────────────────

def sondear(ruta):
    r = correr([FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", ruta])
    d = json.loads(r.stdout or "{}")
    streams = d.get("streams", [])
    # Una carátula de mp3/m4a llega como stream de video: no cuenta.
    video = next((s for s in streams if s.get("codec_type") == "video"
                  and not (s.get("disposition") or {}).get("attached_pic")), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    meta = {"duracion": float(d.get("format", {}).get("duration") or 0),
            "audio": audio is not None, "video": video is not None}
    if video:
        ancho, alto = int(video.get("width") or 0), int(video.get("height") or 0)
        giro = 0
        for extra in video.get("side_data_list") or []:
            if "rotation" in extra:
                giro = int(float(extra["rotation"]))
        giro = giro or int(float((video.get("tags") or {}).get("rotate", 0)))
        if abs(giro) % 180 == 90:          # el celular guarda de lado y marca el giro
            ancho, alto = alto, ancho
        num, _, den = (video.get("avg_frame_rate") or "0/1").partition("/")
        fps = float(num) / float(den) if den and float(den) else 0.0
        meta.update(ancho=ancho, alto=alto, fps=round(fps, 2))
    return meta


def orientacion(meta):
    if meta["alto"] > meta["ancho"] * 1.1:
        return "vertical"
    if meta["ancho"] > meta["alto"] * 1.1:
        return "horizontal"
    return "cuadrado"


# ── lo que se dice ─────────────────────────────────────────────────────────

def vocabulario():
    if not VOCABULARIO.exists():
        return ""
    lineas = [l.strip() for l in VOCABULARIO.read_text(encoding="utf-8").splitlines()]
    return " ".join(l for l in lineas if l and not l.startswith("#"))


def transcribir(fuente, carpeta, idioma):
    whisper = herramienta("whisper-cli")
    if not whisper or not MODELO.exists():
        sys.exit("✗ Falta whisper.cpp o su modelo. Corre:  revisar.py verificar")
    aviso("· transcribiendo…")
    wav = carpeta / "_audio-16k.wav"
    correr([FFMPEG, "-v", "error", "-y", "-i", fuente, "-vn", "-ac", "1", "-ar", "16000",
            "-c:a", "pcm_s16le", wav])
    cmd = [whisper, "-m", MODELO, "-f", wav, "-l", idioma, "-oj", "-osrt",
           "-of", carpeta / "transcripcion", "-np", "-t", min(8, os.cpu_count() or 4)]
    contexto = vocabulario()
    if contexto and idioma in ("es", "auto"):
        cmd += ["--prompt", contexto]
    # Sin --vad a propósito: en whisper.cpp 1.9 junta todas las frases en una sola y
    # borra las pausas, que es justo lo que la línea de tiempo necesita (probado 11-sep-2026).
    try:
        correr(cmd)
    finally:
        wav.unlink(missing_ok=True)


def leer_transcripcion(carpeta):
    ruta = carpeta / "transcripcion.json"
    if not ruta.exists():
        return []
    segmentos = []
    for t in json.loads(ruta.read_text(encoding="utf-8", errors="replace")).get("transcription", []):
        texto = (t.get("text") or "").strip()
        if not texto:
            continue
        segmentos.append({
            "desde": t["offsets"]["from"] / 1000, "hasta": t["offsets"]["to"] / 1000, "texto": texto,
            "sospechoso": any(a in normalizar(texto) for a in ALUCINACIONES),
            # [Música], (aplausos), ♪: Whisper describiendo, no alguien hablando
            "anotacion": bool(re.fullmatch(r"[\[\(].*[\]\)]", texto))
                         or not re.search(r"\w", texto.replace("♪", "")),
        })
    return segmentos


def medir_audio(fuente):
    aviso("· midiendo el audio…")
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(fuente), "-vn",
                        "-af", "ebur128=peak=true:framelog=verbose", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    resumen = r.stderr.rsplit("Summary:", 1)[-1]
    lufs = re.search(r"\bI:\s+(-?[\d.]+|-inf)\s+LUFS", resumen)
    pico = re.search(r"Peak:\s+(-?[\d.]+|-inf)\s+dBFS", resumen)
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(fuente), "-vn",
                        "-af", "silencedetect=noise=-35dB:d=0.4", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    inicios = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    fines = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", r.stderr)]

    def numero(m):
        return None if not m or "inf" in m.group(1) else float(m.group(1))
    return {"lufs": numero(lufs), "pico": numero(pico),
            "silencios": [[round(max(0.0, a), 2), round(fines[k], 2) if k < len(fines) else None]
                          for k, a in enumerate(inicios)]}


# ── lo que se ve ───────────────────────────────────────────────────────────

def sacar_cuadros(fuente, destino, cada, desde=None, hasta=None, escenas=True):
    """Un cuadro cada `cada` segundos y, si `escenas`, otro en cada cambio de plano."""
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    # −0,02: si no, a 30 fps el cuadro «del segundo 1» cae en 0,9999 y el muestreo se corre.
    # `scene` va siempre: sin él los cuadros no llevan metadatos y `metadata=print` no
    # escribe su tiempo. Con escenas=False el umbral es 2, que nunca se alcanza (va de 0 a 1).
    corte = UMBRAL_ESCENA if escenas else 2
    expr = (f"isnan(prev_selected_t)+gte(t-prev_selected_t,{cada - 0.02:.3f})"
            f"+gt(scene,{corte})*gte(t-prev_selected_t,0.25)")
    filtro = (f"select='gt({expr},0)',metadata=print:file=_seleccion.txt,"
              "scale='trunc(iw*min(1,1920/max(iw,ih))/2)*2':-2")
    cmd = [FFMPEG, "-v", "error", "-y"]
    if desde is not None:
        cmd += ["-ss", f"{desde:.3f}"]
    if hasta is not None:     # antes de -i: lo que pasa del límite ni se lee, y metadata=print no lo cuenta
        cmd += ["-t", f"{hasta - (desde or 0):.3f}"]
    cmd += ["-i", fuente, "-vf", filtro, "-fps_mode", "vfr", "-q:v", "3", "-start_number", "0", "%04d.jpg"]
    correr(cmd, cwd=destino)

    tiempos, actual = [], None
    seleccion = destino / "_seleccion.txt"
    for linea in seleccion.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"frame:(\d+)\s+pts:\S+\s+pts_time:(\S+)", linea)
        if m:
            actual = {"t": round(float(m.group(2)) + (desde or 0), 2), "cambio": 0.0}
            tiempos.append(actual)
        elif actual and linea.startswith("lavfi.scene_score="):
            actual["cambio"] = float(linea.split("=", 1)[1])
    seleccion.unlink()
    imagenes = sorted(destino.glob("[0-9][0-9][0-9][0-9].jpg"))
    if len(imagenes) != len(tiempos):
        aviso(f"· ojo: {len(imagenes)} imágenes y {len(tiempos)} tiempos: los tiempos quedan aproximados")
        tiempos = [{"t": round((desde or 0) + k * cada, 2), "cambio": 0.0} for k in range(len(imagenes))]

    cuadros = []
    for i, (imagen, c) in enumerate(zip(imagenes, tiempos), 1):
        m, s = divmod(c["t"], 60)
        nombre = f"{i:04d}-{int(m):02d}m{s:04.1f}s.jpg"
        imagen.rename(destino / nombre)
        cuadros.append({"archivo": nombre, "t": c["t"], "escena": i > 1 and c["cambio"] > UMBRAL_ESCENA})
    return cuadros


def armar_hojas(cuadros, origen, destino, orient):
    """Hojas de contacto de 12 cuadros. Una hoja cuesta lo mismo de leer que un cuadro suelto."""
    destino.mkdir(parents=True, exist_ok=True)
    for vieja in destino.glob("hoja-*.jpg"):
        vieja.unlink()
    cols, filas, tw, th = {"vertical": (4, 3, 270, 480),
                           "horizontal": (3, 4, 480, 270)}.get(orient, (4, 3, 330, 330))
    try:
        from PIL import Image, ImageDraw, ImageFont
        pil = (Image, ImageDraw, ImageFont)
    except ImportError:
        pil = None
    hojas = []
    for k in range(0, len(cuadros), POR_HOJA):
        grupo = cuadros[k:k + POR_HOJA]
        salida = destino / f"hoja-{k // POR_HOJA + 1:02d}.jpg"
        if pil:
            hoja_con_hora(grupo, origen, salida, cols, filas, tw, th, *pil)
        else:
            hoja_sin_hora(grupo, origen, salida, cols, filas, tw, th)
        hojas.append({"archivo": salida.name, "primero": k + 1, "ultimo": k + len(grupo),
                      "desde": grupo[0]["t"], "hasta": grupo[-1]["t"]})
    return hojas, pil is not None


def letra(ImageFont, tamano):
    ruta = comun.fuente(redonda=False)
    if ruta:
        try:
            return ImageFont.truetype(ruta, tamano)
        except OSError:
            pass
    return ImageFont.load_default()


def hoja_con_hora(grupo, origen, salida, cols, filas, tw, th, Image, ImageDraw, ImageFont):
    borde = 8
    hoja = Image.new("RGB", (cols * tw + (cols + 1) * borde, filas * th + (filas + 1) * borde), "white")
    lapiz, fuente = ImageDraw.Draw(hoja), letra(ImageFont, 26)
    for i, c in enumerate(grupo):
        x = borde + (i % cols) * (tw + borde)
        y = borde + (i // cols) * (th + borde)
        with Image.open(origen / c["archivo"]) as im:
            im = im.convert("RGB")
            im.thumbnail((tw, th))
            hoja.paste(im, (x + (tw - im.width) // 2, y + (th - im.height) // 2))
        caja = lapiz.textbbox((x + 10, y + 8), reloj(c["t"]), font=fuente)
        lapiz.rectangle([caja[0] - 6, caja[1] - 5, caja[2] + 6, caja[3] + 5], fill="black")
        lapiz.text((x + 10, y + 8), reloj(c["t"]), fill="#FFD400", font=fuente)
        if c.get("escena"):                    # punto rojo = plano nuevo
            cx, cy, r = caja[2] + 24, (caja[1] + caja[3]) // 2, 10
            lapiz.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#FF2D2D", outline="white", width=3)
    hoja.save(salida, quality=85)


def hoja_sin_hora(grupo, origen, salida, cols, filas, tw, th):
    lista = origen / "_lista.txt"
    lista.write_text("".join(f"file '{c['archivo']}'\n" for c in grupo), encoding="utf-8")
    filtro = (f"scale={tw}:{th}:force_original_aspect_ratio=decrease,"
              f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=white,"
              f"tile={cols}x{filas}:padding=8:margin=8:color=white")
    try:
        correr([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista.name,
                "-vf", filtro, "-frames:v", "1", "-q:v", "3", salida], cwd=origen)
    finally:
        lista.unlink(missing_ok=True)


# ── contra el guion ────────────────────────────────────────────────────────

def palabras_del_guion(texto):
    utiles = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith(("#", "|", "---", "```")):
            continue
        linea = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", linea)     # acotaciones: [corte], (pausa)
        utiles.append(re.sub(r"[*_>`~]", " ", linea))
    return [p for p in " ".join(utiles).split() if normalizar(p)]


def comparar(ruta_guion, segmentos):
    guion = palabras_del_guion(Path(ruta_guion).expanduser().read_text(encoding="utf-8", errors="replace"))
    dichas = []                                # (palabra, segundo aproximado dentro de su frase)
    for s in segmentos:
        if s["sospechoso"] or s["anotacion"]:
            continue
        palabras = [p for p in s["texto"].split() if normalizar(p)]
        for k, p in enumerate(palabras):
            dichas.append((p, s["desde"] + (s["hasta"] - s["desde"]) * k / len(palabras)))
    a = [normalizar(p) for p in guion]
    b = [normalizar(p) for p, _ in dichas]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    cambios, muletillas = [], Counter()
    for tipo, i1, i2, j1, j2 in sm.get_opcodes():
        if tipo == "equal":
            continue
        trozo = " ".join(b[j1:j2]).replace("o sea", "osea").split()
        if tipo == "insert" and trozo and all(p in MULETILLAS for p in trozo):
            muletillas.update(p.replace("osea", "o sea") for p in trozo)
            continue
        t = dichas[j1][1] if j1 < len(dichas) else (dichas[-1][1] if dichas else 0.0)
        cambios.append((tipo, t, " ".join(guion[i1:i2]), " ".join(p for p, _ in dichas[j1:j2])))
    return {"guion": str(ruta_guion), "palabras_guion": len(a), "cambios": cambios, "muletillas": muletillas,
            "tal_cual": sum(m.size for m in sm.get_matching_blocks()) / max(1, len(a))}


# ── el informe ─────────────────────────────────────────────────────────────

def escribir_informe(carpeta, datos, segmentos, comparacion):
    meta, fuente = datos["meta"], Path(datos["fuente"])
    habla = [s for s in segmentos if not (s["sospechoso"] or s["anotacion"])]
    L = [f"# Revisión — {fuente.name}", ""]

    origen = datos.get("origen")
    if origen:
        L.append(f"- **Link:** {origen.get('link')}")
        L.append(f"- **Publicado por:** {origen.get('autor')} · {origen.get('publicado') or 'sin fecha'}")
        cifras = [f"{v:,} {k}".replace(",", ".") for k, v in (
            ("vistas", origen.get("vistas")), ("likes", origen.get("likes")),
            ("comentarios", origen.get("comentarios")), ("compartidos", origen.get("compartidos")))
            if v is not None]
        if cifras:
            L.append(f"- **Cifras al bajarlo:** {' · '.join(cifras)}")
        if origen.get("descripcion"):
            texto_post = " ".join(origen["descripcion"].split())
            L.append(f"- **Texto del post:** {texto_post}")
    L.append(f"- **Archivo:** `{fuente}`")
    formato = [f"dura {reloj(meta['duracion'])}"]
    if meta["video"]:
        formato.append(f"{meta['ancho']}×{meta['alto']} {orientacion(meta)} · {meta['fps']:g} fps")
    formato.append("con audio" if meta["audio"] else "**sin audio**")
    L += [f"- **Formato:** {' · '.join(formato)}", f"- **Preparado:** {dt.datetime.now():%Y-%m-%d %H:%M}", ""]

    if meta["audio"]:
        sonido = datos.get("sonido") or {}
        silencios = sonido.get("silencios") or []
        L += ["## Cómo suena", ""]
        if sonido.get("lufs") is not None:
            L.append(f"- **Volumen:** {sonido['lufs']:.1f} LUFS — en redes la referencia usual es ≈ −14; "
                     "por debajo de −20 se oye bajo al lado de otros videos")
        if sonido.get("pico") is not None:
            alerta = " ⚠️ roza el máximo, puede saturar" if sonido["pico"] > -1 else ""
            L.append(f"- **Pico:** {sonido['pico']:.1f} dBFS{alerta}")
        if habla:
            entra = habla[0]["desde"]
            if silencios and silencios[0][0] <= 0.05 and silencios[0][1]:
                entra = max(entra, silencios[0][1])
            palabras = sum(len(s["texto"].split()) for s in habla)
            tiempo = sum(s["hasta"] - s["desde"] for s in habla)
            L.append(f"- **La voz entra en:** {reloj(entra)}")
            if tiempo > 0:
                L.append(f"- **Ritmo:** {palabras / tiempo * 60:.0f} palabras por minuto "
                         f"({palabras} palabras en {tiempo:.1f} s de habla)")
        largos = [(a, b) for a, b in silencios if b is None or b - a >= 0.8]
        if largos:
            tramos = " · ".join(f"{reloj(a)}–{reloj(b) if b is not None else 'final'}" for a, b in largos)
            L.append(f"- **Silencios de 0,8 s o más:** {tramos}")
        L += ["", "## Lo que se dice", ""]
        if not segmentos:
            L.append("_Whisper no encontró voz._")
        for s in segmentos:
            nota = ("  ⚠️ _frase típica que Whisper inventa sobre música o silencio: "
                    "probablemente nadie la dijo_") if s["sospechoso"] else ""
            L.append(f"- `{reloj(s['desde'])}–{reloj(s['hasta'])}` {s['texto']}{nota}")
        L.append("")

    if comparacion:
        L += [f"## Contra el guion — `{comparacion['guion']}`", "",
              f"- **Dicho tal cual:** {comparacion['tal_cual'] * 100:.0f} % de las "
              f"{comparacion['palabras_guion']} palabras del guion"]
        if comparacion["muletillas"]:
            conteo = " · ".join(f"«{m}» ×{n}" for m, n in comparacion["muletillas"].most_common())
            L.append(f"- **Muletillas:** {conteo}")
        if comparacion["cambios"]:
            etiquetas = {"insert": "➕ agregado", "delete": "➖ omitido", "replace": "✏️ cambiado"}
            L += ["", "| Segundo | | En el guion | Se dijo |", "|---|---|---|---|"]
            for tipo, t, guion, dicho in comparacion["cambios"]:
                L.append(f"| {reloj(t)} | {etiquetas[tipo]} | {recortar(guion, 120) or '—'} | "
                         f"{recortar(dicho, 120) or '—'} |")
        else:
            L.append("- **Se dijo exactamente el guion.**")
        L.append("")

    if datos.get("cuadros"):
        con_voz = meta["audio"]
        L += ["## Línea de tiempo", "",
              ("Cada cuadro con lo que se está diciendo en ese segundo. " if con_voz else "")
              + "**Hoja** = hoja · posición (de izquierda a derecha y de arriba abajo). ● = cambio de plano."
              + (" 〃 = sigue la misma frase." if con_voz else ""),
              "", "| # | Segundo | Hoja | Plano |" + (" Se dice |" if con_voz else ""),
              "|---|---|---|---|" + ("---|" if con_voz else "")]
        anterior = None
        for i, c in enumerate(datos["cuadros"], 1):
            posicion = f"{(i - 1) // POR_HOJA + 1}·{(i - 1) % POR_HOJA + 1}"
            fila = f"| {i} | {reloj(c['t'])} | {posicion} | {'●' if c['escena'] else ''} |"
            if con_voz:
                s = next((s for s in habla if s["desde"] <= c["t"] < s["hasta"]), None)
                if s is None:
                    fila += " — |"
                elif s is anterior:
                    fila += " 〃 |"
                else:
                    fila += f" «{recortar(s['texto'], 90)}» |"
                anterior = s
            L.append(fila)
        L.append("")

    L += ["## Archivos", ""]
    for h in datos.get("hojas") or []:
        L.append(f"- `hojas/{h['archivo']}` — cuadros {h['primero']}–{h['ultimo']} · "
                 f"{reloj(h['desde'])} → {reloj(h['hasta'])}")
    if datos.get("cuadros"):
        L.append(f"- `fotogramas/` — los {len(datos['cuadros'])} cuadros a resolución completa")
        if not datos.get("hojas_con_hora"):
            L.append("- ⚠️ Sin Pillow las hojas no llevan la hora encima: guiarse por la columna «Hoja».")
    if meta["audio"]:
        L.append("- `transcripcion.srt` · `transcripcion.json`")
    (carpeta / "informe.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ── comandos ───────────────────────────────────────────────────────────────

def preparar(args):
    fuente = resolver(args.fuente)
    carpeta = carpeta_de(fuente, args.rehacer)
    ruta_datos = carpeta / "datos.json"
    datos = json.loads(ruta_datos.read_text(encoding="utf-8")) if ruta_datos.exists() else {}
    datos["fuente"] = str(fuente)
    origen = datos_de_origen(fuente)
    if origen:
        datos["origen"] = origen
    meta = datos["meta"] = sondear(fuente)
    if not (meta["audio"] or meta["video"]):
        sys.exit("✗ ffprobe no encuentra ni audio ni video en ese archivo.")

    if meta["audio"]:
        if datos.get("idioma") != args.idioma or not (carpeta / "transcripcion.json").exists():
            transcribir(fuente, carpeta, args.idioma)
            datos["idioma"] = args.idioma
        if "sonido" not in datos:
            datos["sonido"] = medir_audio(fuente)
    segmentos = leer_transcripcion(carpeta)

    if meta["video"]:
        cada = args.cada or max(1.0, round(meta["duracion"] / MAX_CUADROS, 1))
        if datos.get("cada") != cada or not (carpeta / "fotogramas").is_dir():
            aviso("· sacando cuadros…")
            datos["cuadros"] = sacar_cuadros(fuente, carpeta / "fotogramas", cada)
            datos["cada"] = cada
            datos["hojas"], datos["hojas_con_hora"] = armar_hojas(
                datos["cuadros"], carpeta / "fotogramas", carpeta / "hojas", orientacion(meta))

    comparacion = comparar(args.guion, segmentos) if args.guion else None
    ruta_datos.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    escribir_informe(carpeta, datos, segmentos, comparacion)

    habla = [s for s in segmentos if not (s["sospechoso"] or s["anotacion"])]
    print(f"✔ {carpeta}")
    print("  · informe.md  ← empezar por aquí")
    if datos.get("hojas"):
        print(f"  · hojas/: {len(datos['hojas'])} hojas, {len(datos['cuadros'])} cuadros "
              f"(uno cada {datos['cada']:g} s + cada cambio de plano)")
    if meta["audio"]:
        sospechosas = sum(1 for s in segmentos if s["sospechoso"])
        extra = f" · ⚠️ {sospechosas} con pinta de inventadas" if sospechosas else ""
        print(f"  · transcripción: {len(habla)} frases{extra}")
    if comparacion:
        print(f"  · contra el guion: {comparacion['tal_cual'] * 100:.0f} % tal cual, "
              f"{len(comparacion['cambios'])} cambios")


def denso(args):
    fuente = resolver(args.fuente)
    carpeta, meta = carpeta_de(fuente), sondear(fuente)
    if not meta["video"]:
        sys.exit("✗ Ese archivo no tiene video.")
    desde, hasta = a_segundos(args.desde), min(a_segundos(args.hasta), meta["duracion"])
    if hasta <= desde:
        sys.exit("✗ <hasta> tiene que ser mayor que <desde>.")
    destino = carpeta / f"denso-{desde:.1f}-{hasta:.1f}".replace(".", "_")
    cuadros = sacar_cuadros(fuente, destino, args.cada, desde, hasta, escenas=False)
    hojas, _ = armar_hojas(cuadros, destino, destino, orientacion(meta))
    print(f"✔ {len(cuadros)} cuadros entre {reloj(desde)} y {reloj(hasta)}, uno cada {args.cada:g} s")
    print(f"  {destino}")
    for h in hojas:
        print(f"  · {h['archivo']}: {reloj(h['desde'])} → {reloj(h['hasta'])}")


def verificar():
    try:
        import PIL
        pillow = f"Pillow {PIL.__version__}"
    except ImportError:
        pillow = None
    whisper = herramienta("whisper-cli")
    filas = [
        (True, "ffmpeg + ffprobe", FFMPEG and FFPROBE, comun.INSTALAR),
        (True, "whisper-cli", whisper, comun.INSTALAR),
        (True, f"modelo {MODELO.name}", MODELO if MODELO.exists() else None, comun.INSTALAR),
        (False, "yt-dlp (para links)", herramienta("yt-dlp"), comun.INSTALAR),
        (False, "Pillow (hora en las hojas)", pillow, comun.INSTALAR),
    ]
    falta = False
    for requerido, nombre, listo, arreglo in filas:
        marca = "✔" if listo else ("✗" if requerido else "·")
        print(f"  {marca} {nombre:28} {listo or arreglo}")
        falta = falta or (requerido and not listo)
    sys.exit(1 if falta else 0)


def main():
    if not FFMPEG or not FFPROBE:
        sys.exit(f"✗ Falta ffmpeg. Corre:  {comun.INSTALAR}")
    orden = sys.argv[1] if len(sys.argv) > 1 else ""
    if orden == "verificar":
        return verificar()
    if orden == "denso":
        p = argparse.ArgumentParser(prog="revisar.py denso",
                                    description="Cuadros seguidos en una ventana corta, para ver lo que pasa entre dos.")
        p.add_argument("fuente", help="la carpeta de la revisión o el archivo")
        p.add_argument("desde", help="12.5, 0:12.5 o 1:02")
        p.add_argument("hasta")
        p.add_argument("--cada", type=float, default=0.2, help="segundos entre cuadros (0.2)")
        return denso(p.parse_args(sys.argv[2:]))
    p = argparse.ArgumentParser(prog="revisar.py", description=__doc__.split("Uso:")[0].strip(),
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fuente", help="archivo, link (TikTok, Instagram, Facebook, YouTube…) o «ultimo»")
    p.add_argument("--guion", help=".txt con sólo lo que se dice, para comparar palabra por palabra")
    p.add_argument("--cada", type=float, help="segundos entre cuadros (por defecto 1, más en videos largos)")
    p.add_argument("--idioma", default="es", help="es (por defecto) o auto")
    p.add_argument("--rehacer", action="store_true", help="olvidar lo hecho con este archivo")
    preparar(p.parse_args())


if __name__ == "__main__":
    main()
