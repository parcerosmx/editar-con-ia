#!/bin/bash
# Revisa que todo esté instalado y hace una prueba chiquita de punta a punta, sin material de nadie:
# arma un video de prueba de 6 s (con la voz de la Mac), lo transcribe, mide su estilo, le quita las pausas,
# le pone subtítulos, lo mezcla con un riser y lo entrega. Tarda 1–2 minutos.
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

echo; echo "Prueba de punta a punta (sin material de nadie)…"
P="proyectos/_chequeo"; rm -rf "$P"; mkdir -p "$P"
paso() {  # paso "nombre" comando...
  local n="$1"; shift
  if "$@" > "$P/log-$n.txt" 2>&1; then ok "$n"; else mal "$n (ver $P/log-$n.txt)"; tail -5 "$P/log-$n.txt" | sed 's/^/     /'; fi
}
paso "video de prueba"        "$PY" herramientas/video_de_prueba.py "$P/prueba.mp4"
paso "revisar-video"          env REVISIONES="$P/revisiones" "$PY" .claude/skills/revisar-video/revisar.py "$P/prueba.mp4"
if grep -qiE "prueba|arepa|hola" "$P"/revisiones/*/informe.md 2>/dev/null; then ok "Whisper entendió la voz de prueba"
else echo "·  Whisper no reconoció las palabras (si la Mac no tiene voz en español es normal: se usó un tono)"; fi
paso "medir estilo"           "$PY" herramientas/medir_estilo.py "$P/prueba.mp4" --hojas "$P" --json "$P/medidas.json"
paso "quitar pausas"          "$PY" herramientas/quitar_pausas.py "$P/prueba.mp4" "$P/sin-pausas.mp4"
paso "tiempos de palabras"    "$PY" herramientas/tiempos_voz.py "$P/sin-pausas.mp4" --json "$P/palabras.json"
paso "subtítulos"             "$PY" herramientas/subtitulos.py "$P/palabras.json" "$P/subs" --video "$P/sin-pausas.mp4" --salida "$P/con-subs.mp4"
paso "gancho de texto"        "$PY" herramientas/texto_en_pantalla.py "$P/con-subs.mp4" "$P/con-gancho.mp4" "Prueba de gancho" --hasta 2
cat > "$P/mezcla.json" <<EOF
{"video": "$P/con-gancho.mp4", "margen_db": 10,
 "efectos": [{"archivo": "material/03-musica-y-efectos/risers/riser-03-solo-grave-2.0s.wav", "t": 0.0, "tipo": "riser"},
             {"archivo": "material/03-musica-y-efectos/efectos/ding-1.wav", "t": 3.0, "tipo": "ding"}],
 "lufs_final": -14}
EOF
paso "mezcla (dings ≥24 dB)"  "$PY" herramientas/mezclar.py "$P/mezcla.json" "$P/mezclado.mp4"
cat > "$P/mezcla-mala.json" <<EOF
{"video": "$P/con-gancho.mp4",
 "efectos": [{"archivo": "material/03-musica-y-efectos/risers/riser-03-solo-grave-2.0s.wav", "t": 0.0},
             {"archivo": "material/03-musica-y-efectos/risers/riser-01-referencia-1.6s.wav", "t": 2.5}]}
EOF
if "$PY" herramientas/mezclar.py "$P/mezcla-mala.json" "$P/no-debe-salir.mp4" > "$P/log-risers.txt" 2>&1; then
  mal "la regla «nunca dos risers pegados» no frenó la mezcla"
else ok "regla «nunca dos risers pegados» (frenó una mezcla mala)"; fi
paso "verificar"              "$PY" herramientas/verificar_base.py "$P/mezclado.mp4"
paso "entregar"               "$PY" herramientas/entregar.py "$P/mezclado.mp4" _chequeo_v1
paso "storyboard"             "$PY" herramientas/storyboard.py version "$P/mezclado.mp4" "$P/storyboard"
echo
if [ $FALLAS -eq 0 ]; then
  echo "Todo funciona. 🎬  (La prueba quedó en $P/; se puede borrar.)"
else
  echo "$FALLAS cosa(s) fallaron. Pásale este resultado a Claude para que lo arregle."
fi
exit $FALLAS
