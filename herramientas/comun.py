"""Piezas que comparten todas las herramientas: rutas del proyecto, el modelo de Whisper, ffmpeg y
la energía del audio. No se corre solo: lo importan los demás scripts.

Todo es relativo a la carpeta del proyecto (la que tiene CLAUDE.md), así funciona en cualquier Mac.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent          # la carpeta del proyecto
HERRAMIENTAS = RAIZ / "herramientas"
PROYECTOS = RAIZ / "proyectos"
MATERIAL = RAIZ / "material"
ESTILO = RAIZ / "estilo"

NOMBRE_MODELO = "ggml-large-v3-turbo.bin"
URL_MODELO = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/" + NOMBRE_MODELO


def modelo_whisper():
    """El modelo de Whisper: el de herramientas/modelos/, o el de la variable WHISPER_MODELO,
    o el que ya tenga la Mac en ~/.cache/whisper.cpp/."""
    candidatos = []
    if os.environ.get("WHISPER_MODELO"):
        candidatos.append(Path(os.environ["WHISPER_MODELO"]).expanduser())
    candidatos += [HERRAMIENTAS / "modelos" / NOMBRE_MODELO,
                   Path.home() / ".cache" / "whisper.cpp" / NOMBRE_MODELO]
    for c in candidatos:
        if c.exists():
            return c
    sys.exit("✗ Falta el modelo de Whisper. Corre:  bash herramientas/instalar.sh")


def herramienta(nombre):
    ruta = shutil.which(nombre)
    if not ruta:
        for base in ("/opt/homebrew/bin", "/usr/local/bin"):
            p = Path(base) / nombre
            if p.exists():
                return str(p)
    return ruta


def exigir(*nombres):
    faltan = [n for n in nombres if not herramienta(n)]
    if faltan:
        sys.exit(f"✗ Falta {', '.join(faltan)}. Corre:  bash herramientas/instalar.sh")


def ff(*args):
    """ffmpeg callado; si falla, se detiene con el error."""
    subprocess.run([herramienta("ffmpeg") or "ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def duracion(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(f)]).decode().strip())


def fps(f):
    r = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                 "stream=r_frame_rate", "-of", "csv=p=0", str(f)]).decode().strip().split(",")[0]
    num, den = (int(v) for v in r.split("/"))
    return num / den, r


def sonda(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_name,codec_type,width,height,r_frame_rate:format=duration,size,bit_rate",
                        "-of", "json", str(f)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def carpeta_temporal():
    t = tempfile.mkdtemp(prefix="editar-")
    import atexit
    atexit.register(shutil.rmtree, t, True)
    return t


def audio_16k(f, destino, desde=None, hasta=None):
    """El audio a 16 kHz mono (lo que usan Whisper y las medidas) y como arreglo de numpy."""
    import numpy as np
    corte = (["-ss", str(desde)] if desde is not None else []) + (["-to", str(hasta)] if hasta is not None else [])
    ff(*corte, "-i", f, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", destino)
    with wave.open(str(destino)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768


def energia(x, paso=160):
    """Volumen en dB cada 10 ms (160 muestras a 16 kHz)."""
    import numpy as np
    n = max(0, (len(x) - paso) // paso)
    return np.array([20 * np.log10(np.sqrt(np.mean(x[i * paso:(i + 1) * paso] ** 2)) + 1e-9) for i in range(n)])


def whisper_palabras(wav, idioma="es", prompt=None):
    """Palabra por palabra con su tiempo (whisper.cpp). Los tiempos corren hasta ±0,4 s: no son exactos."""
    exigir("whisper-cli")
    base = str(wav)[:-4] + "-w"
    cmd = [herramienta("whisper-cli"), "-m", str(modelo_whisper()), "-f", str(wav), "-l", idioma,
           "-ml", "1", "-sow", "-oj", "-of", base, "-np"] + (["--prompt", prompt] if prompt else [])
    subprocess.run(cmd, capture_output=True, check=True)
    datos = json.load(open(base + ".json", encoding="utf-8"))
    return [(s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, s["text"].strip())
            for s in datos["transcription"] if s["text"].strip() and not s["text"].strip().startswith("[")]


def whisper_texto(wav, idioma="es", prompt=None):
    exigir("whisper-cli")
    cmd = [herramienta("whisper-cli"), "-m", str(modelo_whisper()), "-f", str(wav), "-l", idioma, "-nt", "-np"]
    if prompt:
        cmd += ["--prompt", prompt]
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip().replace("\n", " ")


def entrada(f):
    """Cómo leer una toma: si es HDR del iPhone (HLG/PQ) se pasa a SDR con VideoToolbox; si no, nada.
    Devuelve (argumentos antes de -i, filtro inicial). Sin esto, una toma HDR sale quemada."""
    j = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                            "stream=width,height,color_transfer,pix_fmt:stream_side_data=rotation",
                                            "-of", "json", str(f)]))
    s = j["streams"][0]
    rot = 0
    for sd in s.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if s.get("color_transfer", "") in ("arib-std-b67", "smpte2084"):
        w, h = s["width"], s["height"]
        gir = {-90: ",transpose=clock", 90: ",transpose=cclock", 180: ",hflip,vflip", -180: ",hflip,vflip"}.get(rot, "")
        fmt = "p010le" if "10" in s.get("pix_fmt", "") else "nv12"
        return (["-hwaccel", "videotoolbox", "-hwaccel_output_format", "videotoolbox_vld"],
                f"scale_vt=w={w // 2}:h={h // 2}:color_matrix=bt709:color_primaries=bt709:color_transfer=bt709,"
                f"hwdownload,format={fmt}{gir}")
    return [], "null"


def vision(imagenes):
    """Caras y textos de cada imagen con Vision de macOS (nada sale de la Mac).
    Devuelve {ruta: {"caras": [[x0,y0,x1,y1]...], "textos": [{"t": str, "caja": [...]}, ...]}} en fracciones, y=0 arriba.
    Si Vision no responde (otra versión de macOS), devuelve {}."""
    if not imagenes:
        return {}
    js = HERRAMIENTAS / "vision.js"
    try:
        r = subprocess.run(["osascript", "-l", "JavaScript", str(js), *map(str, imagenes)],
                           capture_output=True, text=True, timeout=600)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    except Exception:
        return {}


def proyecto(nombre):
    """La carpeta de trabajo de un video: proyectos/<nombre>/ (no se sube al repo)."""
    p = PROYECTOS / nombre
    p.mkdir(parents=True, exist_ok=True)
    return p
