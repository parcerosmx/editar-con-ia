#!/usr/bin/env python3
"""Hace un video de prueba de unos segundos, sin material de nadie: tres «tomas» de colores con cortes,
un texto en pantalla y una voz de la computadora diciendo una frase con pausas: en Mac el comando `say`,
en Windows la voz de Windows (System.Speech). Si no hay voz en español usa la que haya; si no hay ninguna,
pone un tono.

  .venv/bin/python herramientas/video_de_prueba.py SALIDA.mp4 [--sin-voz]

Lo usan herramientas/chequeo.sh y chequeo.ps1 para probar que todo funciona. No se sube al repo.
"""
import argparse
import base64
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

FRASE = ["Hola. Esto es una prueba.", "Hoy hicimos arepas, tacos y café de olla."]   # con una pausa en medio


def voz_mac(destino, tmp):
    """Voz en español con `say` (viene con la Mac); si no hay, la voz que tenga la Mac."""
    frase = f"{FRASE[0]} [[slnc 700]] {FRASE[1]}"
    for nombre in ("Paulina", "Mónica", "Eddy (Spanish (Mexico))", "Flo (Spanish (Mexico))", None):
        aiff = Path(tmp) / "voz.aiff"
        r = subprocess.run(["say", *(["-v", nombre] if nombre else []), "-o", str(aiff), frase], capture_output=True)
        if r.returncode == 0 and aiff.exists() and aiff.stat().st_size > 10000:
            comun.ff("-i", aiff, "-ar", "48000", "-ac", "1", destino)
            return True
    return False


# Voz de Windows (SAPI, System.Speech): una voz en español si la hay; si no, la de Windows. Sin internet.
_SAPI = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$es = $s.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -like 'es-*' } | Select-Object -First 1
if ($es) { $s.SelectVoice($es.VoiceInfo.Name) }
$p = New-Object System.Speech.Prompting.PromptBuilder
$p.AppendText($env:FRASE1)
$p.AppendBreak([TimeSpan]::FromMilliseconds(700))
$p.AppendText($env:FRASE2)
$s.SetOutputToWaveFile($env:SALIDA_WAV)
$s.Speak($p)
$s.Dispose()
"""


def voz_windows(destino, tmp):
    wav = Path(tmp) / "voz-sapi.wav"
    entorno = dict(os.environ, FRASE1=FRASE[0], FRASE2=FRASE[1], SALIDA_WAV=str(wav))
    ps = shutil.which("powershell") or shutil.which("pwsh") or "powershell"
    try:
        codigo = base64.b64encode(_SAPI.encode("utf-16-le")).decode()   # así no hay líos de comillas
        r = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-EncodedCommand", codigo], env=entorno,
                           capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if r.returncode == 0 and wav.exists() and wav.stat().st_size > 10000:
        comun.ff("-i", wav, "-ar", "48000", "-ac", "1", destino)
        return True
    return False


def voz(destino, tmp):
    """Devuelve True si salió una voz."""
    if comun.ES_WINDOWS:
        return voz_windows(destino, tmp)
    if shutil.which("say"):
        return voz_mac(destino, tmp)
    return False


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("salida")
    p.add_argument("--sin-voz", action="store_true", help="sólo un tono, sin voz")
    a = p.parse_args()
    from PIL import Image, ImageDraw, ImageFont
    tmp = comun.carpeta_temporal()
    wav = Path(tmp) / "audio.wav"
    con_voz = not a.sin_voz and voz(wav, tmp)
    if not con_voz:
        comun.ff("-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-ar", "48000", "-ac", "1", wav)
    dur = max(4.0, comun.duracion(wav) + 0.4)
    # el texto en pantalla, dibujado con Pillow (el ffmpeg de Homebrew no trae drawtext)
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = comun.fuente(redonda=False)
    fuente = ImageFont.truetype(f, 64) if f else None
    texto = "VIDEO DE PRUEBA"
    w = d.textlength(texto, font=fuente) if fuente else 400
    d.text(((1080 - w) / 2, 1300), texto, font=fuente, fill="white", stroke_width=6, stroke_fill="black")
    png = Path(tmp) / "texto.png"
    im.save(png)
    t1, t2 = round(dur * 0.4, 2), round(dur * 0.7, 2)
    # tres «tomas» con imagen distinta (patrones de prueba de ffmpeg), para que haya cortes que medir
    fondo = (f"testsrc2=s=1080x1920:r=30:d={t1}[a];smptebars=s=1080x1920:r=30:d={t2 - t1:.2f}[b];"
             f"rgbtestsrc=s=1080x1920:r=30:d={dur - t2:.2f}[c];"
             f"[a][b][c]concat=n=3:v=1:a=0,setsar=1[f];[f][1:v]overlay=0:0,format=yuv420p[v]")
    comun.ff("-f", "lavfi", "-i", "nullsrc=s=16x16:d=0.1", "-loop", "1", "-t", f"{dur:.2f}", "-i", png, "-i", wav,
             "-filter_complex", fondo, "-map", "[v]", "-map", "2:a", "-t", f"{dur:.2f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k", a.salida)
    print(f"✔ {a.salida} · {dur:.1f} s · {'con voz de la computadora' if con_voz else 'con tono (sin voz)'}")


if __name__ == "__main__":
    main()
