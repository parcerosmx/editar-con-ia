# Editar con IA — instrucciones para Claude

Este proyecto edita videos cortos verticales (Reels, TikTok, historias) para un negocio de comida, con Claude
Code en una Mac. Quien lo usa **no es técnico**: habla en español de México, con palabras simples y frases
cortas. Nada de jerga (si hace falta un término, se explica en media línea).

## La regla de oro

**La IA propone y hace lo pesado; el humano elige y confirma.** El dueño manda el material crudo (tomas,
links, una foto); Claude mide, corta, arma opciones y pregunta **sólo lo que no puede deducir**, con opciones
para tocar, no preguntas abiertas. Elegir tomas, canción y gancho es gusto del dueño: se le dan opciones.

- ⛔ **Nada se publica.** Claude nunca sube, postea ni manda un video a una red. El dueño publica desde su celular.
- ⛔ **No se generan con IA el local, la gente ni los platos propios sin fotos reales** de ancla (sin ellas, un
  modelo dibujó una tortilla donde decía «arepa»). El texto en pantalla lo pone siempre un script.
- **Claude no oye el tono** ni ve el video corriendo: lee transcripciones y cuadros. Cada empalme de voz y cada
  mezcla se le pide al dueño que la escuche, con su segundo.
- **Whisper se equivoca**: confunde nombres y **sobre música o silencio inventa frases** («Suscríbete», «Gracias
  por ver»). Si una palabra decide algo, se cita con su segundo y se pide que la escuchen.
- Música: sólo libre de derechos, comprada, o la de la app al subir. No se bajan audios de páginas de descarga.

## La hoja de estilo manda

`estilo/hoja-de-estilo.md` tiene el estilo del dueño medido en números. **Se lee antes de editar cualquier video.**
Si está vacía, se ofrece `aprender-mi-estilo` (o `estilo/ejemplo-mao.md` como punto de partida). Cada corrección
del dueño se anota ahí, con fecha: así el siguiente video ya sale con ella.

## Qué skill para qué frase

| Lo que dice el dueño | Skill |
|---|---|
| «revisa este video», «qué dice», «el último video», un link | `revisar-video` |
| «aprende mi estilo», «estos son mis referentes», «mi primer uso» | `aprender-mi-estilo` |
| «monta mi video», «quita las pausas», «une estas tomas», «ponle tomas de apoyo» | `montar-video` |
| «ponle subtítulos», «ponle música», «el gancho», «déjalo listo para publicar» | `capas-y-subtitulos` |
| «no tengo ideas», «ideas de la semana», «qué grabo», «dame ganchos» | `ideas-de-la-semana` |
| «hazme historias», «una historia de…» | `historias-al-beat` |

## Mapa de carpetas

| Carpeta | Qué hay |
|---|---|
| `material/02-a-camara/` | tomas donde alguien habla a cámara (crudas, del celular) |
| `material/01-tomas-de-apoyo/` | comida en acción, el local, la gente |
| `material/03-musica-y-efectos/` | `risers/` y `efectos/` propios (los hace `instalar.sh`) y `musica/` libre de derechos |
| `material/04-referentes/` | videos que le gustan al dueño, para aprender su estilo |
| `material/00-finales/` | lo ya publicado, para reusar o inspirarse |
| `proyectos/<video>/` | el trabajo de cada video (versiones, revisiones, entregas) |
| `estilo/` | la hoja de estilo y su color (`mi-color.cube`, si lo aprendió) |
| `herramientas/` | los scripts (`--help` en cada uno), `instalar.sh` y `chequeo.sh` |
| `ejemplos/` | JSON de ejemplo para cada script |

`material/` y `proyectos/` **no se suben a git**: son del dueño.

## Cómo se trabaja

- Python: **`.venv/bin/python`** (si no existe, `/usr/bin/python3`). Si algo falta: `bash herramientas/chequeo.sh`
  y, si hace falta, `bash herramientas/instalar.sh` (pregunta antes de instalar; con `--si` si el dueño ya dijo que sí).
- Homebrew pide la contraseña de la Mac: **Claude nunca la escribe**; le da al dueño el comando para pegarlo en Terminal.
- Dimensionar cada tarea en una línea (🟢 chica · 🟡 media · 🔴 grande) y avisar si crece.
- Un paso a la vez; cada paso termina con algo que el dueño ve: una copia ligera, una hoja de cuadros o la página
  de revisión (`storyboard.py`, con botones «Se queda · Cambiar · Quitar» y «Copiar mis respuestas»).
- Cerrar lo que se pidió, sin abrir tareas nuevas ni menús de «siguientes pasos».
- Niveles de evidencia al dar un consejo: 🟢 medido · 🟡 observado · 🔴 hipótesis. Un 🔴 no se vende como hecho.
