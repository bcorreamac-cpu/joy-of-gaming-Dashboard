"""Inserta data/analytics.json en scripts/dashboard_template.html -> dashboard.html"""
from pathlib import Path
root = Path(__file__).resolve().parent.parent
body = (root/'scripts/dashboard_template.html').read_text().replace(
    '__DATA__', (root/'data/analytics.json').read_text())
head, rest = body.split('</style>', 1)
(root/'dashboard.html').write_text(
    '<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    + head + '</style>\n</head>\n<body>\n' + rest + '\n</body>\n</html>\n')
print('dashboard.html', (root/'dashboard.html').stat().st_size, 'bytes')
