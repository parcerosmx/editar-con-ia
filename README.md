# Editar con IA

**Edita tus Reels y TikToks con Claude Code, en tu Mac, con tu propio estilo.**

Para dueños de restaurantes, cafeterías, taquerías, panaderías y cualquier negocio de comida que quiere
publicar videos sin pasarse la noche editando. Tú grabas con el celular y eliges; la IA corta, mide, arma
opciones y te enseña cada versión. **Nada se publica sin tu OK: tú subes el video.**

Hecho por **Mao Pinzón**, ingeniero de software con restaurante · [maopinzon.com/edicion-ia](https://maopinzon.com/edicion-ia)

---

## Cómo se usa, en 5 pasos

**1 · La carpeta.** Instala la app de Claude en tu Mac y entra a la pestaña **Code**. Pega el
[prompt de instalación](PROMPT-DE-INSTALACION.md): Claude baja esta carpeta a tu Mac y te explica todo.

**2 · Las herramientas.** Claude te dice qué va a instalar y te pregunta antes. Son programas gratis que
corren en tu Mac (ffmpeg para el video, Whisper para entender lo que se dice). Al final corre un chequeo
y te dice ✅ o ❌. Tarda de 10 a 20 minutos, casi todo es esperar la descarga.

**3 · Tu estilo.** Pon de 3 a 5 videos que te gusten en `material/04-referentes/` (tuyos o de otros) y dile
**«aprende mi estilo»**. Claude los mide: cuánto dura cada toma, cuánto sale tu cara, cómo son los
subtítulos, la música, el color. Te pregunta sólo lo que no puede medir y te enseña tu **hoja de estilo**
para que la apruebes.

**4 · Del clip al video.** Pon tus tomas en `material/02-a-camara/` (donde hablas) y
`material/01-tomas-de-apoyo/` (la comida, el local) y dile **«monta mi video»**. Claude quita las pausas,
une las tomas, te enseña opciones de tomas de apoyo para que elijas tocando botones, y luego le pone
subtítulos, música y efectos.

**5 · Revisar y publicar.** Cada versión te llega como una página con botones (**Se queda · Cambiar ·
Quitar**) o como un video ligero para tu celular. Cuando digas «aprobado», te deja el video final en
calidad. **Lo subes tú**, cuando quieras.

## Qué le puedes pedir

| Dile… | Skill | Qué hace |
|---|---|---|
| «revisa este video», «qué dice», un link | `revisar-video` | Lo transcribe con el segundo exacto, saca los cuadros de cada toma y mide el sonido |
| «aprende mi estilo», «estos son mis referentes» | `aprender-mi-estilo` | Mide tus videos favoritos y llena tu hoja de estilo |
| «monta mi video», «quita las pausas», «ponle tomas de apoyo» | `montar-video` | Del clip crudo a la base cortada, con opciones para elegir |
| «ponle subtítulos», «ponle música», «déjalo listo» | `capas-y-subtitulos` | Subtítulos, gancho de texto, efectos y música sin tapar la voz, y la entrega |
| «no tengo ideas», «qué grabo esta semana» | `ideas-de-la-semana` | 10 ideas, 10 ganchos y la lista de tomas para grabar |
| «hazme historias» | `historias-al-beat` | Historias de 15–20 s con tomas cortadas al ritmo de la canción |

## Qué necesitas

- Una **Mac** (con chip M1 o más nueva va mejor; probado en macOS 15).
- La app de **Claude** con un plan de pago (Pro o Max), que incluye Claude Code.
- ~3 GB libres en el disco para las herramientas, más el espacio de tus videos.
- Tus tomas, grabadas en vertical con el celular.

## Lo que NO hace

- **No publica.** Ni sube, ni postea, ni manda nada a tus redes.
- **No inventa tu local ni tus platos con IA.** Sin fotos reales, un modelo dibujó una tortilla donde
  decía «arepa». La comida que se ve es la tuya.
- **No oye el tono.** Lee lo que se dice y mide el volumen, pero si una frase suena cansada o rara lo
  decides tú. Por eso te pide escuchar cada unión, con su segundo.
- **No reemplaza tu gusto.** Elegir la toma, la canción y el gancho es tuyo: te da opciones.
- **No usa música con derechos de otros.** Usa música libre de derechos o la de la app al subir.
- No corre en Windows tal cual (usa herramientas de la Mac, como Vision para detectar caras y textos).

## Lo que aprendí editando así (y lo que me costó)

Las medidas de mis videos están en [`estilo/ejemplo-mao.md`](estilo/ejemplo-mao.md), con su nivel de
evidencia. Son **lo que me funcionó a mí**, no una ley: todavía no las crucé con datos de retención.

- **La cara a cámara, poco: 20–25 % del video.** El resto, comida en acción. Mi versión tenía 47 % y la de
  mi editor, 20 %. Ganó la de él.
- **Tomas de apoyo de ~0,8 s.** Retención sí, mareo no: ninguna de menos de ~0,75 s.
- **La voz nunca se calla.** Pausas de 0,03 a 0,06 s entre palabras. Al cambiar de toma, la siguiente entra
  0,18 s encima de la anterior.
- **Los tiempos de Whisper corren hasta ±0,4 s.** Por eso los cortes se deciden midiendo el silencio, no con
  la transcripción. Y sobre la música, Whisper inventa frases.
- **La mejora de voz, sobre la toma entera.** Por pedazos, cada pedazo queda a otro volumen.
- **El color, una sola vez.** Con filtros encima de filtros, la comida se ve roja.
- **Los dings, 24 dB por debajo de la voz.** Más fuertes aturden. Y nunca dos risers pegados.
- **Diez ganchos antes del guion.** La vez que me lo salté, rehice todo.
- **El gancho de texto, al final.** Con el video ya armado, no antes.
- **Opciones antes de montar.** Cada vez que la IA eligió las tomas sola, hubo que rehacer.

## Para los curiosos

- Cada script de `herramientas/` tiene `--help`. Todo corre en tu Mac; sólo se conecta a internet para
  instalar y para bajar un video cuando le das un link.
- `bash herramientas/chequeo.sh` arma un video de prueba de 6 s (con la voz de la Mac, sin material de nadie)
  y lo pasa por todo el proceso.
- `bash herramientas/instalar.sh --voz` agrega una IA local para mejorar la voz (opcional, ~2–5 GB).

## Licencia

MIT. Úsalo, cámbialo y compártelo. Ver [LICENSE](LICENSE).

---

¿Prefieres que te lo instale y te enseñe con tus videos? → [maopinzon.com/edicion-ia](https://maopinzon.com/edicion-ia)
