"""Compara el analytics.json nuevo contra el que ya está publicado.

    python3 scripts/guardia.py <json_anterior>

validar.py dice si los datos nuevos son coherentes consigo mismos. Esto dice
otra cosa: si son coherentes con la historia. Una corrida automática que
devuelve medio canal pasa todos los chequeos internos y publica un desastre.

Sale con 1 si el panel iría para atrás. Sin argumento, o si el archivo anterior
no existe, no hay con qué comparar y deja pasar.
"""
import json, os, sys

TOLERANCIA = 0.02      # YouTube reajusta cifras hacia atrás; un 2 % es normal
# Cambiar de fuente mueve el piso una vez: el corte queda un día más atrás, los
# privados dejan de contarse. Eso no es una regresión y hay que poder aceptarlo
# a mano, pero solo a mano: en las corridas automáticas la guardia sigue dura.
ACEPTAR = os.environ.get('GUARDIA_ACEPTAR_BAJA', '').strip() == '1'


def cargar(ruta):
    with open(ruta, encoding='utf-8') as fh:
        return json.load(fh)


def main():
    if len(sys.argv) < 2:
        print('guardia: sin archivo anterior, nada que comparar.')
        return 0
    try:
        viejo = cargar(sys.argv[1])
    except (OSError, ValueError) as e:
        print(f'guardia: no se pudo leer el anterior ({e}). Se deja pasar.')
        return 0
    nuevo = cargar('data/analytics.json')

    # Si lo publicado salió de una corrida local con los CSV viejos, comparar
    # conteos contra eso no dice nada: el catálogo es otro. Pasó de verdad, al
    # commitear un analytics.json regenerado a mano encima del del workflow.
    fuente = viejo['meta'].get('fuente')
    de_api = fuente is None or any('_api' in x for x in fuente)
    if not de_api:
        print(f'guardia: lo publicado no vino del API ({", ".join(fuente)}).')
        print('  Los conteos no son comparables; se revisan solo los totales.\n')

    fallas = []
    def chk(ok, msg):
        print(('  ok   · ' if ok else '  FALLA · ') + msg)
        if not ok:
            fallas.append(msg)

    cv, cn = viejo['meta']['corte'], nuevo['meta']['corte']
    chk(cn >= cv, f'el corte no retrocede: {cv} → {cn}')

    dv, dn = len(viejo['dias']), len(nuevo['dias'])
    vv, vn = len(viejo['videos']), len(nuevo['videos'])
    if de_api:
        chk(dn >= dv, f'no se pierden días: {dv} → {dn}')
        chk(vn >= vv, f'no se pierden videos: {vv} → {vn}')
    else:
        print(f'  (se omite: días {dv} → {dn}, videos {vv} → {vn})')

    for campo, etq in (('v', 'vistas'), ('i', 'impresiones')):
        a = sum(d.get(campo) or 0 for d in viejo['dias'])
        b = sum(d.get(campo) or 0 for d in nuevo['dias'])
        chk(b >= a * (1 - TOLERANCIA),
            f'{etq} del canal no caen más de {TOLERANCIA:.0%}: {a:,.0f} → {b:,.0f}')

    hv, hn = len(viejo['meta']['dias_faltantes']), len(nuevo['meta']['dias_faltantes'])
    chk(hn <= hv, f'no aparecen huecos nuevos: {hv} → {hn}')

    if fallas and ACEPTAR:
        print(f'\nguardia: {len(fallas)} problema(s), aceptados a mano '
              '(GUARDIA_ACEPTAR_BAJA=1). Se publica igual.')
        return 0
    if fallas:
        print(f'\nguardia: {len(fallas)} problema(s). No se publica.')
        return 1
    print('\nguardia: los datos nuevos no empeoran a los publicados.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
