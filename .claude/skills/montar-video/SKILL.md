---
name: montar-video
description: Monta un video vertical donde alguien habla a cámara, desde las tomas crudas del celular hasta la base cortada: quita las pausas, une las tomas como un editor (entrada con la voz, 0,18 s encimadas), limpia la voz, arma opciones de tomas de apoyo para que el dueño elija tocando botones, y verifica que no se haya comido palabras. Úsalo cuando digan «monta mi video», «edita estas tomas», «quita las pausas», «une estas tomas», «ponle tomas de apoyo», «quita esta frase», «que diga…», o pasen una carpeta de clips para editar.
---

# Montar un video a cámara

**Antes de empezar, lee `estilo/hoja-de-estilo.md`** (si está vacía, ofrece correr primero `aprender-mi-estilo`
o usar `estilo/ejemplo-mao.md` como base). Sus números mandan sobre los de aquí.

La regla de oro: **yo hago lo pesado y propongo; el dueño elige y confirma.** Elegir la toma, la frase y las
tomas de apoyo es gusto suyo: se le dan opciones, no se adivina. Nada se publica.

Dimensiona en una línea (🟢 una toma corrida · 🟡 varias tomas y tomas de apoyo · 🔴 guion nuevo con muchas tomas)
y di en qué paso vamos. **Un paso a la vez; cada paso termina con algo que el dueño ve** (un video ligero o la
página de revisión). Todo el trabajo va en `proyectos/<nombre-del-video>/`.

## Los pasos

### 1 · Ver el material
Tomas a cámara en `material/02-a-camara/`, tomas de apoyo en `material/01-tomas-de-apoyo/` (o donde diga el
dueño; «el último» = lo más reciente). `revisar-video` sobre cada toma a cámara: qué dice, con su segundo.
Si hay guion, `--guion`. Arma una tabla corta: **parte del guion · toma(s) donde se dice bien · segundo**.

### 2 · Aprobar la selección EN CRUDO (antes de limpiar nada)
Propón qué toma va en cada parte (elegida + suplentes) y el texto de lo que quedaría dicho. Una unión rápida:
```bash
.venv/bin/python herramientas/unir_tomas.py proyectos/<video>/plan.json      # ejemplo: ejemplos/plan-unir.json
```
Manda el resultado y el texto. **Sólo con su sí se sigue** (no se limpia voz ni se pone color a algo que no va).

### 3 · Voz (sobre cada toma ENTERA, antes de cortar)
```bash
.venv/bin/python herramientas/limpiar_voz.py TOMA proyectos/<video>/tomas/TOMA.mp4 [--ruido] [--ia]
```
Por pedazos no: cada pedazo queda a otro volumen (🟢). Si el dueño usa la «mejora de voz» de CapCut, que la
aplique a la toma entera y aquí sólo se corta. Una toma corrida sin cortes de parte: `quitar_pausas.py`.

### 4 · Unir como un editor
`unir_tomas.py plan.json` con las tomas limpias: cada toma entra con la voz y sale cuando se apaga la última
palabra; pausas internas a ~0,03 s; **0,18 s encimadas** al cambiar de toma si la palabra cae despacio; su color
(`"lut": "estilo/mi-color.cube"`) **una sola vez**. Para una sola toma larga:
```bash
.venv/bin/python herramientas/quitar_pausas.py TOMA proyectos/<video>/base.mp4 --desde 0.4 --hasta 37.2
```
Los **saltos** que imprime (y el `.json`) son el borde exacto entre palabras: ahí se pegan las tomas de apoyo.
Para quitar o cambiar una frase: `palabras.py empalme` prueba el empalme ANTES de montarlo.

### 5 · Verificar antes de mandar
```bash
.venv/bin/python herramientas/verificar_base.py proyectos/<video>/base.mp4 --guion proyectos/<video>/hablado.txt
```
Restos de rodaje («listo», conteos), palabras del guion que no se oyen, huecos > 0,25 s, volumen, parpadeos y
cuadros negros. **No oigo el tono**: cada unión se la pido que la escuche, con su segundo.

### 6 · Revisión tocando botones
```bash
.venv/bin/python herramientas/storyboard.py version proyectos/<video>/base.mp4 proyectos/<video>/revision-1 --dudas dudas.txt
open proyectos/<video>/revision-1/index.html
```
Cada tramo con su clip y **Se queda · Cambiar · Quitar**. Las dudas (lo que Whisper oyó dudoso) van arriba.
El dueño toca «Copiar mis respuestas» y las pega aquí. Si prefiere verlo corrido, `entregar.py` deja la copia ligera.

### 7 · Tomas de apoyo: opciones primero
Parte el guion en ideas («el queso que se estira», «el local lleno») y por cada una busca hasta 10 tomas en
`material/01-tomas-de-apoyo/` (mira sus hojas con `revisar-video`; elige el tramo donde la acción **ya** pasa).
Arma `opciones.json` (ejemplo en `ejemplos/opciones.json`) y:
```bash
.venv/bin/python herramientas/storyboard.py opciones proyectos/<video>/opciones.json proyectos/<video>/opciones-1
```
**Él elige.** Después, cada toma entra con la palabra que muestra, en un salto, con la duración de su hoja de
estilo (ejemplo: mediana 0,8 s, nunca < 0,75 s salvo la ráfaga del arranque). La cara a cámara, en el gancho, los
giros y la invitación (ejemplo: 20–25 %). Se pegan sobre la base (la voz no se toca):
```bash
.venv/bin/python herramientas/poner_tomas.py proyectos/<video>/tomas.json proyectos/<video>/montado-v1.mp4
```
Avisa de parpadeos y dice qué % quedó a cámara. Verifica con `verificar_base.py` y `hoja_cuadros.py` en los saltos,
y manda la revisión (paso 6) otra vez.

### 8 · Lo que sigue
Subtítulos, gancho de texto, efectos y música son de `capas-y-subtitulos`. Dilo en una línea.

## Lo que más se equivocó (no repetir)
- Montar tomas de apoyo sin enseñar opciones, o elegirlas por el nombre del archivo sin mirarlas.
- Guiarse por los tiempos de Whisper: corren ±0,4 s. El borde lo dan los saltos de `quitar_pausas.py`.
- Usar una toma con un corte adentro, o volver a la cara pegado a un salto: parpadeo.
- Cortar una palabra con la voz a todo volumen: «se nota mal editado».
- Tratar una toma HDR del iPhone como normal: sale quemada (las herramientas ya la convierten).
- Apilar filtros de color: la comida se pasa a rojo.

## Cuando el dueño corrige algo
Su corrección se vuelve regla: agrégala a `estilo/hoja-de-estilo.md` (sección «Correcciones», con fecha). Así el
siguiente video ya sale con ella.
