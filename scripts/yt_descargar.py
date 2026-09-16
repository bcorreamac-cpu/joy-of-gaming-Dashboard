"""Baja los datos del canal desde las APIs de YouTube y los deja en data/entrada/.

    python3 scripts/yt_descargar.py

Escribe dos CSV con los MISMOS encabezados que los exports de YouTube Studio,
así build_analytics.py no cambia y validar.py sigue sirviendo:

    data/entrada/canal_api.csv    una fila por día
    data/entrada/videos_api.csv   una fila por video

Necesita tres variables de entorno (secrets en GitHub Actions):
    YT_CLIENT_ID  YT_CLIENT_SECRET  YT_REFRESH_TOKEN

Se sacan una sola vez con scripts/yt_autorizar.py.

Dos APIs distintas, porque ninguna trae todo:
  - Analytics  -> métricas (vistas, impresiones, CTR, subs, ingresos)
  - Data       -> catálogo (títulos, fecha de publicación, duración)

Solo biblioteca estándar.
"""
import csv, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, timedelta

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ENTRADA = os.path.join(RAIZ, 'data', 'entrada')
DESDE = os.environ.get('YT_DESDE', '2024-01-01')
# YouTube cierra los datos con unos días de atraso; pedir hasta ayer devuelve
# cifras que después se mueven. Dos días es el margen que usa el propio Studio.
ATRASO = int(os.environ.get('YT_ATRASO', '2'))

ANALYTICS = 'https://youtubeanalytics.googleapis.com/v2/reports'
DATA = 'https://www.googleapis.com/youtube/v3/'
TOKEN = 'https://oauth2.googleapis.com/token'

# Las impresiones y el CTR se expusieron en el API recién el 15/1/2026. Si por
# lo que sea el canal no las devuelve, el pedido entero falla con un 400. Van
# aparte para poder reintentar sin ellas: es mejor un panel sin CTR que ninguno.
OPCIONALES = ['videoThumbnailImpressions', 'videoThumbnailImpressionsClickRate']
M_CANAL = ['views', 'estimatedMinutesWatched', 'subscribersGained', 'subscribersLost',
           'estimatedRevenue']
M_VIDEO = ['views', 'subscribersGained', 'averageViewPercentage', 'averageViewDuration']

CAB_CANAL = ['Fecha', 'Impresiones de miniaturas', 'Tasa de clics de las miniaturas (%)',
             'Suscriptores obtenidos', 'Suscriptores perdidos', 'RPM (USD)', 'Vistas',
             'Tiempo de reproducción (horas)', 'Ingresos estimados (USD)']
CAB_VIDEOS = ['Contenido', 'Título del video', 'Tiempo de publicación del video', 'Duración',
              'Porcentaje promedio reproducido (%)', 'Suscriptores obtenidos', 'Vistas',
              'Duración promedio de vistas', 'Impresiones de miniaturas',
              'Tasa de clics de las miniaturas (%)']


# ── HTTP ──────────────────────────────────────────────────────────────────
class ErrorAPI(Exception):
    def __init__(self, codigo, cuerpo):
        super().__init__(f'{codigo}: {cuerpo}')
        self.codigo, self.cuerpo = codigo, cuerpo


def get(url, params, token, intentos=4):
    """GET con reintento exponencial: 429 y 5xx son moneda corriente."""
    u = url + '?' + urllib.parse.urlencode(params, doseq=True)
    for n in range(intentos):
        req = urllib.request.Request(u, headers={'Authorization': 'Bearer ' + token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode()[:500]
            if e.code in (429, 500, 502, 503) and n < intentos - 1:
                time.sleep(2 ** n * 2)
                continue
            raise ErrorAPI(e.code, cuerpo)
        except urllib.error.URLError as e:
            if n < intentos - 1:
                time.sleep(2 ** n * 2)
                continue
            raise SystemExit(f'No se pudo conectar a {url}: {e}')


# Se resuelve en el primer pedido y vale para toda la corrida.
HAY_CTR = None


def consultar(token, params, metricas):
    """Pide con las métricas opcionales; si el API las rechaza, va sin ellas.

    Un 400 por métrica desconocida no se reintenta a ciegas: se cae de nuevo
    igual. Se quitan las opcionales una sola vez y queda marcado para el resto
    de la corrida.
    """
    global HAY_CTR
    con = metricas + (OPCIONALES if HAY_CTR is not False else [])
    try:
        r = get(ANALYTICS, {**params, 'metrics': ','.join(con)}, token)
        if HAY_CTR is None and OPCIONALES[0] in con:
            HAY_CTR = True
        return r
    except ErrorAPI as e:
        if e.codigo != 400 or HAY_CTR is False:
            raise SystemExit(f'El API de Analytics respondió {e.codigo}\n{e.cuerpo}')
        print('AVISO: el API rechazó las impresiones y el CTR. Se sigue sin '
              'ellas; el panel va a mostrar esas columnas vacías.\n'
              f'       Respuesta de Google: {e.cuerpo[:200]}', file=sys.stderr)
        HAY_CTR = False
        return get(ANALYTICS, {**params, 'metrics': ','.join(metricas)}, token)


def token_de_acceso():
    faltan = [k for k in ('YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN')
              if not os.environ.get(k)]
    if faltan:
        sys.exit('Faltan variables de entorno: ' + ', '.join(faltan) +
                 '\nSe obtienen una sola vez con scripts/yt_autorizar.py.')
    datos = urllib.parse.urlencode({
        'client_id': os.environ['YT_CLIENT_ID'],
        'client_secret': os.environ['YT_CLIENT_SECRET'],
        'refresh_token': os.environ['YT_REFRESH_TOKEN'],
        'grant_type': 'refresh_token'}).encode()
    req = urllib.request.Request(TOKEN, datos,
                                 {'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)['access_token']
    except urllib.error.HTTPError as e:
        sys.exit('No se pudo renovar el token: ' + e.read().decode()[:300] +
                 '\n\nSi dice invalid_grant, el refresh token caducó. Suele pasar '
                 'cuando la pantalla de consentimiento quedó en modo "Prueba": '
                 'publicala y volvé a correr scripts/yt_autorizar.py.')


# ── Analytics: serie diaria del canal ─────────────────────────────────────
def serie_diaria(token, d0, d1):
    """Un pedido por año: el API corta a 'unos miles' de filas por respuesta."""
    filas = {}
    ini = date.fromisoformat(d0)
    while ini <= date.fromisoformat(d1):
        fin = min(date(ini.year, 12, 31), date.fromisoformat(d1))
        r = consultar(token, {
            'ids': 'channel==MINE', 'startDate': ini.isoformat(), 'endDate': fin.isoformat(),
            'dimensions': 'day', 'sort': 'day'}, M_CANAL)
        cols = [c['name'] for c in r.get('columnHeaders', [])]
        for f in r.get('rows', []):
            d = dict(zip(cols, f))
            filas[d['day']] = d
        ini = date(fin.year + 1, 1, 1)
    return [filas[k] for k in sorted(filas)]


def escribir_canal(filas, ruta):
    with open(ruta, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(CAB_CANAL)
        for d in filas:
            vistas = d.get('views') or 0
            ing = d.get('estimatedRevenue')
            w.writerow([
                d['day'],
                num(d.get('videoThumbnailImpressions')),
                num(d.get('videoThumbnailImpressionsClickRate')),
                num(d.get('subscribersGained')),
                num(d.get('subscribersLost')),
                '' if not ing or not vistas else round(ing / (vistas / 1000), 3),
                num(vistas),
                num(round((d.get('estimatedMinutesWatched') or 0) / 60, 4)),
                num(ing),
            ])


def num(v):
    """Un None se escribe vacío, no como cero: no es lo mismo."""
    return '' if v is None else v


# ── Data API: catálogo del canal ──────────────────────────────────────────
def dato(url, params, token):
    try:
        return get(url, params, token)
    except ErrorAPI as e:
        raise SystemExit(f'El API de Data respondió {e.codigo}\n{e.cuerpo}')


def catalogo(token):
    """Todos los uploads del canal con título, fecha y duración."""
    ch = dato(DATA + 'channels', {'part': 'contentDetails', 'mine': 'true'}, token)
    items = ch.get('items') or []
    if not items:
        sys.exit('La cuenta autorizada no tiene un canal asociado.')
    subidas = items[0]['contentDetails']['relatedPlaylists']['uploads']

    vids, pagina = {}, None
    while True:
        p = {'part': 'contentDetails,snippet', 'playlistId': subidas, 'maxResults': 50}
        if pagina:
            p['pageToken'] = pagina
        r = dato(DATA + 'playlistItems', p, token)
        for it in r.get('items', []):
            cd, sn = it['contentDetails'], it['snippet']
            pub = (cd.get('videoPublishedAt') or sn.get('publishedAt') or '')[:10]
            if not pub or pub < DESDE:
                continue                    # fuera de la ventana del dashboard
            vids[cd['videoId']] = {'id': cd['videoId'], 'titulo': sn.get('title', ''),
                                   'pub': pub}
        pagina = r.get('nextPageToken')
        if not pagina:
            break

    # las duraciones vienen de otro endpoint, de a 50
    ids = list(vids)
    for i in range(0, len(ids), 50):
        r = dato(DATA + 'videos', {'part': 'contentDetails', 'id': ','.join(ids[i:i + 50])}, token)
        for it in r.get('items', []):
            vids[it['id']]['dur'] = iso_a_segundos(it['contentDetails'].get('duration', ''))
    return vids


def iso_a_segundos(v):
    """'PT1M49S' -> 109."""
    m = re.fullmatch(r'P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?', v or '')
    if not m:
        return ''
    d, h, mi, s = (float(x or 0) for x in m.groups())
    return int(d * 86400 + h * 3600 + mi * 60 + s)


# ── Analytics: métricas por video ─────────────────────────────────────────
def metricas_video(token, ids, d0, d1, lote=200):
    """El filtro `video==` acepta varios IDs por pedido; se va de a lotes."""
    out = {}
    for i in range(0, len(ids), lote):
        trozo = ids[i:i + lote]
        r = consultar(token, {
            'ids': 'channel==MINE', 'startDate': d0, 'endDate': d1,
            'dimensions': 'video', 'filters': 'video==' + ','.join(trozo),
            'maxResults': len(trozo), 'sort': '-views'}, M_VIDEO)
        cols = [c['name'] for c in r.get('columnHeaders', [])]
        for f in r.get('rows', []):
            d = dict(zip(cols, f))
            out[d['video']] = d
    return out


def escribir_videos(cat, met, ruta):
    with open(ruta, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(CAB_VIDEOS)
        for v in sorted(cat.values(), key=lambda x: x['pub']):
            m = met.get(v['id'], {})
            # El API omite las filas en cero, así que un conteo ausente es un
            # cero real. Un promedio o un CTR ausentes, en cambio, no existen:
            # esos van vacíos, para que no se lean como "rindió 0 %".
            cero = lambda k: m.get(k) if m.get(k) is not None else 0
            # ...salvo si el API ni siquiera expone la métrica: ahí va vacío,
            # porque "no lo sabemos" no es "fueron cero".
            imp = cero('videoThumbnailImpressions') if HAY_CTR else ''
            w.writerow([
                v['id'], v['titulo'], v['pub'], num(v.get('dur')),
                num(m.get('averageViewPercentage')),
                cero('subscribersGained'),
                cero('views'),
                num(m.get('averageViewDuration')),
                imp,
                num(m.get('videoThumbnailImpressionsClickRate')),
            ])


# ── comprobación ──────────────────────────────────────────────────────────
def comprobar():
    """Un pedido chico que dice qué devuelve de verdad ESTE canal.

    Las impresiones y el CTR se agregaron al API el 15/1/2026. En vez de
    confiar en eso, se pregunta.
    """
    token = token_de_acceso()
    print('Token renovado: las credenciales sirven.\n')

    ayer = (date.today() - timedelta(ATRASO)).isoformat()
    base = {'ids': 'channel==MINE', 'startDate': ayer, 'endDate': ayer, 'dimensions': 'day'}

    # Las dos primeras son imprescindibles; las impresiones, no.
    graves = []
    for etq, ms, esencial in [('métricas base   ', M_CANAL[:4], True),
                              ('ingresos         ', ['estimatedRevenue'], True),
                              ('impresiones y CTR', OPCIONALES, False)]:
        try:
            r = get(ANALYTICS, {**base, 'metrics': ','.join(ms)}, token)
            cols = [c['name'] for c in r.get('columnHeaders', []) if c['name'] != 'day']
            fila = (r.get('rows') or [[]])[0]
            print(f'  OK    {etq}  {", ".join(cols)}')
            if fila:
                print(f'        {ayer}: ' + ', '.join(
                    f'{c}={v}' for c, v in zip(cols, fila[1:])))
        except ErrorAPI as e:
            print(f'  {"FALLA" if esencial else "aviso"} {etq}  {e.codigo}')
            print(f'        {e.cuerpo[:220]}')
            if esencial:
                graves.append(etq.strip())

    try:
        ch = get(DATA + 'channels', {'part': 'contentDetails,snippet', 'mine': 'true'}, token)
        it = (ch.get('items') or [{}])[0]
        print(f"\n  OK    catálogo (Data API)   canal: "
              f"{it.get('snippet', {}).get('title', '?')}")
    except ErrorAPI as e:
        print(f'\n  FALLA catálogo (Data API)   {e.codigo}: {e.cuerpo[:200]}')
        graves.append('catálogo')

    print('\nSi "impresiones y CTR" falla, el panel funciona igual: esas dos '
          'columnas quedan vacías.')
    if graves:
        print('\nFalta algo imprescindible: ' + ', '.join(graves))
        return 1
    return 0


# ── main ──────────────────────────────────────────────────────────────────
def main():
    if '--comprobar' in sys.argv:
        return comprobar()
    hasta = os.environ.get('YT_HASTA') or (date.today() - timedelta(ATRASO)).isoformat()
    if hasta < DESDE:
        sys.exit(f'La ventana está al revés: {DESDE} -> {hasta}')
    os.makedirs(ENTRADA, exist_ok=True)
    token = token_de_acceso()

    dias = serie_diaria(token, DESDE, hasta)
    if not dias:
        sys.exit('El API no devolvió ningún día. No se toca nada de data/entrada/.')
    escribir_canal(dias, os.path.join(ENTRADA, 'canal_api.csv'))
    print(f"canal_api.csv   {len(dias)} días ({dias[0]['day']} → {dias[-1]['day']})")

    cat = catalogo(token)
    met = metricas_video(token, list(cat), DESDE, hasta)
    escribir_videos(cat, met, os.path.join(ENTRADA, 'videos_api.csv'))
    sin = len(cat) - len(met)
    print(f'videos_api.csv  {len(cat)} videos publicados desde {DESDE}'
          + (f' ({sin} sin métricas en la ventana)' if sin else ''))


if __name__ == '__main__':
    main()
