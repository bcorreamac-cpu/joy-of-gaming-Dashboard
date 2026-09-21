"""Mete CTR nuevo en el histórico congelado.

    python3 scripts/ctr_actualizar.py ctr.csv
    pbpaste | python3 scripts/ctr_actualizar.py      (pegando desde el portapapeles)

El API de YouTube no entrega impresiones ni CTR, así que esa parte se junta a
mano desde YouTube Studio —con la extensión de Claude en Chrome, con el prompt
de PROMPT_CTR.md— y se guarda acá. El resto del panel se sigue actualizando solo.

Formato de entrada, una fila por medición:

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
import csv, json, os, re, sys
from datetime import date

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
HISTORICO = os.path.join(RAIZ, 'data', 'historico')
ARCHIVOS = {'dia': 'impresiones_dias.csv', 'video': 'impresiones_videos.csv'}
CLAVE = {'dia': 'fecha', 'video': 'id'}
# El histórico de videos es ACUMULADO desde la publicación. Si llega un export
# de "últimos 28 días", las impresiones vienen mucho más chicas y pisarlas borra
# años de datos. Por debajo de este umbral se asume que el período está mal.
CAIDA_SOSPECHOSA = 0.5


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


def leer_entrada(ruta=None):
    """Filas del archivo o de la entrada estándar, tolerando encabezado."""
    texto = open(ruta, encoding='utf-8-sig').read() if ruta else sys.stdin.read()
    titulos, sin_resolver = indice_titulos(), []
    filas = []
    for f in csv.reader(texto.splitlines()):
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
    if sin_resolver:
        print(f'  {len(sin_resolver)} título(s) sin match en el catálogo:')
        for t in sin_resolver[:5]:
            print(f'    {t[:70]}')
        if len(sin_resolver) > 5:
            print(f'    ...y {len(sin_resolver) - 5} más')
    return filas


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
    ruta = next((a for a in sys.argv[1:] if not a.startswith('-')), None)
    if ruta and not os.path.exists(ruta):
        sys.exit(f'No existe {ruta}.')
    if not ruta and sys.stdin.isatty():
        sys.exit(__doc__)

    filas = leer_entrada(ruta)
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
    print('Y después corré el workflow "Actualizar el panel" en Actions.')


if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:
        pass        # alguien cortó la salida con head o less
