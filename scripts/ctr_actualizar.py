"""Mete CTR nuevo en el histórico congelado.

    python3 scripts/ctr_actualizar.py ~/Downloads/*.zip     (las dos pestañas de una)
    python3 scripts/ctr_actualizar.py ~/Downloads/videos.zip ~/Downloads/dias.zip
    python3 scripts/ctr_actualizar.py ctr.csv
    pbpaste | python3 scripts/ctr_actualizar.py      (pegando desde el portapapeles)

El API de YouTube no entrega impresiones ni CTR, así que esa parte se junta a
mano desde YouTube Studio —con la extensión de Claude en Chrome, con el prompt
de PROMPT_CTR.md— y se guarda acá. El resto del panel se sigue actualizando solo.

Entiende dos formatos.

El mejor es el **export nativo de Studio**: el botón de descargar de la pantalla
de Estadísticas, tal cual sale, sea el .zip o el .csv de adentro. Trae el ID de
cada video, así que no hay títulos que adivinar, y no depende de que nadie lea
bien una tabla de trescientas filas. Sirven tanto la pestaña Contenido como la
de Fecha, y los encabezados se buscan por palabra suelta para aguantar que
Studio exporte en español o en inglés.

El otro es una fila por medición, para cuando los datos vienen a mano o de la
extensión del navegador:

    tipo,clave,impresiones,ctr
    dia,2026-09-20,242829,6.92
    video,_kvBe6rUqg8,3040836,7.15

  tipo   'dia' o 'video'
  clave  la fecha (YYYY-MM-DD) o el ID del video
  ctr    porcentaje, como lo muestra Studio

Es incremental: lo que traigas se suma o pisa lo que había, y lo que no traigas
queda intacto. Podés mandar diez filas o el catálogo entero.

Solo biblioteca estándar.
"""
import csv, json, os, re, sys, zipfile
from datetime import date

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
HISTORICO = os.path.join(RAIZ, 'data', 'historico')
ARCHIVOS = {'dia': 'impresiones_dias.csv', 'video': 'impresiones_videos.csv'}
CLAVE = {'dia': 'fecha', 'video': 'id'}
# El histórico de videos es ACUMULADO desde la publicación. Si llega un export
# de "últimos 28 días", las impresiones vienen mucho más chicas y pisarlas borra
# años de datos. Por debajo de este umbral se asume que el período está mal.
CAIDA_SOSPECHOSA = 0.5
# Studio no exporta más de 500 filas por tabla, y no avisa: corta y entrega el
# archivo como si estuviera entero. Por eso el histórico se armó con la serie
# diaria partida en pedazos —del 2024-01-01 al 2025-05-15 hay 500 días justos—.
LIMITE_STUDIO = 500
# El panel arranca en 2024. Un export más viejo tirado en Downloads no tiene por
# qué entrar: pasó, y sumó todo 2023 sin que nadie lo notara hasta contar las
# filas. Se lee de donde está definido de verdad para no tener dos verdades.
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from build_analytics import DESDE
except ImportError:
    DESDE = '2024-01-01'


def num(v):
    """'1.234.567', '1,234,567' o '12,5' -> float. Studio varía según el idioma."""
    v = (v or '').strip().replace('%', '').replace(' ', '')
    if not v:
        return None
    # Studio escribe 1.234.567 en español y 1,234,567 en inglés, y el decimal
    # es el otro símbolo. Con los dos presentes, el que va último es el decimal.
    if ',' in v and '.' in v:
        dec = ',' if v.rfind(',') > v.rfind('.') else '.'
        v = v.replace('.' if dec == ',' else ',', '').replace(dec, '.')
    elif ',' in v or '.' in v:
        # Un solo símbolo: lo decide el último grupo. Uno o dos dígitos detrás
        # es un decimal (6,92); tres es separador de miles (1.234).
        sep = ',' if ',' in v else '.'
        ent, _, res = v.rpartition(sep)
        v = (f'{ent.replace(sep, "")}.{res}' if len(res) <= 2
             else v.replace(sep, ''))
    try:
        return float(v)
    except ValueError:
        return None


def indice_titulos():
    """Título -> id, para aceptar lo que se lee en pantalla.

    En la tabla de Studio se ve el título, no el id: pedirle a la extensión que
    saque el id de cada enlace es una fuente de error más. Se acepta el título y
    se resuelve acá contra el catálogo que ya está en el panel.
    """
    ruta = os.path.join(RAIZ, 'data', 'analytics.json')
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding='utf-8') as fh:
        vids = json.load(fh).get('videos', [])
    idx = {}
    for v in vids:
        idx.setdefault(normalizar(v.get('t', '')), []).append(v['id'])
    # un título repetido no identifica nada: se descarta
    return {k: ids[0] for k, ids in idx.items() if len(ids) == 1 and k}


def normalizar(t):
    """Minúsculas y sin dobles espacios: Studio recorta y adorna los títulos."""
    return re.sub(r'\s+', ' ', (t or '').strip().lower())


ES_ID = re.compile(r'[A-Za-z0-9_-]{11}$')

MESES = {m: i for i, m in enumerate(
    ['ene:jan', 'feb', 'mar', 'abr:apr', 'may', 'jun', 'jul', 'ago:aug',
     'sep:set', 'oct', 'nov', 'dic:dec'], 1)
    for m in m.split(':')}


def a_fecha(v):
    """'2026-09-14', 'Sep 14, 2026' o '14 sept 2026' -> 'YYYY-MM-DD', o ''.

    Studio exporta la fecha en el idioma de la cuenta y a veces cambia de forma
    sin avisar, así que se aceptan las tres que se vieron.
    """
    v = (v or '').strip().strip('"')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
        return v
    m = (re.match(r'([A-Za-z]{3})\w*\.?\s+(\d{1,2}),?\s+(\d{4})', v)      # Sep 14, 2026
         or re.match(r'(\d{1,2})\s+(?:de\s+)?([A-Za-z]{3})\w*\.?\s+(?:de\s+)?(\d{4})', v))
    if not m:
        return ''
    a, b, anio = m.groups()
    mes, dia = (a, b) if a[0].isalpha() else (b, a)
    n = MESES.get(mes.lower())
    return f'{int(anio):04d}-{n:02d}-{int(dia):02d}' if n else ''


def textos(ruta):
    """El contenido de cada CSV: el archivo suelto, o los que traiga el zip.

    El botón de descargar de Studio da un .zip con varios CSV adentro. Pedirle
    al usuario que lo abra y busque el correcto es una oportunidad más de
    equivocarse: se lee tal cual bajó.
    """
    if ruta and zipfile.is_zipfile(ruta):
        with zipfile.ZipFile(ruta) as z:
            csvs = [n for n in z.namelist() if n.lower().endswith('.csv')]
            # Junto a la tabla vienen los totales del rango, que no son filas.
            tabla = [n for n in csvs if 'total' not in n.lower()]
            return [z.read(n).decode('utf-8-sig') for n in (tabla or csvs)]
    if ruta:
        return [open(ruta, encoding='utf-8-sig').read()]
    return [sys.stdin.read()]


def columna(cab, *alias):
    """Índice de la primera columna cuyo nombre contenga alguno de los alias.

    Por nombre y no por posición: Studio agrega y saca columnas según lo que
    tengas elegido en pantalla, y traduce los encabezados.
    """
    for i, c in enumerate(cab):
        bajo = c.strip().lower()
        if any(a in bajo for a in alias):
            return i
    return None


def como_export(filas):
    """Export nativo de Studio -> tipo,clave,impresiones,ctr. [] si no lo es."""
    if not filas:
        return []
    cab = filas[0]
    # La primera columna dice de qué tabla salió: el catálogo o la serie diaria.
    if columna(cab, 'contenido', 'content') == 0:
        tipo = 'video'
    elif columna(cab, 'fecha', 'date') == 0:
        tipo = 'dia'
    else:
        return []
    i_imp = columna(cab, 'impresion', 'impression')
    i_ctr = columna(cab, 'clic', 'click')
    if i_imp is None or i_ctr is None:
        # Es un export de Studio, pero de la vista simple: exporta solo las
        # columnas que están en pantalla, y ahí no figuran las impresiones. Sin
        # este aviso el archivo se descarta en silencio y parece que no sirviera.
        print(f'  es un export de Studio ({tipo}) pero no trae impresiones ni CTR.')
        print(f'    columnas: {", ".join(c.strip() for c in cab if c.strip())}')
        print('    Volvé a bajarlo desde MODO AVANZADO agregando las columnas '
              '"Impresiones"\n    y "Porcentaje de clics de las impresiones".')
        return []
    out = []
    for f in filas[1:]:
        if len(f) <= max(i_imp, i_ctr):
            continue
        clave = f[0].strip()
        # La fila de arriba resume el rango entero: no es un video ni un día.
        if not clave or clave.lower() in ('total', 'totales', 'totals'):
            continue
        if tipo == 'dia':
            clave = a_fecha(clave) or clave
        out.append([tipo, clave, f[i_imp], f[i_ctr]])
    if len(out) >= LIMITE_STUDIO:
        print(f'  ¡OJO! {len(out)} filas, y Studio corta en {LIMITE_STUDIO}: '
              'este export está truncado.')
        print('    Días: pedilo por año, uno por vez.')
        print('    Videos: ordená la tabla por fecha de publicación, los más '
              'nuevos primero.')
    return out


def crudas(ruta):
    """Todas las filas de entrada, venga el export de Studio o una lista."""
    out = []
    # Con nombre y todo: un comodín en la línea de comandos puede agarrar de
    # más, y el nombre del archivo de Studio lleva adentro el período que trae.
    if ruta:
        print(f'leyendo {os.path.basename(ruta)}')
    for texto in textos(ruta):
        filas = [f for f in csv.reader(texto.splitlines()) if f]
        # Si no es un export reconocible se deja pasar tal cual: abajo se filtra
        # por la primera columna, así que la basura no llega a ningún lado.
        out += como_export(filas) or filas
    return out


def leer_entrada(rutas=()):
    """Filas de los archivos o de la entrada estándar, tolerando encabezado."""
    titulos, sin_resolver, viejos = indice_titulos(), [], []
    filas = []
    for f in [f for r in (rutas or [None]) for f in crudas(r)]:
        if len(f) < 4:
            continue
        tipo = f[0].strip().lower()
        if tipo not in ARCHIVOS:
            continue                      # encabezado o línea suelta
        # Un CTR escrito "5,80" parte la fila en cinco campos y el lector se
        # quedaría con "5": medio punto de CTR perdido sin que nadie se entere.
        # Las impresiones son enteras y el CTR es el decimal, así que los
        # campos que sobran pertenecen al último.
        if len(f) > 4:
            f = [f[0], f[1], f[2], ','.join(x.strip() for x in f[3:])]
        clave, imp, ctr = f[1].strip(), num(f[2]), num(f[3])
        if not clave or imp is None or ctr is None:
            continue
        if tipo == 'dia' and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', clave):
            print(f'  se saltea: fecha con formato raro -> {clave}')
            continue
        if tipo == 'dia' and clave < DESDE:
            viejos.append(clave)
            continue
        if tipo == 'video' and not ES_ID.fullmatch(clave):
            resuelto = titulos.get(normalizar(clave))
            if not resuelto:
                sin_resolver.append(clave)
                continue
            clave = resuelto
        if not 0 <= ctr <= 100:
            print(f'  se saltea: CTR fuera de rango -> {clave} = {ctr}')
            continue
        filas.append((tipo, clave, imp, ctr))
    if viejos:
        print(f'  {len(viejos)} día(s) anteriores a {DESDE} ignorados '
              f'({min(viejos)} … {max(viejos)}): el panel arranca ahí. '
              'Si no esperabas eso, hay un export viejo en la lista.')
    if sin_resolver:
        print(f'  {len(sin_resolver)} título(s) sin match en el catálogo:')
        for t in sin_resolver[:5]:
            print(f'    {t[:70]}')
        if len(sin_resolver) > 5:
            print(f'    ...y {len(sin_resolver) - 5} más')
    return filas


def catalogo():
    """Los IDs que el panel muestra hoy, para saber si el export los cubre."""
    ruta = os.path.join(RAIZ, 'data', 'analytics.json')
    if not os.path.exists(ruta):
        return set()
    with open(ruta, encoding='utf-8') as fh:
        return {v['id'] for v in json.load(fh).get('videos', [])}


def cargar(tipo):
    ruta = os.path.join(HISTORICO, ARCHIVOS[tipo])
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding='utf-8-sig') as fh:
        return {f[0]: [f[1], f[2]] for f in list(csv.reader(fh))[1:] if len(f) >= 3}


def guardar(tipo, datos):
    ruta = os.path.join(HISTORICO, ARCHIVOS[tipo])
    os.makedirs(HISTORICO, exist_ok=True)
    with open(ruta, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow([CLAVE[tipo], 'impresiones', 'clicks'])
        for k in sorted(datos):
            w.writerow([k, datos[k][0], datos[k][1]])


def main():
    rutas = [a for a in sys.argv[1:] if not a.startswith('-')]
    for r in rutas:
        if not os.path.exists(r):
            sys.exit(f'No existe {r}.')
    if not rutas and sys.stdin.isatty():
        sys.exit(__doc__)

    filas = leer_entrada(rutas)
    if not filas:
        sys.exit('No se reconoció ninguna fila. Revisá el formato: '
                 'tipo,clave,impresiones,ctr')

    for tipo in ARCHIVOS:
        propias = [f for f in filas if f[0] == tipo]
        if not propias:
            continue
        datos = cargar(tipo)
        nuevos = cambiados = iguales = 0
        sospechosos = []
        for _, clave, imp, ctr in propias:
            # Un día es un día: su cifra no crece. Un video sí acumula, así que
            # que baje quiere decir que el período no es el mismo.
            if tipo == 'video' and clave in datos:
                try:
                    antes = float(datos[clave][0])
                except (TypeError, ValueError):
                    antes = 0
                if antes and imp < antes * CAIDA_SOSPECHOSA:
                    sospechosos.append((clave, antes, imp))
                    continue
            # el histórico guarda clicks, no el porcentaje: así el CTR de un
            # período es suma(clicks)/suma(impresiones) y no un promedio de CTRs
            fila = [str(int(imp)), str(round(imp * ctr / 100, 4))]
            if clave not in datos:
                nuevos += 1
            elif datos[clave] != fila:
                cambiados += 1
            else:
                iguales += 1
            datos[clave] = fila
        guardar(tipo, datos)
        print(f'{ARCHIVOS[tipo]}: {len(datos)} en total '
              f'(+{nuevos} nuevos, {cambiados} actualizados, {iguales} sin cambio)')
        # El rango es lo que delata un export del período equivocado: los
        # conteos solos no dicen nada, un día de más se ve igual que uno de
        # menos. Para los videos importa el final, que es hasta dónde llega.
        if tipo == 'dia':
            claves = sorted(c for _, c, _, _ in propias)
            print(f'  entraron {len(propias)} días, de {claves[0]} a {claves[-1]}')
        else:
            # Lo que importa no es cuántas filas trajo el export sino cuántos de
            # los videos que el panel muestra quedaron con impresiones. Un
            # export de 500 filas puede traer cientos de videos viejos y
            # saltearse los nuevos, que son los que interesan.
            cat = catalogo()
            if cat:
                print(f'  del panel ({len(cat)} videos), {len(cat & set(datos))} '
                      'tienen impresiones')
                sobran = len(set(datos) - cat)
                if sobran:
                    print(f'  ({sobran} id(s) fuera del catálogo: videos de '
                          'antes de 2024 o shorts. El panel los ignora.)')
        if sospechosos:
            print(f'\n  {len(sospechosos)} video(s) NO se tocaron: traían menos de '
                  f'la mitad de las impresiones guardadas.')
            print('  El histórico es acumulado desde la publicación. Si el export '
                  'salió\n  con "últimos 28 días", pedilo de nuevo con el rango '
                  'completo.')
            for k, a, b in sospechosos[:5]:
                print(f'    {k}  {a:,.0f} -> {b:,.0f}'.replace(',', '.'))
            if len(sospechosos) > 5:
                print(f'    ...y {len(sospechosos) - 5} más')

    print('\nListo. Para que el panel lo tome:')
    print('  git add data/historico && git commit -m "CTR al '
          + date.today().isoformat() + '" && git push')
    print('El push solo dispara la actualización del panel; tarda un par de minutos.')


if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:
        pass        # alguien cortó la salida con head o less
