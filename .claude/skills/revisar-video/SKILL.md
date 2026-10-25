---
name: revisar-video
description: Primera opción para revisar un video o un audio como si lo vieras y lo oyeras. Transcribe lo que se dice con el segundo exacto (whisper.cpp, local), saca los cuadros de cada toma (ffmpeg) y mide volumen, silencios y ritmo; si hay guion, marca palabra por palabra qué cambió. Úsalo antes que cualquier otra cosa cuando pasen un video (.mp4, .mov…), un audio o un link de TikTok, Instagram, Facebook o YouTube, o digan «revisa este video», «qué dice», «transcríbelo», «mira la toma», «el video que te acabo de pasar», «el último video».
---

# Revisar un video

No puedo abrir video ni audio: leo **texto** e **imágenes**. `revisar.py` convierte el video en las dos
cosas, todo en esta computadora (Mac o Windows). Nada sale a internet, salvo la descarga cuando el dueño da un link.

Al dueño le toca sólo pasar el video. Lo demás lo hago yo, y pregunto sólo lo que no puedo deducir (por
ejemplo, contra qué guion comparar, si no es obvio).

> **En Windows**, donde dice `.venv/bin/python` va `.venv/Scripts/python.exe`; lo demás es igual.

## 1 · Preparar

```bash
.venv/bin/python .claude/skills/revisar-video/revisar.py <archivo | link | ultimo> [--guion hablado.txt]
```
(Si no existe `.venv`: `/usr/bin/python3` en Mac, `python` en Windows. Si falta algo: `revisar.py verificar` y el
instalador: `bash herramientas/instalar.sh` en Mac, `powershell -ExecutionPolicy Bypass -File herramientas/instalar.ps1` en Windows.)

| Entrada | Qué pasa |
|---|---|
| ruta a un archivo | video o audio; si es sólo audio, sólo transcribe |
| link | lo baja yt-dlp a `proyectos/_revisiones/_descargas/`, con autor, fecha y cifras del post |
| `ultimo` | el video más reciente de `material/`, Descargas, Escritorio o Películas (ahí cae lo que llega por AirDrop). **Di cuál tomaste.** |

- **`--guion`**: un `.txt` con **sólo lo que se dice** (sin títulos ni acotaciones).
- **`--cada N`**: un cuadro cada N segundos (por defecto 1; en videos largos se espacia solo).
- **`--idioma`**: `es` por defecto; `auto` si no es español.
- El mismo archivo no se procesa dos veces: se reusa lo hecho. `--rehacer` empieza de cero.

Si el link pide sesión (Instagram suele pedirla): **no insistas y nunca uses las cookies del navegador.**
Pide que lo bajen desde la app y lo pongan en `material/04-referentes/`.

## 2 · Mirar, en este orden

1. **`informe.md`**: el archivo, cómo suena, la transcripción con tiempos, la comparación contra el guion y la
   línea de tiempo (cada cuadro al lado de lo que se dice en ese segundo).
2. **`hojas/`**: 12 cuadros por imagen, con la hora encima y un punto rojo donde cambia la toma. En videos
   cortos, míralas **todas**.
3. **`fotogramas/`**: resolución completa, **sólo** para un detalle (texto en pantalla, una cara, el fondo).
4. Si algo pasa entre dos cuadros:
   `.venv/bin/python .claude/skills/revisar-video/revisar.py denso <carpeta-o-archivo> <desde> <hasta>`
   saca cuadros cada 0,2 s en esa ventana.

## 3 · Entregar

Primero lo que se pidió. Si no se pidió nada puntual:
- **Lo que se dice**: la transcripción limpia. Con guion, los cambios con su segundo (➕ agregado · ✏️ cambiado ·
  ➖ omitido). Lo agregado es lo que más importa: por ahí se cuelan las frases improvisadas.
- **Lo que se ve**: los primeros dos segundos (el gancho), quién sale, qué hay al fondo, el texto en pantalla
  (¿se lee? ¿lo tapa la interfaz de la red?), encuadre y luz.
- **Cómo suena**: volumen, en qué segundo entra la voz, ritmo, pausas largas.
- **Duración.** Cita siempre el segundo (`0:12`).

## Lo que no puedo (se dice, no se disimula)

- **No oigo el tono.** Si suena cansado, sarcástico o a la defensiva lo decide quien lo escucha.
- **Veo cuadros sueltos, no movimiento.** Para eso está `denso`.
- **Whisper se equivoca.** Confunde nombres propios, a veces borra muletillas y **sobre música o silencio inventa
  frases** (el informe marca con ⚠️ las típicas: «Suscríbete», «Gracias por ver»). Si una palabra decide algo,
  cítala con su segundo y pide que el dueño la escuche.

## Dónde queda cada cosa

- **El trabajo** (cuadros, transcripción, informe): `proyectos/_revisiones/<fecha>-<nombre>-<huella>/`. No se sube al repo.
- **Las conclusiones** van en la conversación; a un archivo sólo si el dueño lo pide.
- **`vocabulario.txt`**, junto a este archivo: nombres que Whisper tiene que reconocer (el negocio, los platos).
  Si escribe mal un nombre que se repite, se agrega ahí. **Sólo nombres, nunca frases con postura.**
