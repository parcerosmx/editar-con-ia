# Prompt de instalación

Abre la app de Claude en tu Mac, entra a la pestaña **Code**, elige una carpeta cualquiera (por ejemplo,
Documentos) y pega esto completo:

```text
Quiero instalar «Editar con IA» para editar mis videos de Reels y TikTok. No soy técnico: háblame en
español simple, frases cortas, y explícame cada paso antes de hacerlo.

1. Pregúntame en qué carpeta lo quiero (sugiere Documentos/editar-con-ia). Clona ahí
   https://github.com/parcerosmx/editar-con-ia y trabaja desde esa carpeta.
2. Lee CLAUDE.md y herramientas/instalar.sh. Explícame en 5 líneas, sin jerga, qué se va a instalar,
   cuánto pesa (el modelo de voz son ~1,6 GB) y que todo corre en mi Mac. Pregúntame si sigo.
3. Con mi sí, corre: bash herramientas/instalar.sh --si
   - Si falta Homebrew, NO escribas mi contraseña: dime qué comando pegar en la app Terminal, espera a que
     te diga «listo» y vuelve a correr el instalador.
   - Si falla algo, arréglalo tú y dime en una línea qué pasó.
4. Corre bash herramientas/chequeo.sh y dime el resultado en 3 líneas (✅ lo que funciona, ❌ lo que no).
5. Primer uso: pídeme de 3 a 5 videos que me gusten (míos o de otros; archivos o links) y dime que los
   ponga en material/04-referentes/. Cuando te diga «listo», usa la skill aprender-mi-estilo: mídelos,
   pregúntame sólo lo que no puedas medir y enséñame mi hoja de estilo para que la apruebe.
6. Después, pídeme las tomas de mi primer video (en material/02-a-camara/ y material/01-tomas-de-apoyo/)
   y edítalo con montar-video y capas-y-subtitulos, un paso a la vez, enseñándome cada versión.

Reglas: nunca publiques nada; yo subo los videos. Pregúntame antes de instalar o borrar cualquier cosa.
```

¿Prefieres que te lo instale y te enseñe con tus videos? → [maopinzon.com/edicion-ia](https://maopinzon.com/edicion-ia)
