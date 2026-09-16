# Joy Of Gaming · Panel de performance

Dos páginas estáticas, sin servidor ni build. Se abren con doble clic.

| Archivo | Qué es |
|---|---|
| `dashboard.html` | **Dashboard interactivo.** Filtros por año, quarter y mes, comparación de períodos, modos A/B, performance por categoría, exportación a CSV. |
| `index.html` | Reporte fijo del último mes cerrado. Una foto, sin controles. |

## El switch: dos universos de análisis

El dashboard nunca mezcla estas dos preguntas en un mismo indicador. El panel
cambia de color (violeta / azul), el título de cada KPI dice de qué universo
sale el número y el estado del switch va en la barra superior.

Con **enero 2025** seleccionado:

| | Switch OFF | Switch ON |
|---|---|---|
| Filtra por | Fecha de **publicación** | Fecha en que se **generó la métrica** |
| Incluye | Solo videos publicados en enero 2025 | Todos los videos, sin importar cuándo salieron |
| Mide | Su acumulado **completo**, hasta el corte | Solo lo ocurrido **dentro** de enero 2025 |
| Título del KPI | "Vistas acumuladas — Videos publicados en enero 2025" | "Vistas generadas — Todo el canal durante enero 2025" |
| Responde | ¿Cuánto terminó generando lo que publicamos? | ¿Cuánto generó el canal? |

Un video publicado en enero 2025 con 300.000 vistas aporta las 300.000 en OFF,
aunque la mayoría las haya juntado en marzo. En ON aporta solo las vistas que
hizo durante enero.

El switch gobierna vistas, CTR, suscriptores y performance por categoría.

**Antigüedad media del lote.** Como OFF suma acumulados, un lote viejo tuvo más
tiempo para juntar vistas que uno reciente. No es un error de cálculo: es la
definición. Pero para que dos períodos sean comparables, la antigüedad media
del lote aparece como KPI y como columna de la tabla, y el panel avisa cuando
los lotes en pantalla difieren demasiado.

**Comparaciones contra huecos.** Si el período de referencia cae fuera de los
datos disponibles, la variación no se muestra: se dice cuántos períodos faltan.
Un −93 % contra un hueco es peor que no mostrar nada.

## Actualización automática

Todos los lunes a las 11:00 UTC, GitHub Actions baja los datos de YouTube,
reconstruye el panel y lo publica. No hace falta tener la computadora
prendida: corre en los servidores de GitHub.

```
.github/workflows/actualizar.yml   el cron y los pasos
scripts/yt_autorizar.py            permiso de YouTube (se corre UNA vez)
scripts/yt_descargar.py            baja los datos y escribe data/entrada/
scripts/guardia.py                 frena una publicación que empeore los datos
```

`yt_descargar.py` escribe CSV con **los mismos encabezados** que los exports de
YouTube Studio, así que el resto del proceso no distingue si los datos llegaron
a mano o por API. Usa dos APIs, porque ninguna trae todo: Analytics para las
métricas, Data para los títulos, fechas y duraciones.

### Puesta en marcha (una vez, ~15 minutos)

1. **Proyecto en Google Cloud.** En <https://console.cloud.google.com> creá un
   proyecto y activá dos APIs: *YouTube Analytics API* y *YouTube Data API v3*.
2. **Permisos.** Desde 2025 esto vive en *APIs y servicios → Google Auth
   Platform*, con cuatro pestañas: *Branding*, *Audience*, *Data Access* y
   *Clients*. En **Audience** elegí *Externo*; en **Data Access** usá
   *Add or remove scopes* y, abajo, **Manually add scopes**, para pegar los tres:
   `yt-analytics.readonly`, `yt-analytics-monetary.readonly`, `youtube.readonly`.
3. **Publicala.** En *Audience*, pasá de *Prueba* a **En producción**. En modo
   Prueba, Google caduca el permiso **a los 7 días** y la automatización se corta
   sola. Va a aparecer un aviso de "app no verificada"; para uso propio se sigue
   igual (el límite es 100 usuarios).

   `youtube.readonly` es un permiso **sensible**. Publicar sin verificar suele
   alcanzar para uso personal, pero la documentación de Google no es del todo
   clara sobre si el token dura para siempre en ese caso. Por eso corre el
   *latido* de abajo: si el permiso muere, te enterás al día siguiente.
4. **Credenciales → ID de cliente de OAuth**, tipo *Aplicación de escritorio*.
   Anotá el *client ID* y el *client secret*.
5. **Sacá el permiso**, en tu máquina:
   ```
   python3 scripts/yt_autorizar.py
   ```
   Abre el navegador, elegís la cuenta del canal y aceptás. Imprime los tres
   valores que necesitás.
6. **Guardalos como secrets** en *Settings → Secrets and variables → Actions*:
   `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
   El repo es público: nunca los pongas en un archivo.
7. **Comprobá que el canal devuelve todo**, antes de tocar GitHub:
   ```
   YT_CLIENT_ID=... YT_CLIENT_SECRET=... YT_REFRESH_TOKEN=... \
     python3 scripts/yt_descargar.py --comprobar
   ```
   Hace tres pedidos chicos y dice cuáles pasan. Tarda segundos.
8. **Probalo entero** en *Actions → Actualizar el panel → Run workflow*.
   No esperes al lunes para saber si funciona.

### Impresiones y CTR

Google expuso estas dos métricas en el API el **15 de enero de 2026**
(`videoThumbnailImpressions` y `videoThumbnailImpressionsClickRate`); antes eran
exclusivas de Studio. El descargador no da eso por sentado: las pide, y si el
API las rechaza avisa y sigue sin ellas. El panel funciona igual, con las
columnas de CTR vacías. El chequeo del paso 7 te lo confirma en segundos.

### El latido

`.github/workflows/latido.yml` corre todos los días, no toca el repo y solo pide
un token nuevo. Si el permiso de Google caducó, falla y GitHub te manda un mail.
Sin esto te enterarías el lunes siguiente, con el panel ya desactualizado.

Podés correr el mismo chequeo a mano:

```
python3 scripts/yt_descargar.py --comprobar
```

Sale con código 1 si falta algo imprescindible. Que fallen las impresiones y el
CTR no cuenta: el panel funciona sin ellas.

### Dos puertas antes de publicar

El workflow no publica nada que no pase estos dos chequeos:

- **`validar.py`** — 55 chequeos: que los datos sean coherentes consigo mismos.
- **`guardia.py`** — que no empeoren a los publicados: que el corte no
  retroceda, que no se pierdan días ni videos, que las vistas no caigan más de
  2 % (YouTube reajusta cifras hacia atrás, por eso la tolerancia).

Si alguno falla, el job se cae y **el panel queda como estaba**. GitHub te manda
un mail cuando una corrida programada falla.

### Si algo se rompe

| Síntoma | Causa casi segura |
|---|---|
| `invalid_grant` al renovar el token | El permiso caducó: la app volvió a *Prueba*, revocaste el acceso, o Google expiró el token de una app sin verificar. Repetí los pasos 3 y 5. |
| El workflow dejó de correr solo | GitHub apaga los cron de repos públicos tras 60 días sin actividad. Como esto commitea cada semana, no debería pasar; si pasa, se reactiva desde *Actions*. |
| Los ingresos del último día vienen vacíos | Normal: YouTube tarda en liquidar. El panel lo avisa. |
| La página no se actualiza pero el commit está | Revisá *Settings → Pages*: tiene que servir desde la rama `main`. |

## Actualizar a mano con data nueva

Los exports de YouTube Studio se cortan en **500 filas**, así que hay que
partirlos y juntarlos después. El script acepta varios archivos por tipo.

1. Descargá de YouTube Studio → Analytics → Modo avanzado:
   - Pestaña **Fecha**, agrupado por día. Partí el rango en tramos de 500 días.
   - Pestaña **Contenido**. Partí por año de publicación del video.
2. De cada ZIP sacá `Datos de la tabla.csv` y dejalo en `data/entrada/` como
   `canal_*.csv` o `videos_*.csv`. El nombre después del prefijo da igual.
3. Corré:
   ```
   python scripts/build_analytics.py   # data/analytics.json
   python scripts/render_dashboard.py  # dashboard.html
   ```

Sin dependencias: solo biblioteca estándar. Si falta algún CSV, el script
aborta sin pisar el `analytics.json` existente.

**Un archivo cortado se reconoce** porque tiene exactamente 501 filas de datos
y mezcla varios años de publicación. Los buenos traen un solo año.

## Categorías

Los exports **no traen categoría**. Se deduce del título con reglas por nombre
de juego, en `data/categorias.json` — editable, se evalúan en orden y gana la
primera que coincide. Validado contra 30 videos etiquetados a mano: 29
coincidieron. El dashboard muestra cuántos quedan sin clasificar.

## Diseño de los gráficos

La paleta categórica está **validada**, no elegida a ojo: banda de luminosidad,
piso de croma, separación bajo daltonismo, piso de visión normal y contraste
contra la superficie real de los paneles (`#0e121b`). Ocho slots en orden fijo,
asignados por categoría y nunca por ranking — ordenar una columna de la tabla no
repinta nada. "Sin clasificar" lleva un gris neutro: es un bucket, no una
categoría más, y no gasta un slot.

Reglas de marca: barra de 24 px como máximo, con el extremo de dato redondeado y
la base cuadrada, separadas por 2 px del color del fondo; línea de 2 px con
marcadores de 8 px y anillo de 2 px; relleno de área al 10 %; grilla hairline
sólida. Los ejes caen siempre en números redondos. Una sola serie no lleva
leyenda, dos o más sí. El texto nunca se pinta del color de la serie: la
identidad la lleva la marca al lado.

En el gráfico de volumen vs. eficiencia el color **no** codifica nada: con nueve
categorías y todos los pares en juego ningún orden de colores se distingue bien,
así que identifica la etiqueta sobre cada burbuja. Una etiqueta que no entra sin
pisar a otra no se dibuja — el dato sigue en el tooltip y en la tabla.

## Validación

```
python3 scripts/validar.py
```

55 chequeos sobre `data/analytics.json`: continuidad de la serie diaria,
duplicados, rangos, nulos, clasificación short/largo, cuadratura contra las
filas "Total" de los propios exports y coherencia de las agregaciones por mes,
quarter y año. Sale con código 1 si algo no cuadra.

## Límites conocidos

- **Los últimos días llegan sin ingresos.** YouTube tarda en liquidar: el
  export trae la celda vacía. Se guardan como `null` (no como cero) y quedan
  listados en `meta.dias_sin_ingresos`; el panel avisa cuando el período
  seleccionado incluye alguno, porque los ingresos y el RPM de ese mes salen
  por debajo del valor final.
- **% reproducido por encima de 100 %.** Pasa en Shorts: el bucle hace que se
  vean más de una vez. No entran al panel de todos modos.

- **La ventana arranca en enero 2024.** `DESDE` en `scripts/build_analytics.py`
  descarta todo lo anterior, días y videos. Así el acumulado por video es
  completo: cada uno entra con toda su historia, no con un pedazo.
- **Los dos modos no miden el mismo universo, y está bien.** En OFF entran los
  296 videos publicados desde 2024 con sus vistas acumuladas. En ON entran
  todas las vistas del canal en esas fechas, incluidas las que sigue trayendo
  el catálogo anterior a 2024 — que es la mayor parte. Comparar un total de OFF
  contra uno de ON no tiene sentido.
- **Categorías en modo ON.** Repartir por categoría las vistas de un período
  necesita un export con una fila por video y por día. Sin eso, la sección de
  categorías con el switch en ON muestra el catálogo acumulado.
- **YouTube no cuadra consigo mismo.** En los exports por video tal como los
  entrega YouTube, la suma de las filas difiere de la fila "Total" del propio
  archivo en 39 suscriptores sobre 47.124 (0,08 %). Se respetan las filas.

## Reglas de cálculo

- Solo videos largos (`es_largo = True`) con 14 días o más publicados.
- CTR = suma(clicks) ÷ suma(impresiones). Nunca el promedio de CTRs.
- % reproducido y AVD ponderados por vistas. RPM = ingresos ÷ (vistas/1000).
- Semanas ISO lunes–domingo. Los períodos incompletos se marcan, no se ocultan.
- Las variaciones de CTR van en puntos porcentuales (pp).
- Categorías con menos de 8 videos: muestra insuficiente, no se rankean.
