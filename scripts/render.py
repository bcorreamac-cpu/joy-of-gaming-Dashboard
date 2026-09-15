"""Inserta data/data.json en scripts/template.html y genera index.html."""
from pathlib import Path
root = Path(__file__).resolve().parent.parent
body = (root/'scripts/template.html').read_text().replace('__DATA__', (root/'data/data.json').read_text())
head, rest = body.split('</style>', 1)
(root/'index.html').write_text('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
  '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
  + head + '</style>\n</head>\n<body>\n' + rest + '\n</body>\n</html>\n')
