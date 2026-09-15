# Joy Of Gaming · Panel de performance

Dashboard HTML de una sola página con la performance del canal (corte 2026-09-13).

Abrí `index.html` en el navegador. No necesita servidor.

## Actualizar con data nueva

1. Copiá los CSV nuevos a `data/`: `catalogo_videos.csv`, `metricas_video.csv`, `metricas_canal.csv`.
2. Corré:
   ```
   pip install pandas
   python scripts/build.py     # calcula data/data.json
   python scripts/render.py    # genera index.html
   ```

Los CSV no se suben al repo (ver `.gitignore`). Solo se guarda `data/data.json` agregado.

## Reglas de cálculo

- Solo videos largos (`es_largo = True`) con 14 días o más publicados.
- CTR = suma(clicks) ÷ suma(impresiones). Nunca promedio de CTRs.
- % reproducido y AVD ponderados por vistas. RPM = ingresos ÷ (vistas/1000).
- Semanas ISO lunes–domingo. Semanas y meses parciales excluidos.
- Grupos con menos de 8 videos: muestra insuficiente. OTROS no se rankea.
