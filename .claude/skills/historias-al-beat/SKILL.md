---
name: historias-al-beat
description: Arma historias de Instagram o Facebook (9:16, ~15–20 s) con tomas antojables cortadas al ritmo de una canción y un texto fijo arriba («ya abrimos», «hoy hay…», un horario, un antojo). Úsalo cuando digan «hazme historias», «una historia de…», «historias al ritmo de la música», «una historia para hoy», o pasen tomas de comida para historias.
---

# Historias al beat

Regla de oro: el dueño pasa las tomas y dice qué quiere anunciar; yo elijo los tramos, propongo el texto y 3
canciones, armo, y **él aprueba**. Nada se publica.

## 1 · Qué anuncia y el texto
Una o dos líneas cortas, arriba (la interfaz tapa ~250 px arriba y ~330 abajo). Datos del negocio (horario,
dirección, cómo pedir) **sólo como el dueño los dé o como estén en su hoja de estilo**, nunca de memoria. Propón
2–3 versiones del texto y que elija.

## 2 · Las tomas
De `material/01-tomas-de-apoyo/` (o las que mande). `revisar-video` para ver sus hojas y elegir **el segundo donde
la acción YA pasa** (el queso se estira, el jugo cae, la mordida cruje), nunca el «antes». Reglas:
- 5–9 tomas de ~2 s (o 4 golpes); la primera, la que más antoja.
- Todo del plato que nombra el texto.
- Una misma toma, máximo en 2 historias.
- Nada de tomas donde se espera en vez de actuar, lluvia, calle sucia o cajas. Si faltan tomas buenas, se dice y se
  propone qué grabar; no se rellena con tomas flojas.

## 3 · La canción
**Tres opciones**, libres de derechos o compradas, en `material/03-musica-y-efectos/musica/`. Si el dueño prefiere
la música de Instagram, se arma sin canción (`"bpm": 120`) y la pone al subir.

## 4 · Armar
Escribe `proyectos/historias/<nombre>.json` (ejemplo en `ejemplos/historia.json`) y:
```bash
.venv/bin/python herramientas/historias_al_beat.py proyectos/historias/<nombre>.json --hoja
```
Mide el pulso de la canción y cada corte cae en un golpe; corre la entrada si una toma tiene un corte adentro;
−14 LUFS. Con `"lut": "estilo/mi-color.cube"`, su color, una sola vez. Mira la hoja antes de mandar.

## 5 · Entregar
`entregar.py` deja la copia ligera para el celular. Una versión por canción si pidió elegir. **Él la sube.**
