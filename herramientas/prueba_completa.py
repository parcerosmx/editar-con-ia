#!/usr/bin/env python3
"""La prueba de punta a punta del chequeo, igual en Mac y en Windows, sin material de nadie: arma un video
de prueba de 6 s (con la voz de la computadora), lo transcribe, mide su estilo, le quita las pausas, le pone
subtítulos y gancho, lo mezcla con un riser y lo entrega. Imprime una línea ✅/❌ por paso.

  .venv/bin/python herramientas/prueba_completa.py            (Mac)
  .venv\\Scripts\\python.exe herramientas\\prueba_completa.py  (Windows)

La corren herramientas/chequeo.sh y herramientas/chequeo.ps1. Sale con el número de pasos que fallaron.
Todo queda en proyectos/_chequeo/ (se puede borrar).
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

R = comun.RAIZ
P = comun.PROYECTOS / "_chequeo"
H = comun.HERRAMIENTAS
PY = sys.executable
FALLAS = 0


def ok(t):
    print(f"✅ {t}", flush=True)


def mal(t):
    global FALLAS
    FALLAS += 1
    print(f"❌ {t}", flush=True)


def rel(p):
    try:
        return Path(p).relative_to(R).as_posix()
    except ValueError:
        return str(p)


def correr(*args, env=None):
    entorno = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", **(env or {}))
    return subprocess.run([PY, *map(str, args)], cwd=R, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=entorno)


def paso(nombre, *args, env=None, debe_fallar=False):
    r = correr(*args, env=env)
    log = P / f"log-{re.sub(r'[^a-z0-9]+', '-', nombre.lower()).strip('-')}.txt"
    log.write_text((r.stdout or "") + (r.stderr or ""), encoding="utf-8")
    bien = (r.returncode != 0) if debe_fallar else (r.returncode == 0)
    if bien:
        ok(nombre)
    else:
        mal(f"{nombre} (ver {rel(log)})")
        for linea in ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-5:]:
            print(f"     {linea}")
    return bien


def main():
    print("\nPrueba de punta a punta (sin material de nadie)…", flush=True)
    shutil.rmtree(P, ignore_errors=True)
    P.mkdir(parents=True)
    prueba = P / "prueba.mp4"
    paso("video de prueba", H / "video_de_prueba.py", prueba)
    paso("revisar-video", R / ".claude/skills/revisar-video/revisar.py", prueba,
         env={"REVISIONES": str(P / "revisiones")})
    informes = " ".join(f.read_text(encoding="utf-8", errors="replace").lower()
                        for f in (P / "revisiones").glob("*/informe.md"))
    if re.search(r"prueba|arepa|hola", informes):
        ok("Whisper entendió la voz de prueba")
    else:
        print("·  Whisper no reconoció las palabras (si la computadora no tiene voz en español es normal)")
    paso("medir estilo", H / "medir_estilo.py", prueba, "--hojas", P, "--json", P / "medidas.json")
    paso("quitar pausas", H / "quitar_pausas.py", prueba, P / "sin-pausas.mp4")
    paso("tiempos de palabras", H / "tiempos_voz.py", P / "sin-pausas.mp4", "--json", P / "palabras.json")
    paso("subtítulos", H / "subtitulos.py", P / "palabras.json", P / "subs", "--video", P / "sin-pausas.mp4",
         "--salida", P / "con-subs.mp4")
    paso("gancho de texto", H / "texto_en_pantalla.py", P / "con-subs.mp4", P / "con-gancho.mp4",
         "Prueba de gancho", "--hasta", "2")
    efectos = "material/03-musica-y-efectos"
    mezcla = {"video": rel(P / "con-gancho.mp4"), "margen_db": 10,
              "efectos": [{"archivo": f"{efectos}/risers/riser-03-solo-grave-2.0s.wav", "t": 0.0, "tipo": "riser"},
                          {"archivo": f"{efectos}/efectos/ding-1.wav", "t": 3.0, "tipo": "ding"}],
              "lufs_final": -14}
    (P / "mezcla.json").write_text(json.dumps(mezcla, ensure_ascii=False), encoding="utf-8")
    paso("mezcla (dings ≥24 dB)", H / "mezclar.py", P / "mezcla.json", P / "mezclado.mp4")
    mala = {"video": rel(P / "con-gancho.mp4"),
            "efectos": [{"archivo": f"{efectos}/risers/riser-03-solo-grave-2.0s.wav", "t": 0.0},
                        {"archivo": f"{efectos}/risers/riser-01-referencia-1.6s.wav", "t": 2.5}]}
    (P / "mezcla-mala.json").write_text(json.dumps(mala, ensure_ascii=False), encoding="utf-8")
    r = correr(H / "mezclar.py", P / "mezcla-mala.json", P / "no-debe-salir.mp4")
    (P / "log-risers.txt").write_text((r.stdout or "") + (r.stderr or ""), encoding="utf-8")
    if r.returncode == 0:
        mal("la regla «nunca dos risers pegados» no frenó la mezcla")
    else:
        ok("regla «nunca dos risers pegados» (frenó una mezcla mala)")
    paso("verificar", H / "verificar_base.py", P / "mezclado.mp4")
    paso("entregar", H / "entregar.py", P / "mezclado.mp4", "_chequeo_v1")
    paso("storyboard", H / "storyboard.py", "version", P / "mezclado.mp4", P / "storyboard")
    print()
    if FALLAS == 0:
        print(f"Todo funciona. 🎬  (La prueba quedó en {rel(P)}/; se puede borrar.)")
    else:
        print(f"{FALLAS} cosa(s) fallaron. Pásale este resultado a Claude para que lo arregle.")
    return FALLAS


if __name__ == "__main__":
    sys.exit(main())
