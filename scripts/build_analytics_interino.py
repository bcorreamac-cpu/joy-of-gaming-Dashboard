"""Arma un analytics.json PARCIAL con lo unico que hay versionado.

Los CSV no estan en el repo (.gitignore), asi que este script reconstruye lo
que se pueda desde data/data.json y desde la version original que quedo en el
historial de git (commit 493212f, el unico corte que todavia incluia 2024).

Es un puente para poder usar el dashboard hoy. Cuando los CSV esten en data/,
corre build_analytics.py y este archivo deja de usarse.
"""
import json, subprocess, os
from datetime import date

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.chdir(root)

hoy = json.load(open('data/data.json'))
orig = json.loads(subprocess.run(
    ['git', 'show', '493212f:data/data.json'],
    capture_output=True, text=True, check=True).stdout)

# --- serie del canal: mensual, desde 2024-01 (el original, antes del recorte)
subs_conocidos = {  # unicos meses con el desglose ganados/perdidos publicado
    '2026-08': (orig['resumen']['actual']['subs_ganados'], orig['resumen']['actual']['subs_perdidos']),
    '2026-07': (orig['resumen']['prev']['subs_ganados'],   orig['resumen']['prev']['subs_perdidos']),
    '2025-08': (orig['resumen']['yoy']['subs_ganados'],    orig['resumen']['yoy']['subs_perdidos']),
}
periodos = []
for r in orig['mensual']:
    sg, sp = subs_conocidos.get(r['mes'], (None, None))
    periodos.append({
        'p': r['mes'],
        'v': r['vistas'], 'i': r['imp'],
        'c': r['imp'] * r['ctr'] / 100,      # clicks reconstruidos desde el CTR ponderado
        'sn': r['subs'],                      # neto (lo unico disponible mes a mes)
        'sg': sg and int(sg), 'sp': sp and int(sp),
        'ing': r['ing'],
    })

# --- videos: solo los 30 que quedaron expuestos en top/bottom
vistos, videos = set(), []
for r in hoy['top'] + hoy['bottom']:
    if r['video_id'] in vistos:
        continue
    vistos.add(r['video_id'])
    videos.append({
        'id': r['video_id'], 't': r['titulo'], 'cat': r['categoria'],
        'pub': r['fecha_publicacion'], 'v': int(r['vistas']), 'i': int(r['impresiones']),
        'c': r['impresiones'] * r['ctr'] / 100, 'pct': r['pct_reproducido'],
        'avd': None, 'sg': int(r['subs_ganados']), 'lg': True, 'edad': None,
    })

out = {
    'meta': {
        'corte': hoy['corte'],
        'generado': date.today().isoformat(),
        'anios': ['2024', '2025', '2026'],
        'granularidad': 'mes',          # sin CSV no hay detalle diario
        'meses_parciales': ['2026-09'],
        'semanas_parciales': [],
        'video_serie_temporal': False,
        'dims_extra': [],
        'n_videos': len(videos),
        'n_videos_canal': orig['n_total'],
        'min_dias_video': 14,
        'parcial': True,                # el dashboard avisa cuando esto es true
        'ventana_videos': ['2023', '2026'],
    },
    'periodos': periodos,
    'videos': videos,
    'cats': hoy['categorias'],
}
json.dump(out, open('data/analytics.json', 'w'), default=float)
print(f"analytics.json PARCIAL: {len(periodos)} meses "
      f"({periodos[0]['p']} -> {periodos[-1]['p']}), {len(videos)} de "
      f"{orig['n_total']} videos, granularidad mes")
