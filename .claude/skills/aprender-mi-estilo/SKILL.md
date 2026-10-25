---
name: aprender-mi-estilo
description: Aprende el estilo de edición del dueño a partir de 3 a 5 videos de referencia (suyos o de otros que le gustan, en archivo o link) y llena estilo/hoja-de-estilo.md con números medidos (duración de las tomas, % de cara a cámara, pausas, subtítulos, música, color), preguntando sólo lo que no se puede medir. Úsalo cuando digan «aprende mi estilo», «quiero que mis videos se vean así», «estos son mis referentes», «mide estos videos», «hazme la hoja de estilo», «mi primer uso», o pasen varios videos que les gustan.
---

# Aprender mi estilo

El dueño pasa de 3 a 5 videos que le gustan. Yo los mido, propongo su hoja de estilo ya llena y él confirma.
**Nunca le pido que describa su estilo con palabras**: lo saco de los videos. Sólo pregunto lo que no se puede
medir, y con opciones para elegir, no con preguntas abiertas.

Dimensiona en una línea: 🟢 3 videos propios · 🟡 5 referentes con links · 🔴 más de 5 (propón quedarse con 5).

## 1 · Juntar los videos (lo único que hace el dueño)

- Archivos: que los ponga en `material/04-referentes/` (o que diga dónde están; «el último» también sirve).
- Links: `revisar.py <link>` los baja. Si piden sesión (Instagram), que los baje desde la app; nunca cookies.
- Mejor si son **del mismo tipo** de video que quiere hacer (a cámara con comida, historias, etc.). Si mezcla
  tipos, dilo y mide cada grupo aparte.
- Si no tiene referentes, ofrécele empezar con `estilo/ejemplo-mao.md` como base y ajustarlo después.

## 2 · Mirar cada video

Por cada video, `revisar-video` (lee su `SKILL.md`): transcripción, hojas y volumen. Con más de 3 videos, un
subagente por video, en paralelo, con este encargo (no escriben archivos):

> Revisa <archivo> con `.venv/bin/python .claude/skills/revisar-video/revisar.py <archivo>` (lee antes
> `.claude/skills/revisar-video/SKILL.md`; mira informe.md y todas las hojas). Devuelve en ≤200 palabras: estilo
> (a cámara · voz en off · sketch), gancho literal con su segundo, estructura en 3-5 tiempos, qué tomas se ven,
> cómo son los subtítulos (posición, tamaño, color, mayúsculas, fuente aproximada), música o efectos que se notan
> en la transcripción, y por qué crees que funciona. No escribas archivos.

## 3 · Medir con números

```bash
.venv/bin/python herramientas/medir_estilo.py material/04-referentes/<video1> material/04-referentes/<video2> ...
```
(Con links, pasa los archivos que bajó `revisar.py` a `proyectos/_revisiones/_descargas/`.)

Da por video y en mediana: **ritmo** (toma mediana, la más corta, cortes en los primeros 3 s), **cara** (% a
cámara con Vision), **texto** (altura, tamaño, mayúsculas, tonos, el gancho de texto), **voz** (palabras por
minuto, pausas, fondo de música bajo la voz), **sonido** (LUFS) y **color** (luz, contraste, saturación, calidez).

**Revisa las hojas** `proyectos/_estilo/tomas-*.jpg` (cada toma marcada CARA o apoyo): Vision cuenta como
«cara» cualquier cara grande (un futbolista en la tele, alguien de fondo). Corrige el % si hace falta y dilo.

**Si edita en CapCut**: `.venv/bin/python herramientas/leer_capcut.py "<nombre del proyecto>"` lee su proyecto
sin tocarlo y dice cuánto duran sus piezas y cuánto encima al cambiar de toma. Es la mejor fuente: su propio corte.

**Su color**: si quiere que el color salga como el suyo, pídele un par «antes y después» (el mismo video sin color
y con su color, misma duración) y corre `herramientas/aprender_color.py ANTES DESPUES` → `estilo/mi-color.cube`.
Si el error en cuadros no vistos no baja mucho, dile que su color es toma por toma y que lo siga poniendo en su app.

## 4 · Preguntar sólo lo que falta

Una sola ronda, con opciones (usa la herramienta de preguntas si está, o una lista numerada):
- De qué es su negocio y a quién le habla (si no está ya en la hoja, sección 0).
- Qué tipo de música quiere y de dónde la saca (libre de derechos, comprada o la de la app al subir).
- Lo que **nunca** quiere ver en un video suyo.
- Si alguna medida le sorprende (p. ej. «tus referentes tienen 65 % de cara: ¿quieres eso o más comida?»).

## 5 · Proponer la hoja y confirmar

Llena `estilo/hoja-de-estilo.md` con los números, cada uno con su nivel (🟢 medido · 🟡 observado · 🔴 supuesto)
y de qué video sale. Enséñale un resumen de 8–10 líneas («tus tomas duran 0,9 s, la cara sale 25 %, subtítulos
blancos de ~66 px a la altura del pecho…») y **espera su sí** antes de darla por buena. Lo que corrija, manda.

Cierra diciendo en una línea que ya puede editar su primer video («pon tus tomas en `material/02-a-camara/` y dime
"monta mi video"»). No abras más tareas.

## Lo que no hago

- No copio el video de otro: aprendo su ritmo, no su contenido.
- No invento medidas: si algo no se pudo medir (Vision no respondió, no hay voz), lo digo y lo pregunto.
- Los videos de referencia no se suben al repo (viven en `material/`, que está fuera de git).
