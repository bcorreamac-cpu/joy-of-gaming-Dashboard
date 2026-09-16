"""Lee los exports crudos de YouTube Studio y genera data/analytics.json.

Entrada: data/entrada/
  canal_*.csv   desglose "Fecha", una fila por día. Varios archivos si hubo
                que partir el rango por el tope de 500 filas del export.
  videos_*.csv  desglose "Contenido", una fila por video.

Salida: dos tablas planas (días y videos). Todo lo demás —agregados por mes,
quarter o año, los dos universos del switch, las categorías— se calcula en el
navegador, así los filtros son instantáneos.

Solo biblioteca estándar: no hace falta instalar nada.
"""
import csv, json, os, re, sys, unicodedata
from datetime import date, datetime, timedelta
from calendar import monthrange
from statistics import median

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MIN_DIAS_VIDEO = 14  # antes de eso el video todavía no juntó sus vistas
VENTANA_IX = 20      # videos vecinos que forman la base del índice relativo
MIN_IX = 8           # con menos vecinos la mediana es un número al azar
ENTRADA = os.path.join(RAIZ, 'data', 'entrada')
ANIOS = ('2024', '2025', '2026')          # periodo que cubre el dashboard
DESDE = ANIOS[0] + '-01-01'               # nada anterior entra, ni dias ni videos
SHORT_CORTO, SHORT_LARGO = 60, 180        # umbrales de Shorts, en segundos
SHORT_CAMBIO = '2024-10-15'               # YouTube subió el tope a 3 min

# ── utilidades ────────────────────────────────────────────────────────────
def norm(s):
    """Minúsculas sin tildes: los encabezados vienen con acentos inconsistentes."""
    s = unicodedata.normalize('NFKD', s or '')
    return ''.join(c for c in s if not unicodedata.combining(c)).strip().lower()

def leer(ruta):
    """Filas del CSV como dicts, descartando 'Total' y el pie del export."""
    with open(ruta, encoding='utf-8-sig') as fh:
        filas = list(csv.reader(fh))
    cab = [norm(c) for c in filas[0]]
    out = []
    for f in filas[1:]:
        if not f or not f[0].strip() or f[0] == 'Total' or f[0].startswith('Mostrando'):
            continue
        out.append(dict(zip(cab, f)))
    return out

def col(fila, *claves):
    """Primera columna cuyo encabezado contenga alguna de las claves."""
    for k in claves:
        for c, v in fila.items():
            if k in c:
                return v
    return ''

def num(v):
    v = (v or '').strip().replace(',', '')
    if not v or v in ('-', '—'):
        return None
    try:
        return float(v)
    except ValueError:
        return None

MESES_EN = {m: i for i, m in enumerate(
    ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'], 1)}

def fecha_pub(v):
    """'Jun 14, 2026' o '2026-06-14' -> date."""
    v = (v or '').strip().strip('"')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
        return date.fromisoformat(v)
    m = re.match(r'([A-Za-z]{3})\w*\.?\s+(\d{1,2}),?\s+(\d{4})', v)
    if m and m.group(1).lower() in MESES_EN:
        return date(int(m.group(3)), MESES_EN[m.group(1).lower()], int(m.group(2)))
    return None

def a_segundos(v):
    """'0:01:49' -> 109. Un número suelto ya viene en segundos."""
    v = (v or '').strip()
    if not v:
        return None
    if ':' in v:
        p = [int(x) for x in v.split(':')]
        while len(p) < 3:
            p.insert(0, 0)
        return p[0] * 3600 + p[1] * 60 + p[2]
    return int(float(v)) if v.replace('.', '').isdigit() else None

# ── comprobaciones de entrada ─────────────────────────────────────────────
def listar(patron):
    if not os.path.isdir(ENTRADA):
        sys.exit(f'No existe {ENTRADA}. Dejá ahí los CSV de YouTube Studio.')
    return sorted(os.path.join(ENTRADA, f) for f in os.listdir(ENTRADA)
                  if f.startswith(patron) and f.endswith('.csv'))

def main():
    """Lee data/entrada/, escribe data/analytics.json y resume por consola.

    Va dentro de una función a propósito: validar.py importa este módulo para
    reusar el lector de CSV, y con el cuerpo suelto el import regeneraba el
    analytics.json que justamente venía a revisar.
    """
    f_canal, f_videos = listar('canal_'), listar('videos_')
    if not f_canal or not f_videos:
        sys.exit('Faltan CSV en data/entrada/: se esperan canal_*.csv y videos_*.csv.\n'
                 'analytics.json no se modificó.')

    # ── categorías: se deducen del título ─────────────────────────────────────
    cfg = json.load(open(os.path.join(RAIZ, 'data', 'categorias.json'), encoding='utf-8'))
    # Juegos que se repiten: sirven para saber qué conviene volver a grabar.
    try:
        jcfg = json.load(open(os.path.join(RAIZ, 'data', 'juegos.json'), encoding='utf-8'))
        JUEGOS = [(n, re.compile(pt, re.I)) for n, pt in jcfg['reglas']]
    except (OSError, ValueError, KeyError):
        JUEGOS = []
    dejuego = lambda t: next((n for n, pt in JUEGOS if pt.search(t or '')), None)
    REGLAS = [(c, re.compile(p, re.I)) for c, p in cfg['reglas']]
    clasificar = lambda t: next((c for c, p in REGLAS if p.search(t or '')), 'OTROS')

    # ── serie diaria del canal ────────────────────────────────────────────────
    dias, vistos = {}, set()
    for ruta in f_canal:
        for f in leer(ruta):
            d = col(f, 'fecha')
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', d.strip()):
                continue
            d = d.strip()
            if d[:4] not in ANIOS or d in vistos:
                continue            # los rangos exportados pueden solaparse
            vistos.add(d)
            imp, ctr = num(col(f, 'impresiones')), num(col(f, 'tasa de clics', 'ctr'))
            dias[d] = {
                'f': d,
                'v': num(col(f, 'vistas')),
                'i': imp,
                'c': None if imp is None or ctr is None else imp * ctr / 100,
                'sg': num(col(f, 'suscriptores obtenidos', 'suscriptores ganados')),
                'sp': num(col(f, 'suscriptores perdidos')),
                'ing': num(col(f, 'ingresos')),
                'th': num(col(f, 'tiempo de reproduccion')),
            }
    if not dias:
        sys.exit('Los canal_*.csv no trajeron ningún día dentro de ' + '/'.join(ANIOS))
    serie = [dias[k] for k in sorted(dias)]

    # YouTube tarda unos dias en cerrar los ingresos: los ultimos dias del export
    # llegan con la celda vacia. Se guardan como null, no como cero, y se avisan.
    sin_ingresos = sorted(d['f'] for d in serie if d['ing'] is None)

    # huecos: el export se parte en tramos y es fácil perder un día en el empalme
    d0, d1 = date.fromisoformat(serie[0]['f']), date.fromisoformat(serie[-1]['f'])
    esperados = {(d0 + timedelta(n)).isoformat() for n in range((d1 - d0).days + 1)}
    huecos = sorted(esperados - set(dias))

    # meses y semanas incompletos
    por_mes, por_sem = {}, {}
    for d in dias:
        y, m, dd = map(int, d.split('-'))
        por_mes.setdefault(f'{y}-{m:02d}', set()).add(dd)
        iso = date(y, m, dd).isocalendar()
        por_sem.setdefault(f'{iso[0]}-W{iso[1]:02d}', set()).add(d)
    meses_parciales = sorted(k for k, ds in por_mes.items()
                             if len(ds) < monthrange(int(k[:4]), int(k[5:]))[1])
    semanas_parciales = sorted(k for k, ds in por_sem.items() if len(ds) < 7)

    # ── tabla de videos ───────────────────────────────────────────────────────
    corte = serie[-1]['f']
    corte_d = date.fromisoformat(corte)
    videos, ids = [], set()
    for ruta in f_videos:
        for f in leer(ruta):
            vid = col(f, 'contenido', 'video id').strip()
            if not vid or vid in ids:
                continue            # los tramos por año no se pisan, pero por las dudas
            ids.add(vid)
            pub = fecha_pub(col(f, 'tiempo de publicacion', 'fecha de publicacion'))
            if pub is None or pub.isoformat() < DESDE:
                continue            # fuera de la ventana del dashboard
            # 'duracion', nunca 'duracion promedio de vistas'
            dur = a_segundos(next((v for k, v in f.items()
                                   if k.startswith('duracion') and 'promedio' not in k), ''))
            imp, ctr = num(col(f, 'impresiones')), num(col(f, 'tasa de clics', 'ctr'))
            tope = SHORT_LARGO if pub.isoformat() >= SHORT_CAMBIO else SHORT_CORTO
            videos.append({
                'id': vid,
                't': col(f, 'titulo del video', 'titulo'),
                'cat': clasificar(col(f, 'titulo del video', 'titulo')),
                'pub': pub.isoformat(),
                'v': num(col(f, 'vistas')),
                'i': imp,
                'c': None if imp is None or ctr is None else imp * ctr / 100,
                'pct': num(col(f, 'porcentaje promedio reproducido')),
                'avd': a_segundos(next((v for k, v in f.items() if 'promedio' in k and
                                        ('duracion' in k or 'vistas' in k)), '')),
                'sg': num(col(f, 'suscriptores obtenidos', 'suscriptores ganados')),
                'lg': dur is None or dur > tope,
                'dur': dur,
                'edad': (corte_d - pub).days,
                'j': dejuego(col(f, 'titulo del video', 'titulo')),
            })
    if not videos:
        sys.exit(f'Los videos_*.csv no trajeron ningún video publicado desde {DESDE}.')
    videos.sort(key=lambda v: v['pub'])

    # Índice relativo: vistas del video ÷ mediana de sus vecinos en el tiempo.
    # El canal viene cayendo, así que comparar vistas crudas entre 2024 y 2026
    # miente: un video mediocre de 2024 le gana a uno bueno de 2026. Con este
    # número, 1,0 es "lo normal para su época", en cualquier época.
    # La base son vecinos y no el mes calendario, que partiría en dos a videos
    # publicados con días de diferencia.
    medibles = [v for v in videos if v['lg'] and v['edad'] >= MIN_DIAS_VIDEO]
    for i, v in enumerate(medibles):
        ini = max(0, i - VENTANA_IX // 2)
        vecinos = [w['v'] for w in medibles[ini:ini + VENTANA_IX + 1]
                   if w is not v and w['v'] is not None]
        base = median(vecinos) if len(vecinos) >= MIN_IX else None
        v['ix'] = round(v['v'] / base, 3) if base and v['v'] is not None else None

    # ── salida ────────────────────────────────────────────────────────────────
    salida = {
        'meta': {
            'corte': corte,
            'generado': date.today().isoformat(),
            'anios': list(ANIOS),
            'granularidad': 'dia',
            'meses_parciales': meses_parciales,
            'semanas_parciales': semanas_parciales,
            'dias_faltantes': huecos,
            'dias_sin_ingresos': sin_ingresos,
            # metricas_video.csv trae acumulados sin fecha: no se puede aislar
            # "vistas ocurridas en el periodo" video por video.
            'video_serie_temporal': False,
            'ventana_videos': [serie[0]['f'][:4], corte[:4]],
            'cat_inferida': True,          # la categoria sale del titulo, no del export
            'cat_etiquetas': cfg['_etiquetas'],
            'n_videos': len(videos),
            'n_largos': sum(1 for v in videos if v['lg']),
            'min_dias_video': MIN_DIAS_VIDEO,
            'ventana_ix': VENTANA_IX,
            'dims_extra': [],
        },
        'dias': serie,
        'videos': videos,
    }
    json.dump(salida, open(os.path.join(RAIZ, 'data', 'analytics.json'), 'w'),
              ensure_ascii=False)

    print("analytics.json")
    print(f"  días   : {len(serie)} ({serie[0]['f']} → {corte})"
          + (f"  ¡{len(huecos)} faltantes!" if huecos else "  sin huecos"))
    print(f"  videos : {len(videos)} ({salida['meta']['n_largos']} largos, "
          f"{len(videos) - salida['meta']['n_largos']} shorts)")
    print(f"  meses incompletos  : {meses_parciales or 'ninguno'}")
    if sin_ingresos:
        print(f"  sin ingresos aun   : {len(sin_ingresos)} días ({sin_ingresos[0]} → {sin_ingresos[-1]})")
    sin = sum(1 for v in videos if v['cat'] == 'OTROS')
    print(f"  sin clasificar     : {sin} videos ({sin / len(videos) * 100:.1f} %)")



if __name__ == '__main__':
    main()
