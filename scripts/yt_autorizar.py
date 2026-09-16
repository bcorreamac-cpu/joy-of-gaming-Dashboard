"""Paso único: consigue el refresh token de YouTube. Se corre UNA vez, a mano.

    python3 scripts/yt_autorizar.py

Abre el navegador, pide permiso sobre el canal y escupe el refresh token para
pegar en los secrets de GitHub. De ahí en adelante el workflow se renueva solo:
el refresh token no caduca mientras la app esté "En producción".

OJO: si la pantalla de consentimiento quedó en "Prueba"/"Testing", Google mata
el refresh token a los 7 días y la automatización se corta sin avisar. Hay que
publicarla. El README lo explica paso a paso.

Solo biblioteca estándar.
"""
import http.server, json, os, secrets, ssl, sys, threading, urllib.parse, urllib.request, webbrowser

AYUDA_SSL = '''SSL: tu Python no encuentra los certificados raíz.

Pasa con el Python descargado de python.org en macOS: trae su propio paquete
de certificados pero no lo instala. Corré esto una vez y listo:

    /Applications/Python\ 3.X/Install\ Certificates.command

(reemplazá 3.X por tu versión; también está en Finder -> Aplicaciones ->
Python 3.X -> Install Certificates.command)

Después volvé a correr este script.'''


def es_certificado(e):
    """¿El error es 'no encuentro los certificados raíz'?"""
    return isinstance(getattr(e, 'reason', None), ssl.SSLCertVerificationError)

AUTOR = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN = 'https://oauth2.googleapis.com/token'
PUERTO = 8731
REDIR = f'http://localhost:{PUERTO}/'
ALCANCES = [
    'https://www.googleapis.com/auth/yt-analytics.readonly',          # vistas, subs, CTR
    'https://www.googleapis.com/auth/yt-analytics-monetary.readonly',  # ingresos
    'https://www.googleapis.com/auth/youtube.readonly',                # catálogo y duraciones
]


class Recibe(http.server.BaseHTTPRequestHandler):
    """Se queda con el ?code= que Google devuelve al redirigir."""
    codigo = estado = None

    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        Recibe.codigo = (q.get('code') or [None])[0]
        Recibe.estado = (q.get('state') or [None])[0]
        ok = Recibe.codigo is not None
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(
            ('<h2>Listo, ya podés cerrar esta pestaña.</h2>' if ok else
             '<h2>No llegó el código. Volvé a la terminal.</h2>').encode())

    def log_message(self, *a):
        pass        # sin ruido en la terminal


def pedir(url, datos):
    req = urllib.request.Request(url, urllib.parse.urlencode(datos).encode(),
                                 {'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f'Google respondió {e.code}: {e.read().decode()[:400]}')
    except urllib.error.URLError as e:
        if es_certificado(e):
            sys.exit('\n' + AYUDA_SSL)
        sys.exit(f'No se pudo conectar con Google: {e.reason}')


def preguntar(etiqueta, pinta, ejemplo):
    """Pregunta hasta que la respuesta tenga forma de lo que se pidió.

    Si el script quedó esperando y encima le pegan comandos de la terminal, se
    los come como respuesta y arma una URL con basura. Mejor rechazarlo acá.
    """
    for _ in range(5):
        try:
            v = input(f'{etiqueta}: ').strip().strip('"\'')
        except EOFError:
            sys.exit('\nNo llegó nada por consola.')
        if pinta(v):
            return v
        print(f'  Eso no parece un {etiqueta.lower()}. Se espera algo como {ejemplo}.')
        print('  (si pegaste un comando por error, pegá solo el valor)\n')
    sys.exit('Demasiados intentos.')


def main():
    cid = os.environ.get('GOOGLE_CLIENT_ID') or preguntar(
        'Client ID', lambda v: v.endswith('.apps.googleusercontent.com'),
        '1234-abcd.apps.googleusercontent.com')
    sec = os.environ.get('GOOGLE_CLIENT_SECRET') or preguntar(
        'Client secret', lambda v: len(v) > 8 and ' ' not in v, 'GOCSPX-...')

    estado = secrets.token_urlsafe(16)
    url = AUTOR + '?' + urllib.parse.urlencode({
        'client_id': cid,
        'redirect_uri': REDIR,
        'response_type': 'code',
        'scope': ' '.join(ALCANCES),
        'access_type': 'offline',       # sin esto no hay refresh token
        # 'consent' solo fuerza volver a aceptar los permisos: con la sesión ya
        # abierta Google saltea la elección de cuenta y siempre toma la misma.
        # 'select_account' obliga a mostrar el selector, que es donde aparecen
        # las cuentas de marca.
        'prompt': 'select_account consent',
        'state': estado,
    })

    srv = http.server.HTTPServer(('localhost', PUERTO), Recibe)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    print(f'\nAbriendo el navegador. Si no se abre solo, entrá acá:\n\n{url}\n')
    try:
        webbrowser.open(url)
    except Exception:
        pass
    srv.socket.settimeout(300)
    while Recibe.codigo is None and threading.active_count() > 1:
        threading.Event().wait(.4)
    if Recibe.codigo is None:
        sys.exit('No llegó el código de autorización.')
    if Recibe.estado != estado:
        sys.exit('El "state" no coincide: cortá acá y volvé a empezar.')

    r = pedir(TOKEN, {'code': Recibe.codigo, 'client_id': cid, 'client_secret': sec,
                      'redirect_uri': REDIR, 'grant_type': 'authorization_code'})
    rt = r.get('refresh_token')
    if not rt:
        sys.exit('Google no devolvió refresh_token. Revisá access_type=offline '
                 'y prompt=consent, y que la app no esté en modo Prueba.')

    print('\n' + '=' * 62)
    print('Guardá estos tres valores como secrets del repo:\n')
    print(f'  YT_CLIENT_ID      {cid}')
    print(f'  YT_CLIENT_SECRET  {sec}')
    print(f'  YT_REFRESH_TOKEN  {rt}')
    print('=' * 62)
    print('\nSettings -> Secrets and variables -> Actions -> New repository secret')
    print('No los pegues en un archivo del repo: es público.\n')


if __name__ == '__main__':
    main()
