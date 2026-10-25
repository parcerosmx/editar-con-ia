#!/usr/bin/env python3
"""Limpia la voz de una toma ENTERA, antes de cortarla. La imagen no se toca.

  .venv/bin/python herramientas/limpiar_voz.py TOMA SALIDA.mp4 [--ia] [--ruido]

Por defecto (sin nada que instalar): repara las sílabas que saturaron el micrófono (adeclip) y deja la
voz a −14 LUFS, el volumen de las redes.
  --ruido   toma sin micrófono o con ruido de salón: quita ruido (afftdn nr=24), compuerta suave y −14 LUFS,
            SIN compresor. 🟢 medido: la separación voz/ruido pasó de 18 a 21 dB; con compresor bajaba a 11.
  --ia      además, ClearerVoice (IA local) reconstruye los agudos que corta el micrófono, y sólo se usa
            arriba de 8 kHz para no cambiar consonantes («s» finales). Necesita `bash herramientas/instalar.sh --voz`.

Lo aprendido (🟢): la mejora de voz se aplica a la toma ENTERA, nunca por pedazos: si no, cada pedazo queda
a otro volumen y las uniones suenan raro. Si tienes CapCut, su «mejora de voz» sigue siendo muy buena:
úsala sobre la toma entera y aquí sólo se corta.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

ENTORNO_IA = comun.HERRAMIENTAS / ".voz-ia"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("toma")
    ap.add_argument("salida")
    ap.add_argument("--ruido", action="store_true", help="quitar ruido de fondo (salón, calle)")
    ap.add_argument("--ia", action="store_true", help="reconstruir agudos con ClearerVoice (instalar con --voz)")
    a = ap.parse_args()
    comun.exigir("ffmpeg")
    tmp = comun.carpeta_temporal()
    cadena = "adeclip"
    if a.ruido:
        cadena += ",afftdn=nr=24:nf=-34,agate=threshold=0.02:ratio=2:attack=5:release=120"
    base = Path(tmp) / "voz.wav"
    comun.ff("-i", a.toma, "-vn", "-af", cadena, "-ac", "1", "-ar", "48000", base)
    if a.ia:
        py = ENTORNO_IA / ("Scripts/python.exe" if comun.ES_WINDOWS else "bin/python")
        if not py.exists():
            sys.exit("✗ Falta la voz IA (por ahora sólo en Mac). Corre:  bash herramientas/instalar.sh --voz")
        sr = Path(tmp) / "voz-sr.wav"
        codigo = ("from clearvoice import ClearVoice\n"
                  "cv = ClearVoice(task='speech_super_resolution', model_names=['MossFormer2_SR_48K'])\n"
                  f"o = cv(input_path=r'{base}', online_write=False)\ncv.write(o, output_path=r'{sr}')\n")
        # ClearerVoice baja sus modelos a ./checkpoints de donde se corre: siempre la misma carpeta
        subprocess.run([str(py), "-c", codigo], check=True, cwd=str(ENTORNO_IA))
        mezcla = Path(tmp) / "voz-mezcla.wav"
        comun.ff("-i", base, "-i", sr, "-filter_complex",
                 "[0:a]aresample=48000,lowpass=f=8000:p=2,lowpass=f=8000:p=2[a];"
                 "[1:a]aresample=48000,highpass=f=8000:p=2,highpass=f=8000:p=2[h];[a][h]amix=inputs=2:normalize=0",
                 "-ac", "1", "-ar", "48000", mezcla)
        base = mezcla
    final = Path(tmp) / "final.wav"
    comun.ff("-i", base, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", final)
    comun.ff("-i", a.toma, "-i", final, "-map", "0:v?", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
             "-shortest", "-movflags", "+faststart", a.salida)
    print(f"✔ {a.salida} · voz {'con IA, ' if a.ia else ''}{'sin ruido, ' if a.ruido else ''}a −14 LUFS · escúchala antes de seguir")


if __name__ == "__main__":
    main()
