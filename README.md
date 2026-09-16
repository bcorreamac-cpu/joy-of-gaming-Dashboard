# Joy Of Gaming · Panel de performance

Dos páginas estáticas, sin servidor ni build. Se abren con doble clic.

| Archivo | Qué es |
|---|---|
| `dashboard.html` | **Dashboard interactivo.** Filtros por año, quarter y mes, comparación de períodos, modos A/B, performance por categoría, exportación a CSV. |
| `index.html` | Reporte fijo del último mes cerrado. Una foto, sin controles. |

## Los dos modos de análisis

El dashboard nunca mezcla estas dos preguntas en un mismo indicador. El panel
cambia de color según el modo activo (violeta / azul) y el modo va siempre en
la barra superior.

**Modo A · contenido publicado.** Sólo los videos con fecha de publicación
dentro del período. Responde *¿qué tan bien funcionó lo que publicamos?*

**Modo B · performance del canal.** Todo lo que ocurrió en el período, sin
importar cuándo se publicó el video. Responde *¿cuánto generó el canal?*

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
