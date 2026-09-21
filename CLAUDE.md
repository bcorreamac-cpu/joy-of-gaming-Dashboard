# Joy of Gaming · panel de analytics

Panel estático del canal de YouTube **Joy Of Gaming**, publicado en GitHub Pages
y actualizado solo todos los lunes por GitHub Actions.

Idioma del proyecto: **español**, incluidos comentarios y mensajes de commit.
Las respuestas al usuario van cortas y en lenguaje simple, sin jerga técnica
cuando se puede evitar.

---

## "Dame el prompt del lunes"

Cuando el usuario pida **el prompt del lunes**, el **prompt del CTR**, o algo
equivalente: leé `PROMPT_CTR.md` y devolvéle el **bloque del paso 2** listo para
copiar y pegar en la extensión de Claude en Chrome, más los comandos del paso 5.
No lo reescribas de memoria: está afinado y probado.

Es una rutina semanal de unos cinco minutos. Existe porque el API de YouTube
**no entrega impresiones ni CTR** —responde `The query is not supported`,
probado con permisos de dueño en tres formas distintas— y todo lo demás sí se
actualiza automáticamente.

---

## Cómo funciona

```
.github/workflows/actualizar.yml   lunes 11:00 UTC: baja, valida y publica
.github/workflows/latido.yml       diario: avisa si el permiso de Google caducó
scripts/yt_descargar.py            APIs de YouTube -> data/entrada/*.csv
scripts/build_analytics.py         CSV -> data/analytics.json
scripts/render_dashboard.py        analytics.json + plantilla -> dashboard.html
scripts/validar.py                 ¿los datos son coherentes consigo mismos?
scripts/guardia.py                 ¿no empeoran a los publicados?
scripts/ctr_actualizar.py          carga el CTR semanal en data/historico/
data/juegos.json                   juegos repetidos, para el ranking (editable)
scripts/yt_autorizar.py            permiso de Google (se corrió una sola vez)
```

`yt_descargar.py` escribe CSV con **los mismos encabezados que los exports de
YouTube Studio**, así que el resto del proceso no distingue si los datos
llegaron a mano o por API. Mantener esa compatibilidad al tocarlo.

---

## Reglas que no se negocian

- **Las dos puertas antes de publicar.** `validar.py` y `guardia.py` frenan el
  workflow si algo no cuadra. No se relajan para que una corrida pase: si
  fallan, hay un problema de datos. La única excepción es el input
  `aceptar_baja`, manual y para migraciones de fuente.
- **Los dos universos del switch nunca se mezclan.** OFF filtra por fecha de
  publicación y suma acumulados; ON filtra por fecha de la métrica. Cada KPI
  dice de cuál sale.
- **El índice relativo es mediana, nunca promedio.** Un video viral desfigura
  cualquier promedio: el 5 % de los videos genera el 55 % de las vistas.
- **El índice compara contra vecinos en el tiempo, no contra meses calendario.**
  Dos videos publicados con días de diferencia tienen que caer en la misma base.
- **CTR = suma(clicks) ÷ suma(impresiones).** Nunca el promedio de CTR.
  Por eso el histórico guarda clicks y no porcentajes.
- **El CTR siempre va atrás del resto.** Se carga a mano, así que los últimos
  días y los videos más nuevos no tienen impresiones. Eso es la frontera normal,
  no un agujero: lo que `validar.py` rechaza es un hueco en el medio.
- **No commitear `data/analytics.json` regenerado a mano.** Correr
  `build_analytics.py` en local lo rehace desde los CSV viejos de `data/entrada/`
  y pisa el que dejó el workflow, que es el real. `meta.fuente` dice de dónde
  salió cada uno y `guardia.py` lo detecta, pero lo sano es no subirlo: para
  probar el panel alcanza con `render_dashboard.py`.
- **Nada de números fijos en los chequeos.** Esto corre todas las semanas: todo
  lo que dependa del rango se deriva del rango.
- **La paleta está validada** (banda de luminosidad, croma, daltonismo,
  contraste). El color sigue a la categoría, nunca a su posición en una tabla.
- Tras tocar el panel: `python3 scripts/render_dashboard.py` y revisar que siga
  andando. Tras tocar los datos: `python3 scripts/validar.py`.

---

## Datos del canal

- Canal: `UCCIR3AdAbybtkNgINS9UyNA` (cuenta de marca; la personal del dueño es
  otra y está vacía, por eso el ID va explícito en los workflows).
- Ventana: desde **2024-01-01**. La define `DESDE` en `build_analytics.py`.
- El repo es **público a propósito**: el panel muestra ingresos y RPM. Decisión
  tomada por el usuario, no reabrirla salvo que la mencione.
- Las credenciales viven en los secrets del repo: `YT_CLIENT_ID`,
  `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

---

## Lo que dicen los datos (sept 2026)

- El canal **cae fuerte**: la mediana por video pasó de 4.260 vistas en 2024-H1
  a 958 en 2026-H2. Por eso existe el índice relativo: sin él, toda comparación
  histórica en vistas crudas miente.
- **La concentración es extrema**: el 5 % de los videos genera el 55 % de las
  vistas, y el mejor hace 75 veces la mediana. Cualquier análisis por promedio
  simple, o cualquier corte que deje grupos de menos de ~8 videos, es ruido.
- **Riders Republic rinde 7,3 veces lo normal** sostenido en 12 videos, y nueve
  de esos son de 2026, el peor momento del canal: es el juego, no la época.
  Steep 4,0x y Spider-Man 2 3,0x lo siguen de lejos.
- Con 237 videos largos **no da para cruzar muchas dimensiones** (primera vs.
  tercera persona, género, plataforma): los grupos quedan de 4 y un outlier
  decide el resultado. Retomarlo con 500+ videos.

## Cosas que ya se probaron y no funcionan

- **Impresiones y CTR por API.** `videoThumbnailImpressions` y
  `videoThumbnailImpressionsClickRate` figuran en la documentación desde enero
  de 2026 pero devuelven 400. El descargador las sigue pidiendo por si algún día
  andan; si vuelven, esta rutina manual deja de hacer falta.
- **Apuntar a la cuenta de marca solo con `YT_CANAL`.** El catálogo sí sale
  (es público), Analytics devuelve 403: el token tiene que ser del dueño.
- **La extensión del navegador para automatizar todo.** Necesita la máquina
  prendida y la sesión viva. Por eso el grueso va por API y Actions.
