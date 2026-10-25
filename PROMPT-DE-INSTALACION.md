# Prompt de instalación

Sirve en **Mac** y en **Windows 10/11 (64 bits)**. Abre la app de Claude, entra a la pestaña **Code**, elige
una carpeta cualquiera (por ejemplo, Documentos) y pega esto completo:

```text
Quiero instalar «Editar con IA» para editar mis videos de Reels y TikTok. No soy técnico: háblame en
español simple, frases cortas, y explícame cada paso antes de hacerlo.

0. Fíjate qué computadora tengo (lo ves en tu entorno; si dudas, corre uname o echo $env:OS) y dímelo
   en una línea: «Tu computadora es Mac» o «Tu computadora es Windows». Sigue sólo los pasos de esa.
   Necesito ~5 GB libres; si no los tengo, avísame antes de empezar.
1. Si es Windows: revisa git --version. Si no está, pídeme permiso para correr
   winget install --id Git.Git -e (si Windows pregunta «¿Permitir cambios?», le doy Sí yo).
2. Pregúntame en qué carpeta lo quiero (sugiere Documentos/editar-con-ia). Clona ahí
   https://github.com/parcerosmx/editar-con-ia y trabaja desde esa carpeta.
3. Lee CLAUDE.md y el instalador de mi computadora (Mac: herramientas/instalar.sh; Windows:
   herramientas/instalar.ps1). Explícame en 5 líneas, sin jerga, qué se va a instalar, cuánto pesa
   (el modelo de voz son ~1,6 GB) y que todo corre en mi computadora. Pregúntame si sigo.
4. Con mi sí, corre el instalador:
   - Mac:     bash herramientas/instalar.sh --si
   - Windows: powershell -ExecutionPolicy Bypass -File herramientas/instalar.ps1 -Si
   Nunca escribas mi contraseña. Si falta Homebrew (Mac) o winget (Windows), dime en palabras simples
   qué hacer, espera a que te diga «listo» y vuelve a correrlo. Si falla algo, arréglalo tú y dime en
   una línea qué pasó.
5. Corre el chequeo y dime el resultado en 3 líneas (✅ lo que funciona, ❌ lo que no):
   - Mac:     bash herramientas/chequeo.sh
   - Windows: powershell -ExecutionPolicy Bypass -File herramientas/chequeo.ps1
6. Primer uso: pídeme de 3 a 5 videos que me gusten (míos o de otros; archivos o links) y dime que los
   ponga en material/04-referentes/. Cuando te diga «listo», usa la skill aprender-mi-estilo: mídelos,
   pregúntame sólo lo que no puedas medir y enséñame mi hoja de estilo para que la apruebe.
7. Después, pídeme las tomas de mi primer video (en material/02-a-camara/ y material/01-tomas-de-apoyo/)
   y edítalo con montar-video y capas-y-subtitulos, un paso a la vez, enseñándome cada versión.

Reglas: nunca publiques nada; yo subo los videos. Pregúntame antes de instalar o borrar cualquier cosa.
```

¿Prefieres que te lo instale y te enseñe con tus videos? → [maopinzon.com/edicion-ia](https://maopinzon.com/edicion-ia)
