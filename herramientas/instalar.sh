#!/bin/bash
# Instala lo que necesita «Editar con IA» en una Mac. Se puede correr las veces que sea: lo que ya está, se salta.
# (En Windows es otro: powershell -ExecutionPolicy Bypass -File herramientas\instalar.ps1)
#
#   bash herramientas/instalar.sh            pregunta antes de instalar cada cosa
#   bash herramientas/instalar.sh --si       instala sin preguntar (ya dijiste que sí)
#   bash herramientas/instalar.sh --voz      además, la voz IA local (ClearerVoice, ~2–5 GB). Opcional.
#   bash herramientas/instalar.sh --ayuda    muestra esto
#
# Qué instala (todo corre en tu Mac; nada de tus videos sale a internet):
#   · Homebrew      el instalador de programas de la Mac (si no lo tienes, te dice cómo, porque pide tu contraseña)
#   · ffmpeg        corta, une y mide el video y el audio
#   · whisper-cpp   transcribe lo que se dice, con el segundo exacto
#   · yt-dlp        baja videos de un link (TikTok, Instagram, YouTube) para estudiarlos
#   · el modelo de Whisper que entiende español (large-v3-turbo, ~1,6 GB) en herramientas/modelos/
#   · un Python propio del proyecto (.venv) con Pillow y numpy
#   · efectos de sonido propios (risers, woosh, ding) en material/03-musica-y-efectos/
set -u

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ" || exit 1
SI=0; VOZ=0
for a in "$@"; do
  case "$a" in
    --si|-y) SI=1 ;;
    --voz) VOZ=1 ;;
    --ayuda|-h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "No conozco la opción $a (usa --ayuda)"; exit 1 ;;
  esac
done

# WHISPER_MODELO_NOMBRE=ggml-base.bin cambia el modelo (lo usa la prueba automática de GitHub, para no bajar 1,6 GB)
MODELO="${WHISPER_MODELO_NOMBRE:-ggml-large-v3-turbo.bin}"
case "$MODELO" in *large*) MINIMO=1500000000 ;; *) MINIMO=30000000 ;; esac
URL_MODELO="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$MODELO"

ok()   { echo "✅ $*"; }
nota() { echo "   $*"; }
mal()  { echo "❌ $*"; }

preguntar() {   # preguntar "texto" → 0 si sí
  [ "$SI" = 1 ] && return 0
  if [ ! -t 0 ]; then
    echo "   (para instalarlo sin preguntar: bash herramientas/instalar.sh --si)"; return 1
  fi
  read -r -p "   ¿Lo instalo? [s/N] " r
  case "$r" in s|S|si|SI|sí|Sí) return 0 ;; *) return 1 ;; esac
}

[ "$(uname)" = "Darwin" ] || { mal "Esto es para Mac. En Windows: powershell -ExecutionPolicy Bypass -File herramientas\\instalar.ps1"; exit 1; }
echo "Editar con IA · instalación en $RAIZ"
echo

# 1 · Homebrew
for b in /opt/homebrew/bin /usr/local/bin; do [ -x "$b/brew" ] && export PATH="$b:$PATH"; done
if command -v brew >/dev/null 2>&1; then
  ok "Homebrew"
else
  mal "Falta Homebrew (el instalador de programas de la Mac)."
  nota "Pide la contraseña de tu Mac, así que lo instalas tú, una sola vez:"
  nota "1. Abre la app «Terminal» (Cmd+Espacio, escribe Terminal)."
  nota "2. Pega esto y dale Enter:"
  echo '      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  nota "3. Escribe tu contraseña cuando la pida (no se ven las letras: es normal)."
  nota "4. Cuando termine, vuelve aquí y corre otra vez: bash herramientas/instalar.sh"
  exit 2
fi

# 2 · Programas
FALTAN=()
command -v ffmpeg >/dev/null 2>&1 && ok "ffmpeg" || FALTAN+=(ffmpeg)
command -v whisper-cli >/dev/null 2>&1 && ok "whisper-cpp" || FALTAN+=(whisper-cpp)
command -v yt-dlp >/dev/null 2>&1 && ok "yt-dlp" || FALTAN+=(yt-dlp)
if [ ${#FALTAN[@]} -gt 0 ]; then
  echo "• Faltan: ${FALTAN[*]} (se instalan con Homebrew; ffmpeg es lo más pesado, unos minutos)"
  if preguntar; then
    brew install "${FALTAN[@]}" || { mal "Homebrew no pudo instalar ${FALTAN[*]}"; exit 1; }
    ok "instalados: ${FALTAN[*]}"
  else
    mal "Sin ${FALTAN[*]} no funciona. Vuelve a correr esto cuando quieras."; exit 1
  fi
fi

# 3 · Modelo de Whisper (español)
mkdir -p herramientas/modelos
DEST="herramientas/modelos/$MODELO"
if [ -s "$DEST" ] && [ "$(stat -L -f%z "$DEST" 2>/dev/null || echo 0)" -gt "$MINIMO" ]; then
  ok "modelo de Whisper ($MODELO)"
elif [ -s "$HOME/.cache/whisper.cpp/$MODELO" ]; then
  ln -sf "$HOME/.cache/whisper.cpp/$MODELO" "$DEST"
  ok "modelo de Whisper (ya estaba en esta Mac; se enlazó, no se volvió a bajar)"
else
  echo "• Falta el modelo de Whisper que entiende español: $MODELO (~1,6 GB, se baja una vez)"
  if preguntar; then
    curl -L --fail -C - --progress-bar -o "$DEST.part" "$URL_MODELO" && mv "$DEST.part" "$DEST" \
      && ok "modelo de Whisper" || { mal "No se pudo bajar el modelo (¿internet?). Vuelve a correr esto: sigue donde se quedó."; exit 1; }
  else
    mal "Sin el modelo no se puede transcribir."; exit 1
  fi
fi

# 4 · Python del proyecto
if [ -x .venv/bin/python ] && .venv/bin/python -c "import PIL, numpy" 2>/dev/null; then
  ok "Python del proyecto (.venv con Pillow y numpy)"
else
  if ! xcode-select -p >/dev/null 2>&1; then
    mal "Falta Python (viene con las «herramientas de línea de comandos» de Apple)."
    nota "Corre:  xcode-select --install   (se abre una ventana: dale Instalar) y luego vuelve a correr esto."
    exit 2
  fi
  echo "• Creando el Python del proyecto en .venv (Pillow y numpy, ~60 MB)"
  if preguntar; then
    python3 -m venv .venv && .venv/bin/python -m pip install -q --upgrade pip \
      && .venv/bin/python -m pip install -q -r herramientas/requirements.txt \
      && ok "Python del proyecto" || { mal "No se pudo crear .venv"; exit 1; }
  else
    mal "Sin Python no corren las herramientas."; exit 1
  fi
fi

# 5 · Efectos de sonido propios
if ls material/03-musica-y-efectos/risers/*.wav >/dev/null 2>&1; then
  ok "efectos de sonido propios"
else
  .venv/bin/python herramientas/sintetizar_efectos.py >/dev/null && ok "efectos de sonido propios (risers, woosh, ding)"
fi

# 6 · Opcional: voz IA local
if [ "$VOZ" = 1 ]; then
  if [ -x herramientas/.voz-ia/bin/python ] && herramientas/.voz-ia/bin/python -c "import clearvoice" 2>/dev/null; then
    ok "voz IA (ClearerVoice)"
  else
    echo "• Voz IA local (ClearerVoice): un Python 3.11 aparte en herramientas/.voz-ia, ~2–5 GB con sus modelos."
    nota "Es opcional: la «mejora de voz» de CapCut sobre la toma entera da un resultado parecido."
    if preguntar; then
      command -v uv >/dev/null 2>&1 || brew install uv
      uv venv --python 3.11 herramientas/.voz-ia && uv pip install --python herramientas/.voz-ia/bin/python clearvoice \
        && ok "voz IA (los modelos se bajan la primera vez que se usa)" || mal "No se pudo instalar ClearerVoice"
    fi
  fi
fi

echo
echo "Listo. Para comprobar que todo funciona:  bash herramientas/chequeo.sh"
