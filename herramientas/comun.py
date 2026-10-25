"""Piezas que comparten todas las herramientas: rutas del proyecto, dónde están los programas (ffmpeg,
whisper, el Python del proyecto) en Mac y en Windows, el modelo de Whisper, ffmpeg y la energía del audio.
No se corre solo: lo importan los demás scripts.

Todo es relativo a la carpeta del proyecto (la que tiene CLAUDE.md), así funciona en cualquier computadora.
"""
import glob
import json
import os
import platform
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

ES_WINDOWS = os.name == "nt"
ES_MAC = sys.platform == "darwin"
SISTEMA = "Windows" if ES_WINDOWS else ("Mac" if ES_MAC else platform.system() or "Linux")

# El modelo: large-v3-turbo (~1,6 GB, entiende bien el español). WHISPER_MODELO_NOMBRE cambia el nombre
# (la prueba automática de GitHub usa ggml-base.bin para no bajar 1,6 GB cada vez).
NOMBRE_MODELO = os.environ.get("WHISPER_MODELO_NOMBRE") or "ggml-large-v3-turbo.bin"
URL_MODELO = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/" + NOMBRE_MODELO

# Cómo se arregla lo que falta, según la computadora.
INSTALAR = ("powershell -ExecutionPolicy Bypass -File herramientas\\instalar.ps1" if ES_WINDOWS
            else "bash herramientas/instalar.sh")
CHEQUEO = ("powershell -ExecutionPolicy Bypass -File herramientas\\chequeo.ps1" if ES_WINDOWS
           else "bash herramientas/chequeo.sh")


def _utf8():
    """Que los acentos y los ✅ se vean bien también en la consola de Windows."""
    os.environ.setdefault("PYTHONUTF8", "1")           # para los Python que se llamen desde aquí
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _carpetas_extra():
    """Dónde pueden estar los programas aunque no estén en el PATH de esta ventana (p. ej. recién
    instalados con winget o Homebrew, antes de abrir otra terminal)."""
    extra = [HERRAMIENTAS / "whisper"]
    if ES_WINDOWS:
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        extra += [local / "Microsoft" / "WinGet" / "Links"]
        extra += [Path(p) for p in glob.glob(str(local / "Microsoft" / "WinGet" / "Packages" / "Gyan.FFmpeg*" / "*" / "bin"))]
        extra += [Path(p) for p in glob.glob(str(local / "Microsoft" / "WinGet" / "Packages" / "yt-dlp.yt-dlp*"))]
        extra += [Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "chocolatey" / "bin"]
        # whisper.cpp: el zip oficial trae los .exe en Release/ (o en la raíz, según la versión)
        extra += [Path(p).parent for p in glob.glob(str(HERRAMIENTAS / "whisper" / "**" / "whisper-cli.exe"), recursive=True)]
    else:
        extra += [Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
    return [p for p in extra if p.is_dir()]


def _preparar_path():
    actual = os.environ.get("PATH", "").split(os.pathsep)
    nuevas = [str(p) for p in _carpetas_extra() if str(p) not in actual]
    if nuevas:
        # al final: lo que ya está en el PATH manda; esto sólo rellena lo que falte
        os.environ["PATH"] = os.pathsep.join(actual + nuevas)


_utf8()
_preparar_path()

# whisper.cpp cambió el nombre del programa: whisper-cli (Homebrew y versiones nuevas), main (versiones viejas).
_ALIAS = {"whisper-cli": ["whisper-cli", "whisper-cpp", "main"] if ES_WINDOWS else ["whisper-cli", "whisper-cpp"]}


def herramienta(nombre):
    """La ruta completa de un programa (ffmpeg, ffprobe, yt-dlp, whisper-cli), o None si no está."""
    for n in _ALIAS.get(nombre, [nombre]):
        if ES_WINDOWS and n == "main":
            # main.exe sólo si es el de whisper.cpp (en herramientas/whisper), nunca otro «main» del sistema
            cand = sorted(glob.glob(str(HERRAMIENTAS / "whisper" / "**" / "main.exe"), recursive=True))
            if cand:
                return cand[0]
            continue
        ruta = shutil.which(n)
        if ruta:
            return ruta
    return None


def ffmpeg():
    return herramienta("ffmpeg") or "ffmpeg"


def ffprobe():
    return herramienta("ffprobe") or "ffprobe"


def whisper():
    return herramienta("whisper-cli")


def python_proyecto():
    """El Python del proyecto (.venv): .venv/bin/python en Mac, .venv\\Scripts\\python.exe en Windows."""
    p = RAIZ / ".venv" / ("Scripts/python.exe" if ES_WINDOWS else "bin/python")
    return p if p.exists() else Path(sys.executable)


def modelo_whisper(salir=True):
    """El modelo de Whisper: el de la variable WHISPER_MODELO, el de herramientas/modelos/, o el que ya
    tenga la computadora en ~/.cache/whisper.cpp/."""
    candidatos = []
    if os.environ.get("WHISPER_MODELO"):
        candidatos.append(Path(os.environ["WHISPER_MODELO"]).expanduser())
    candidatos += [HERRAMIENTAS / "modelos" / NOMBRE_MODELO,
                   Path.home() / ".cache" / "whisper.cpp" / NOMBRE_MODELO]
    for c in candidatos:
        if c.exists():
            return c
    if salir:
        sys.exit(f"✗ Falta el modelo de Whisper. Corre:  {INSTALAR}")
    return None


def fuente(redonda=True):
    """Una letra gruesa que exista en esta computadora (para subtítulos y textos), o None."""
    win = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    lista = (["/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf", win / "ARLRDBD.TTF"] if redonda else [])
    lista += ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc",
              win / "arialbd.ttf", win / "segoeuib.ttf", win / "seguisb.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    return next((str(f) for f in lista if Path(f).exists()), None)


def ruta_filtro(p):
    """Una ruta para escribirla DENTRO de un filtro de ffmpeg (lut3d=file='…'). En Windows la «C:» rompe
    el filtro: se pasa a C\\:/carpeta/archivo, que ffmpeg sí entiende. En Mac queda igual."""
    s = Path(p).resolve().as_posix() if ES_WINDOWS else str(p)
    return s.replace(":", "\\:") if ES_WINDOWS else s


def exigir(*nombres):
    faltan = [n for n in nombres if not herramienta(n)]
    if faltan:
        sys.exit(f"✗ Falta {', '.join(faltan)}. Corre:  {INSTALAR}")


def ff(*args):
    """ffmpeg callado; si falla, se detiene con el error."""
    subprocess.run([ffmpeg(), "-v", "error", "-y", *map(str, args)], check=True)


def duracion(f):
    return float(subprocess.check_output([ffprobe(), "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(f)]).decode().strip())


def fps(f):
    r = subprocess.check_output([ffprobe(), "-v", "error", "-select_streams", "v:0", "-show_entries",
                                 "stream=r_frame_rate", "-of", "csv=p=0", str(f)]).decode().strip().split(",")[0]
    num, den = (int(v) for v in r.split("/"))
    return num / den, r


def sonda(f):
    r = subprocess.run([ffprobe(), "-v", "error", "-show_entries",
                        "stream=codec_name,codec_type,width,height,r_frame_rate:format=duration,size,bit_rate",
                        "-of", "json", str(f)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", check=True)
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
    cmd = [whisper(), "-m", str(modelo_whisper()), "-f", str(wav), "-l", idioma,
           "-ml", "1", "-sow", "-oj", "-of", base, "-np"] + (["--prompt", prompt] if prompt else [])
    subprocess.run(cmd, capture_output=True, check=True)
    with open(base + ".json", encoding="utf-8", errors="replace") as fh:
        datos = json.load(fh)
    return [(s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, s["text"].strip())
            for s in datos["transcription"] if s["text"].strip() and not s["text"].strip().startswith("[")]


def whisper_texto(wav, idioma="es", prompt=None):
    exigir("whisper-cli")
    cmd = [whisper(), "-m", str(modelo_whisper()), "-f", str(wav), "-l", idioma, "-nt", "-np"]
    if prompt:
        cmd += ["--prompt", prompt]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip().replace("\n", " ")


# Pasar una toma HDR a SDR sin VideoToolbox (Windows): mapa de tonos con zscale (lo trae el ffmpeg de winget).
_HDR_A_SDR = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
              "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def entrada(f):
    """Cómo leer una toma: si es HDR del iPhone (HLG/PQ) se pasa a SDR (en Mac con VideoToolbox; en Windows
    con zscale); si no, nada. Devuelve (argumentos antes de -i, filtro inicial). Sin esto, una toma HDR
    sale quemada."""
    j = json.loads(subprocess.check_output([ffprobe(), "-v", "error", "-select_streams", "v:0", "-show_entries",
                                            "stream=width,height,color_transfer,pix_fmt:stream_side_data=rotation",
                                            "-of", "json", str(f)]))
    s = j["streams"][0]
    rot = 0
    for sd in s.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if s.get("color_transfer", "") in ("arib-std-b67", "smpte2084"):
        w, h = s["width"], s["height"]
        if not ES_MAC:
            # sin aceleración, ffmpeg ya gira la toma solo; se baja a la mitad como en la Mac
            return [], f"{_HDR_A_SDR},scale=trunc(iw/4)*2:trunc(ih/4)*2"
        gir = {-90: ",transpose=clock", 90: ",transpose=cclock", 180: ",hflip,vflip", -180: ",hflip,vflip"}.get(rot, "")
        fmt = "p010le" if "10" in s.get("pix_fmt", "") else "nv12"
        return (["-hwaccel", "videotoolbox", "-hwaccel_output_format", "videotoolbox_vld"],
                f"scale_vt=w={w // 2}:h={h // 2}:color_matrix=bt709:color_primaries=bt709:color_transfer=bt709,"
                f"hwdownload,format={fmt}{gir}")
    return [], "null"


# Lo que no se mide solo fuera de la Mac (Vision es de macOS). Claude lo revisa mirando la hoja de cuadros.
NOTA_SIN_VISION = (f"no medido en {SISTEMA}: Claude lo revisa en la hoja de cuadros" if not ES_MAC
                   else "Vision de macOS no respondió: se mide mirando la hoja de cuadros")


def vision_disponible():
    return ES_MAC and bool(shutil.which("osascript"))


def vision(imagenes):
    """Caras y textos de cada imagen con Vision de macOS (nada sale de la computadora).
    Devuelve {ruta: {"caras": [[x0,y0,x1,y1]...], "textos": [{"t": str, "caja": [...]}, ...]}} en fracciones, y=0 arriba.
    En Windows (sin Vision) o si Vision no responde, devuelve {}: quien lo use dice NOTA_SIN_VISION, nunca se cae."""
    if not imagenes or not vision_disponible():
        return {}
    js = HERRAMIENTAS / "vision.js"
    try:
        r = subprocess.run(["osascript", "-l", "JavaScript", str(js), *map(str, imagenes)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    except Exception:
        return {}


def proyecto(nombre):
    """La carpeta de trabajo de un video: proyectos/<nombre>/ (no se sube al repo)."""
    p = PROYECTOS / nombre
    p.mkdir(parents=True, exist_ok=True)
    return p


if __name__ == "__main__":
    # python herramientas/comun.py → qué encontró (lo usan chequeo.sh y chequeo.ps1)
    print(json.dumps({"sistema": SISTEMA, "ffmpeg": herramienta("ffmpeg"), "ffprobe": herramienta("ffprobe"),
                      "whisper": whisper(), "yt-dlp": herramienta("yt-dlp"),
                      "modelo": str(modelo_whisper(salir=False) or ""), "python": str(python_proyecto()),
                      "vision": vision_disponible(), "fuente": fuente()}, ensure_ascii=False, indent=1))
