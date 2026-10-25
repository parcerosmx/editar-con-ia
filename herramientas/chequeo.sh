#!/bin/bash
# Revisa que todo esté instalado y hace una prueba chiquita de punta a punta, sin material de nadie:
# arma un video de prueba de 6 s (con la voz de la Mac), lo transcribe, mide su estilo, le quita las pausas,
# le pone subtítulos, lo mezcla con un riser y lo entrega. Tarda 1–2 minutos.
# En Windows: powershell -ExecutionPolicy Bypass -File herramientas\chequeo.ps1
#
#   bash herramientas/chequeo.sh            todo
#   bash herramientas/chequeo.sh --rapido   sólo revisa que esté instalado (sin la prueba)
set -u
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ" || exit 1
for b in /opt/homebrew/bin /usr/local/bin; do [ -d "$b" ] && export PATH="$b:$PATH"; done
FALLAS=0
ok()  { echo "✅ $*"; }
mal() { echo "❌ $*"; FALLAS=$((FALLAS + 1)); }

PY=.venv/bin/python
[ -x "$PY" ] || PY=/usr/bin/python3

echo "Editar con IA · chequeo"
command -v brew >/dev/null 2>&1 && ok "Homebrew" || mal "Homebrew  → bash herramientas/instalar.sh"
command -v ffmpeg >/dev/null 2>&1 && ok "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}')" || mal "ffmpeg  → bash herramientas/instalar.sh"
command -v ffprobe >/dev/null 2>&1 && ok "ffprobe" || mal "ffprobe  → bash herramientas/instalar.sh"
command -v whisper-cli >/dev/null 2>&1 && ok "whisper-cpp" || mal "whisper-cpp  → bash herramientas/instalar.sh"
command -v yt-dlp >/dev/null 2>&1 && ok "yt-dlp (para links)" || mal "yt-dlp  → bash herramientas/instalar.sh"
MOD=$("$PY" -c "import sys; sys.path.insert(0,'herramientas'); import comun; print(comun.modelo_whisper())" 2>/dev/null)
[ -n "$MOD" ] && ok "modelo de Whisper ($(basename "$MOD"))" || mal "modelo de Whisper  → bash herramientas/instalar.sh"
if [ "$PY" = ".venv/bin/python" ]; then ok "Python del proyecto (.venv)"; else mal "Python del proyecto (.venv)  → bash herramientas/instalar.sh"; fi
"$PY" -c "import PIL, numpy" 2>/dev/null && ok "Pillow y numpy" || mal "Pillow y numpy  → bash herramientas/instalar.sh"
V=$(osascript -l JavaScript herramientas/vision.js 2>/dev/null)
[ "$V" = "{}" ] && ok "Vision de macOS (caras y textos)" || mal "Vision de macOS no respondió (se puede trabajar sin él, mirando las hojas)"
ls material/03-musica-y-efectos/risers/*.wav >/dev/null 2>&1 && ok "efectos de sonido propios" || mal "efectos propios  → bash herramientas/instalar.sh"
[ -x herramientas/.voz-ia/bin/python ] && ok "voz IA (opcional)" || echo "·  voz IA no instalada (opcional: bash herramientas/instalar.sh --voz)"

if [ "${1:-}" = "--rapido" ]; then
  echo; [ $FALLAS -eq 0 ] && echo "Todo instalado." || echo "$FALLAS cosa(s) por arreglar."; exit $FALLAS
fi
if [ $FALLAS -gt 0 ]; then
  echo; echo "Faltan $FALLAS cosa(s): corre  bash herramientas/instalar.sh  y vuelve a probar."; exit 1
fi

# la prueba de punta a punta es la misma en Mac y en Windows (herramientas/prueba_completa.py)
"$PY" herramientas/prueba_completa.py
exit $?
