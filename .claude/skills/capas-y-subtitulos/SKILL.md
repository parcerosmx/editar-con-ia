---
name: capas-y-subtitulos
description: Le pone las capas a un video ya montado —subtítulos palabra por palabra, gancho de texto, letreros con un dato, riser, woosh, ding y música— sin tapar la voz, y lo deja listo para publicar en calidad y en copia ligera para el celular. Mide en vez de oír, enseña una muestra antes de montar y obliga las reglas de sonido (dings 24 dB bajo la voz, nunca dos risers pegados). Úsalo cuando digan «ponle subtítulos», «subtítulos palabra por palabra», «ponle el gancho», «un letrero con…», «ponle música», «ponle efectos», «déjalo listo para publicar», «entrégamelo».
---

# Capas y subtítulos

**Lee primero `estilo/hoja-de-estilo.md`**: tamaño y color de subtítulos, márgenes de sonido, música. Sus números
mandan sobre los de aquí (que son los de `estilo/ejemplo-mao.md`).

Regla de oro: yo mido, propongo y armo una muestra; **el dueño aprueba**. La música la elige él entre 3. Nada se publica.

## El orden (de menos a más esfuerzo, y el gancho de texto AL FINAL)
riser → letreros con datos → subtítulos → efectos y música → **gancho de texto, lo último** (con el video ya armado).
Cada parte cierra con una versión numerada (`<video>_v1`, `_v2`…) en `proyectos/<video>/`.

## 0 · Ver el video
`revisar-video` sobre el video montado: transcripción, hojas, volumen. Si viene de tomas crudas, primero `montar-video`.

## 1 · Plan de capas (se acuerda antes de hacer nada)
Una tabla corta: **momento · palabra que lo dispara · capa**. Lo subjetivo se marca como muestra opcional.
Reglas: nunca tres letreros seguidos (fecha, lugar y hora en uno solo); mientras hay letrero, no hay subtítulo;
nada sobre una cara; todo dentro de la zona segura (y entre 205 y 1550 en 1920).

## 2 · Tiempos de cada palabra
```bash
.venv/bin/python herramientas/tiempos_voz.py VIDEO --json proyectos/<video>/palabras.json --prompt "platos, nombres"
```
Tres pasadas de Whisper, mediana y rango; **desconfía de lo que trae «?»**. Corrige a mano el JSON: nombres
propios, y lo que se quiso decir (el «o no» de un error de dicción no se subtitula). Sobre una canción, Whisper
no sirve palabra por palabra (se desfasa hasta 1 s): subtítulos por verso, escritos a mano.

## 3 · Subtítulos
```bash
.venv/bin/python herramientas/subtitulos.py proyectos/<video>/palabras.json proyectos/<video>/subs \
  --video VIDEO --salida proyectos/<video>/<video>_v1.mp4 --tam 60 --y 1250 --color "#FFFFFF" [--grandes 2x1,HOY]
```
Valores de la hoja de estilo. Deja también `subtitulos.srt` (para CapCut o para subirlo a la red).

## 4 · Muestra antes de montar
```bash
.venv/bin/python herramientas/hoja_cuadros.py proyectos/<video>/<video>_v1.mp4 1.0 2.5 4.0 --zona-segura \
  --salida proyectos/<video>/hoja.jpg --muestra 0 3
```
Mira la hoja: que nada tape una cara ni caiga bajo la interfaz (franjas rojas). Manda la muestra (2–3 s con sonido)
y **espera su visto bueno**. Si es subjetivo, dos variantes.

## 5 · Efectos y música
Los efectos propios están en `material/03-musica-y-efectos/` (`risers/`, `efectos/`; los hace `sintetizar_efectos.py`).
La música: **libre de derechos o comprada** (Pixabay Music, Mixkit, YouTube Audio Library) en
`material/03-musica-y-efectos/musica/`, o se pone en la app al subir. **Tres canciones para elegir, siempre.**
```bash
.venv/bin/python herramientas/mezclar.py proyectos/<video>/mezcla.json proyectos/<video>/<video>_v2.mp4   # ejemplo: ejemplos/mezcla.json
```
`mezclar.py` hace cumplir: **dings ≥ 24 dB bajo la voz** (aturden), **nunca dos risers pegados** (se detiene; el
segundo riser va más bajo y de otro tipo), efectos 10 dB y música 18 dB bajo la voz, final a −14 LUFS. El riser
arranca en el segundo 0 y su punto alto cae al terminar la frase del gancho (`"desde"` recorta el riser por delante).
El informe dice cuánto quedó cada cosa bajo la voz. **Si «suena bien» lo decide el dueño**: yo no oigo.

## 6 · Gancho de texto (lo último)
Propón 3 versiones cortas (de lo que dice el video; si hay chiste, el texto sirve al chiste y no adelanta la noticia).
Él elige y:
```bash
.venv/bin/python herramientas/texto_en_pantalla.py proyectos/<video>/<video>_v2.mp4 proyectos/<video>/<video>_v3.mp4 \
  "El taco que nadie pide" --hasta 4 --y 330 [--muestra]
```
Avisa si tapa una cara (Vision) o se sale de la zona segura.

## 7 · Entregar
```bash
.venv/bin/python herramientas/entregar.py proyectos/<video>/<video>_v3.mp4 <video>_final [--comparar <video>_v2.mp4]
```
Verifica formato, audio y volumen; deja la calidad y una copia ligera (≤ 30 MB) para mandarse por AirDrop o
WhatsApp. Recuerda en una línea lo que sigue sin confirmar (ortografía de nombres, un dato). **Publicar lo hace el
dueño** desde su celular, cuando lo apruebe.

## Lo que esta skill no hace
- No oye ni ve el video corriendo: **mide** (energía, hojas, Vision, LUFS).
- No genera con IA el local, la gente ni los platos propios sin fotos reales (sin ellas sale una tortilla donde
  decía arepa).
- No usa música con derechos de terceros ni audios bajados de páginas de descarga.
- No mete capas que el dueño no aprobó.
