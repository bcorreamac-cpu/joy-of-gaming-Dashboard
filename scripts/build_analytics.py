"""Genera data/analytics.json, la base del dashboard interactivo.

Emite dos tablas planas y deja TODO el resto (agregados por mes, quarter,
anio, categoria, modo A/B) para calcularse en el navegador. Asi los filtros
son instantaneos y no hay que regenerar nada al cambiar de periodo.

Requiere los tres CSV en data/. Si falta alguno, aborta sin pisar el archivo
existente.
"""
import json, os, sys
from datetime import date

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data'))

ANIOS = ('2024', '2025', '2026')   # periodo cubierto por el dashboard
FALTAN = [f for f in ('metricas_canal.csv', 'catalogo_videos.csv', 'metricas_video.csv')
          if not os.path.exists(f)]
if FALTAN:
    sys.exit('Faltan los CSV: ' + ', '.join(FALTAN) + '\n'
             'Descargalos de YouTube Studio y dejalos en data/. '
             'analytics.json no se modifico.')

import pandas as pd

m = pd.read_csv('metricas_canal.csv')
c = pd.read_csv('catalogo_videos.csv')
v = pd.read_csv('metricas_video.csv')

m = m[m.mes.str[:4].isin(ANIOS)].copy()

# ---- serie diaria del canal (modo B: todo lo que ocurrio en el periodo) ----
m['clicks'] = m.get('clicks', m.impresiones * m.get('ctr', 0) / 100)
dias = [{
    'f':  r.fecha,
    'v':  None if pd.isna(r.vistas) else int(r.vistas),
    'i':  None if pd.isna(r.impresiones) else int(r.impresiones),
    'c':  None if pd.isna(r.clicks) else float(r.clicks),
    'sg': None if pd.isna(r.subs_ganados) else int(r.subs_ganados),
    'sp': None if pd.isna(r.subs_perdidos) else int(r.subs_perdidos),
    'ing': None if pd.isna(r.ingresos_usd) else float(r.ingresos_usd),
    'th': None if pd.isna(getattr(r, 'tiempo_repr_horas', float('nan'))) else float(r.tiempo_repr_horas),
} for r in m.itertuples()]

# ---- tabla de videos (modo A: que publicamos y como rindio) ----
d = c.merge(v, on='video_id', how='inner')
extra = [col for col in ('franquicia', 'juego', 'tipo_contenido', 'serie', 'saga')
         if col in d.columns]
videos = []
for r in d.itertuples():
    row = {
        'id':  r.video_id,
        't':   r.titulo,
        'cat': r.categoria,
        'pub': str(r.fecha_publicacion)[:10],
        'v':   None if pd.isna(r.vistas) else int(r.vistas),
        'i':   None if pd.isna(r.impresiones) else int(r.impresiones),
        'c':   None if pd.isna(r.clicks) else float(r.clicks),
        'pct': None if pd.isna(r.pct_reproducido) else float(r.pct_reproducido),
        'avd': None if pd.isna(r.avd_seg) else float(r.avd_seg),
        'sg':  None if pd.isna(r.subs_ganados) else int(r.subs_ganados),
        'lg':  bool(r.es_largo),
        'edad': None if pd.isna(r.dias_publicado) else int(r.dias_publicado),
    }
    for col in extra:
        row[col] = getattr(r, col)
    videos.append(row)

out = {
    'meta': {
        'corte': m.fecha.max(),
        'generado': date.today().isoformat(),
        'anios': list(ANIOS),
        'granularidad': 'dia',
        'meses_parciales': sorted(m[m.mes_parcial].mes.unique().tolist()),
        'semanas_parciales': sorted(m[m.semana_parcial].semana.unique().tolist()),
        # metricas_video.csv trae acumulados sin fecha: el modo A no puede
        # aislar "vistas ocurridas en el periodo" por video.
        'video_serie_temporal': False,
        'dims_extra': extra,
        'n_videos': len(videos),
        'min_dias_video': 14,
    },
    'dias': dias,
    'videos': videos,
}
json.dump(out, open('analytics.json', 'w'), default=float)
print(f"analytics.json: {len(dias)} dias ({dias[0]['f']} -> {dias[-1]['f']}), "
      f"{len(videos)} videos, dims extra: {extra or 'ninguna'}")
