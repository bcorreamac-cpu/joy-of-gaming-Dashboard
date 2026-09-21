"""Mira un export de Studio y dice si alcanza, sin tocar nada.

    python3 scripts/ctr_revisar.py ~/Downloads/*.zip

Studio corta las tablas largas sin avisar y exporta solo las columnas que están
en pantalla. Las dos cosas pasaron, y las dos se notaron tarde: primero se
cargaba el archivo y después aparecía el problema, con el histórico ya escrito.

Esto va antes. Abre cada archivo, mira todos los CSV de adentro, dice qué es
cada uno y qué aportaría, y compara contra lo que ya hay y contra el catálogo
del panel. No escribe nada.

Solo biblioteca estándar.
"""
import os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ctr_actualizar import (DESDE, textos, columna, como_export, cargar,
                            catalogo)
import csv as _csv

# Studio cierra las cifras con dos o tres días de atraso; más que eso es falta.
ATRASO = 3


def tabla(texto):
    """Las filas de un CSV, sin líneas vacías."""
    return [f for f in _csv.reader(texto.splitlines()) if f]


def describir(ruta):
    """Qué trae cada CSV del archivo. Devuelve las filas aprovechables."""
    print(f'\n=== {os.path.basename(ruta)}')
    utiles = []
    for texto in textos(ruta):
        filas = tabla(texto)
        if not filas:
            continue
        cab = [c.strip() for c in filas[0]]
        n = len(filas) - 1
        primera = cab[0] if cab else '?'
        tiene = [e for e, a in (('impresiones', ('impresion', 'impression')),
                                ('CTR', ('clic', 'click')))
                 if columna(cab, *a) is not None]
        print(f'  · {n} filas · empieza en "{primera}" · '
              f'{"trae " + " y ".join(tiene) if tiene else "SIN impresiones ni CTR"}')
        rec = como_export(filas)
        if rec:
            utiles += rec
        elif tiene:
            print(f'    no se puede usar (columnas: {", ".join(cab[:6])}…)')
    return utiles


def main():
    rutas = [a for a in sys.argv[1:] if not a.startswith('-')]
    rutas = [r for r in rutas if os.path.exists(r)]
    if not rutas:
        sys.exit('Pasame los archivos: python3 scripts/ctr_revisar.py ~/Downloads/*.zip')

    filas = []
    for r in rutas:
        filas += describir(r)

    dias = {c: (i, t) for tp, c, i, t in filas if tp == 'dia'}
    vids = {c: (i, t) for tp, c, i, t in filas if tp == 'video'}

    print('\n=== Lo que aportan, sumados')
    print(f'  días : {len(dias)}')
    print(f'  videos: {len(vids)}')

    # ── días: ¿cubren el rango, o quedan huecos? ─────────────────────────
    hasta = (date.today() - timedelta(days=ATRASO)).isoformat()
    ya = cargar('dia')
    cubiertos = set(ya) | set(dias)
    d0, d1 = date.fromisoformat(DESDE), date.fromisoformat(hasta)
    faltan = []
    d = d0
    while d <= d1:
        if d.isoformat() not in cubiertos:
            faltan.append(d.isoformat())
        d += timedelta(days=1)

    print('\n=== Serie diaria (lo que ya hay + lo que traen estos archivos)')
    print(f'  rango que debería estar cubierto: {DESDE} … {hasta}')
    if not faltan:
        print('  COMPLETA: no falta ningún día.')
    else:
        # Un bloque al final es la frontera normal del CTR; en el medio es hueco.
        al_final = faltan == [d.isoformat() for d in
                              (d1 - timedelta(days=i) for i in range(len(faltan)))][::-1]
        print(f'  faltan {len(faltan)} días: {faltan[0]} … {faltan[-1]}')
        print('  (están todos al final: es la frontera normal del CTR)' if al_final
              else '  HAY HUECOS EN EL MEDIO: validar.py va a rechazar esto.')
        print(f'  -> pedí la pestaña Fecha del período {faltan[0]} a hoy.')

    # ── videos: lo que importa es cuántos del panel quedan cubiertos ─────
    cat, yav = catalogo(), cargar('video')
    if cat:
        print('\n=== Videos del panel')
        antes = cat & set(yav)
        ahora = cat & (set(yav) | set(vids))
        print(f'  el panel tiene {len(cat)}')
        print(f'  con impresiones hoy: {len(antes)}')
        print(f'  con impresiones si cargás esto: {len(ahora)}')
        nuevos = cat & set(vids) - set(yav)
        if nuevos:
            print(f'  ({len(nuevos)} que hoy no tienen ninguna)')
        sin = sorted(cat - (set(yav) | set(vids)))
        if sin:
            print(f'  quedarían {len(sin)} sin impresiones: {", ".join(sin[:5])}'
                  + ('…' if len(sin) > 5 else ''))
            print('  -> suelen ser los más nuevos, que Studio todavía no cerró.')
        ajenos = len(set(vids) - cat)
        if ajenos:
            print(f'  ({ajenos} id(s) del export no están en el panel: videos de '
                  'antes de 2024 o shorts. Entran al histórico pero se ignoran.)')

    # ── veredicto ────────────────────────────────────────────────────────
    print('\n=== Veredicto')
    problemas = []
    if not dias and not vids:
        problemas.append('ningún archivo trae impresiones y CTR usables')
    if faltan and len(faltan) > 7:
        problemas.append(f'{len(faltan)} días sin impresiones')
    if cat and len(cat & (set(yav) | set(vids))) < len(cat) * 0.9:
        problemas.append('menos del 90 % de los videos del panel quedan cubiertos')
    if problemas:
        for p in problemas:
            print(f'  FALTA · {p}')
        print('\n  No cargues todavía: falta material.')
        return 1
    print('  Sirve. Cargalo con:')
    print('    python3 scripts/ctr_actualizar.py ' +
          ' '.join(f'"{r}"' for r in rutas))
    return 0


if __name__ == '__main__':
    sys.exit(main())
