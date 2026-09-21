"""Chequeos de integridad sobre data/analytics.json y los CSV de origen.

    python3 scripts/validar.py

Devuelve 0 si todo cuadra. Necesita los CSV crudos en data/entrada/ para los
chequeos contra las filas "Total" de los propios exports.
"""
import csv, json, sys, os, re
from datetime import date, timedelta
from collections import Counter, defaultdict
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, 'scripts')
import build_analytics as B   # reutiliza norm/leer/col/num

D = json.load(open('data/analytics.json'))
dias, vids, meta = D['dias'], D['videos'], D['meta']
fallos, avisos = [], []
def chk(ok, msg): (avisos if ok else fallos).append(msg)

# ── 1. estructura de la serie diaria ──────────────────────────────────
fs = [d['f'] for d in dias]
chk(len(fs) == len(set(fs)), f"días duplicados: {len(fs)-len(set(fs))}")
chk(fs == sorted(fs), "días ordenados")
d0, d1 = date.fromisoformat(fs[0]), date.fromisoformat(fs[-1])
esp = [(d0+timedelta(n)).isoformat() for n in range((d1-d0).days+1)]
chk(esp == fs, f"serie diaria continua {fs[0]}→{fs[-1]} ({len(fs)} días)")
chk(all(f >= '2024-01-01' for f in fs), "ningún día antes de 2024")
chk(meta['dias_faltantes'] == [], f"huecos declarados: {meta['dias_faltantes']}")

# ── 2. estructura de videos ───────────────────────────────────────────
ids = [v['id'] for v in vids]
chk(len(ids) == len(set(ids)), f"ids duplicados: {len(ids)-len(set(ids))}")
chk([v['pub'] for v in vids] == sorted(v['pub'] for v in vids), "videos ordenados por publicación")
chk(all(v['pub'] >= '2024-01-01' for v in vids), "ningún video publicado antes de 2024")
chk(all(v['pub'] <= meta['corte'] for v in vids), "ningún video publicado después del corte")
chk(meta['n_videos'] == len(vids), "meta.n_videos coincide")
chk(meta['n_largos'] == sum(1 for v in vids if v['lg']), "meta.n_largos coincide")

# edad = corte - pub
mal_edad = [v['id'] for v in vids
            if v['edad'] != (date.fromisoformat(meta['corte'])-date.fromisoformat(v['pub'])).days]
chk(not mal_edad, f"edad mal calculada en {len(mal_edad)} videos")

# shorts: umbral 60s hasta 2024-10-15, 180s después
mal_lg = [v['id'] for v in vids if v['dur'] is not None
          and v['lg'] != (v['dur'] > (180 if v['pub'] >= '2024-10-15' else 60))]
chk(not mal_lg, f"clasificación short/largo inconsistente en {len(mal_lg)}")
chk(all(v['dur'] is not None for v in vids), "todos los videos traen duración")

# ── 3. valores fuera de rango ─────────────────────────────────────────
def rango(rows, campo, lo=0, hi=None, etq=''):
    if etq.startswith('videos largos'): rows = [r for r in rows if r.get('lg')]
    malos = [r for r in rows if r.get(campo) is not None
             and (r[campo] < lo or (hi is not None and r[campo] > hi))]
    chk(not malos, f"{etq}{campo}: {len(malos)} fuera de [{lo},{hi}]")
for c in ('v','i','sg','sp','ing','th'): rango(dias, c, etq='días · ')
for c in ('v','i','sg','dur'):           rango(vids, c, etq='videos · ')
rango(vids, 'pct', 0, 100, 'videos largos · ')  # no aplica a shorts
bucle = [v for v in vids if v['pct'] and v['pct'] > 100]
chk(all(not v['lg'] for v in bucle),
    f"% reproducido > 100 solo en shorts ({len(bucle)}): el bucle los cuenta de nuevo")

# clicks nunca por encima de impresiones
mal = [d['f'] for d in dias if d['c'] and d['i'] and d['c'] > d['i']]
chk(not mal, f"días con clicks > impresiones: {len(mal)}")
mal = [v['id'] for v in vids if v['c'] and v['i'] and v['c'] > v['i']]
chk(not mal, f"videos con clicks > impresiones: {len(mal)}")

# nulos
for c in ('v','sg','sp'):
    n = sum(1 for d in dias if d[c] is None)
    chk(n == 0, f"días con {c} nulo: {n}")

# Impresiones y CTR: el API los expone desde enero 2026 y el descargador sigue
# adelante sin ellos si los rechaza. Que falten en TODOS los días es un modo
# degradado conocido; que falten en algunos es un agujero de verdad.
# El CTR se carga a mano y siempre va atrás de los datos que trae el API, así
# que los días sin impresiones son los del final: la frontera entre lo medido y
# lo que falta. Un hueco en el medio, en cambio, sí es un problema.
faltan_i = [i for i, d in enumerate(dias) if d['i'] is None]
if len(faltan_i) == len(dias):
    avisos.append(f"ningún día trae impresiones ({len(dias)}): el panel queda sin CTR")
elif faltan_i:
    al_final = faltan_i == list(range(len(dias) - len(faltan_i), len(dias)))
    chk(al_final,
        f"los {len(faltan_i)} días sin impresiones son los últimos "
        f"({dias[faltan_i[0]]['f']} → {dias[faltan_i[-1]]['f']}): falta cargar el CTR")
else:
    avisos.append("todos los días traen impresiones")
nulo_ing = sorted(d['f'] for d in dias if d['ing'] is None)
chk(nulo_ing == meta['dias_sin_ingresos'],
    f"días sin ingresos liquidados: {nulo_ing or 'ninguno'} (declarados en meta)")
chk(all(f > dias[-30]['f'] for f in nulo_ing),
    "los días sin ingresos son los últimos del export, no huecos sueltos")
for c in ('v','sg'):
    n = sum(1 for v in vids if v[c] is None)
    chk(n == 0, f"videos con {c} nulo: {n}")
# misma regla que en los días: todo o nada
# Misma idea en videos: los que no tienen impresiones son los más nuevos,
# publicados después del último CTR cargado a mano.
sin_iv = [v for v in vids if v['i'] is None]
if len(sin_iv) == len(vids):
    avisos.append(f"ningún video trae impresiones ({len(vids)})")
elif sin_iv:
    corte_i = max((v['pub'] for v in vids if v['i'] is not None), default='')
    tarde = [v for v in sin_iv if v['pub'] < corte_i]
    chk(not tarde,
        f"los {len(sin_iv)} videos sin impresiones son los más nuevos "
        f"(desde {min(v['pub'] for v in sin_iv)})")
else:
    avisos.append("todos los videos traen impresiones")

# ── 4. contra las filas "Total" de los propios exports ────────────────
def totales(patron, campos):
    acc = Counter()
    for ruta in B.listar(patron):
        with open(ruta, encoding='utf-8-sig') as fh:
            filas = list(csv.reader(fh))
        cab = [B.norm(c) for c in filas[0]]
        for f in filas[1:]:
            if f and f[0] == 'Total':
                r = dict(zip(cab, f))
                for k, claves in campos.items():
                    acc[k] += B.num(B.col(r, *claves)) or 0
    return acc

tc = totales('canal_', {'v':['vistas'],'i':['impresiones'],
                        'sg':['suscriptores obtenidos'],'sp':['suscriptores perdidos'],
                        'ing':['ingresos']})
for k, v in tc.items():
    mio = sum(d[k] or 0 for d in dias)
    chk(abs(mio-v) < 1, f"canal · {k}: parseado {mio:,.0f} vs Total del export {v:,.0f}")

tv = totales('videos_', {'v':['vistas'],'i':['impresiones'],'sg':['suscriptores obtenidos']})
avisos.append(f"videos · el Total del export cubre el catálogo entero "
              f"({tv['v']:,.0f} vistas); acá entran solo los publicados desde {B.DESDE}")

# ── 5. cobertura: los videos 2024+ no pueden superar al canal ─────────
vv, cv = sum(v['v'] or 0 for v in vids), sum(d['v'] or 0 for d in dias)
chk(vv <= cv, f"vistas de videos 2024+ ({vv:,.0f}) ≤ vistas del canal ({cv:,.0f}) = {vv/cv*100:.1f} %")

# ── 6. agrupación por mes / quarter / año ─────────────────────────────
mes = defaultdict(lambda: Counter())
for d in dias:
    for c in ('v','i','sg','sp','ing'): mes[d['f'][:7]][c] += d[c] or 0
chk(sum(m['v'] for m in mes.values()) == cv, "suma de meses = suma de días")
q = defaultdict(float); a = defaultdict(float)
for k, m in mes.items():
    q[f"{k[:4]}-Q{(int(k[5:7])-1)//3+1}"] += m['v']; a[k[:4]] += m['v']
chk(abs(sum(q.values())-cv) < 1, "suma de quarters = suma de días")
chk(abs(sum(a.values())-cv) < 1, "suma de años = suma de días")
esperados_mes = (d1.year - d0.year) * 12 + (d1.month - d0.month) + 1
chk(len(mes) == esperados_mes,
    f"meses en la serie: {len(mes)} (el rango {fs[0]}→{fs[-1]} cubre {esperados_mes})")

# meses parciales: solo el del corte
completos = [k for k in mes if k not in meta['meses_parciales']]
import calendar
mal = [k for k in completos
       if sum(1 for d in fs if d.startswith(k)) != calendar.monthrange(int(k[:4]),int(k[5:7]))[1]]
chk(not mal, f"meses marcados completos que no lo están: {mal}")
# Solo el primer y el último mes pueden estar cortados: los del medio, no.
bordes = {fs[0][:7], fs[-1][:7]}
chk(set(meta['meses_parciales']) <= bordes,
    f"meses parciales solo en los bordes: {meta['meses_parciales'] or 'ninguno'}")

# ── 7. categorías ─────────────────────────────────────────────────────
cats = Counter(v['cat'] for v in vids)
etq = set(meta['cat_etiquetas'])
chk(set(cats) <= etq, f"categorías fuera del diccionario: {set(cats)-etq}")
chk(sum(cats.values()) == len(vids), "todo video tiene exactamente una categoría")
sin = cats.get('OTROS', 0)
avisos.append(f"sin clasificar: {sin}/{len(vids)} ({sin/len(vids)*100:.1f} %)")

# ── índice relativo y juegos ──────────────────────────────────────────
con_ix = [v for v in vids if v.get('ix') is not None]
if con_ix:
    import statistics
    med_ix = statistics.median(v['ix'] for v in con_ix)
    # por construcción cada video se divide por la mediana de sus vecinos:
    # el conjunto tiene que quedar centrado en 1
    chk(0.8 <= med_ix <= 1.25, f"índice relativo centrado en 1: mediana {med_ix:.3f}")
    chk(all(v['ix'] > 0 for v in con_ix), "ningún índice negativo o cero")
    elegibles = [v for v in vids if v['lg'] and v['edad'] >= meta['min_dias_video']]
    faltan = [v for v in elegibles if v.get('ix') is None]
    chk(len(faltan) <= meta.get('ventana_ix', 20),
        f"videos elegibles sin índice: {len(faltan)} (solo los de los extremos)")
    avisos.append(f"con índice: {len(con_ix)} de {len(elegibles)} elegibles")

juegos = [v['j'] for v in vids if v.get('j')]
if juegos:
    from collections import Counter
    cj = Counter(juegos)
    avisos.append(f"juegos repetidos: {len(cj)} cubriendo {len(juegos)} videos")
    chk(all(v.get('j') is None or isinstance(v['j'], str) for v in vids),
        "el juego es texto o nada")

# ── 8. CTR ponderado ≠ promedio simple ────────────────────────────────
ci = sum(d['c'] or 0 for d in dias); ii = sum(d['i'] or 0 for d in dias)
con_imp = [d for d in dias if d['i']]
if not con_imp:
    avisos.append("sin impresiones: no hay CTR que chequear")
else:
    pond = ci/ii*100
    simple = sum(d['c']/d['i']*100 for d in con_imp)/len(con_imp)
    avisos.append(f"CTR canal ponderado {pond:.3f} % (promedio simple daría {simple:.3f} %)")
    chk(0 < pond < 100, "CTR del canal en rango")

print('\n'.join('  ok   · '+m for m in avisos))
if fallos:
    print('\n'.join('  FALLA · '+m for m in fallos)); sys.exit(1)
print(f"\n{len(avisos)} chequeos, 0 fallas.")
