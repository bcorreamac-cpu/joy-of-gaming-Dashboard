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

## Actualizar con data nueva

1. Copiá los CSV a `data/`: `catalogo_videos.csv`, `metricas_video.csv`,
   `metricas_canal.csv`. No se versionan (ver `.gitignore`).
2. Corré:
   ```
   pip install pandas
   python scripts/build.py             # data/data.json      -> reporte fijo
   python scripts/build_analytics.py   # data/analytics.json -> dashboard
   python scripts/render.py            # index.html
   python scripts/render_dashboard.py  # dashboard.html
   ```

Sin los CSV, `build_analytics.py` aborta sin pisar nada. El
`data/analytics.json` que hay en el repo lo generó
`scripts/build_analytics_interino.py`, que reconstruye lo que puede desde
`data.json` y el historial de git: 32 meses de canal reales, pero sólo 30 de
los 401 videos. El dashboard lo avisa en pantalla mientras esté así.

## Lo que todavía no se puede calcular

Para separar **vistas de videos nuevos** de **vistas del catálogo** dentro de
un mismo período hace falta un export con **una fila por video y por día**.
`metricas_video.csv` trae un total acumulado por video, sin fecha.

Consecuencias mientras no esté:

- El modo A mide el acumulado de cada video, no lo que generó dentro del
  período. Un video viejo lleva meses sumando y uno nuevo apenas días, así que
  los períodos recientes se ven peores de lo que son.
- Las categorías no siguen el filtro temporal en modo B.

## Reglas de cálculo

- Solo videos largos (`es_largo = True`) con 14 días o más publicados.
- CTR = suma(clicks) ÷ suma(impresiones). Nunca el promedio de CTRs.
- % reproducido y AVD ponderados por vistas. RPM = ingresos ÷ (vistas/1000).
- Semanas ISO lunes–domingo. Los períodos incompletos se marcan, no se ocultan.
- Las variaciones de CTR van en puntos porcentuales (pp).
- Categorías con menos de 8 videos: muestra insuficiente, no se rankean.
