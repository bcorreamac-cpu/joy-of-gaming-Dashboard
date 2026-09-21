# La rutina del lunes

Todo el panel se actualiza solo, menos **impresiones y CTR**: el API de YouTube
no los entrega. Eso se baja a mano una vez por semana, y toma unos tres minutos.

**La regla que importa:** la tabla de **videos va completa todos los lunes**, con
el rango entero. No es capricho. Un día cerrado ya no cambia —el 14 de
septiembre va a tener siempre las mismas impresiones—, pero un video **acumula
para siempre**: los 288 del panel suman impresiones nuevas cada semana, incluso
los de 2024. Si solo traés lo nuevo, los viejos quedan clavados en la cifra de
la semana pasada y el panel se va despegando de Studio.

---

## 1. Bajar los dos archivos de Studio

Entrá con la cuenta de **Joy of Gaming** a <https://studio.youtube.com> →
**Estadísticas** (menú izquierdo).

Arriba a la derecha, poné el período en **Personalizado → desde 2024-01-01 hasta
hoy**. Si aparece *Máximo* o *Todo el tiempo*, también sirve.

Después, dos descargas:

| # | Pestaña | Sub-pestaña | Qué trae |
|---|---------|-------------|----------|
| 1 | **Contenido** | **Videos** (no Shorts) | impresiones y CTR de cada video |
| 2 | **Fecha** | — | impresiones y CTR del canal, día por día |

En cada una, el botón **Descargar** (la flecha hacia abajo, arriba a la derecha)
→ **Valores separados por comas (.csv)**. Bajan dos `.zip` a `~/Downloads`.

> **No los abras ni los toques.** El script los lee tal cual, zip incluido, y
> saca de adentro el archivo que corresponde.

Si el botón de descargar no aparece, andá al **Plan B** del final.

---

## 2. Cargarlos

```bash
cd ~/Documents/joy-of-gaming-Dashboard
git pull
python3 scripts/ctr_actualizar.py ~/Downloads/*.zip
```

Te dice cuántos videos y cuántos días entraron, cuántos se actualizaron, y
cuáles no reconoció.

---

## 3. Publicar

```bash
git add data/historico
git commit -m "CTR al $(date +%F)"
git push
```

Y listo: el push dispara la actualización del panel. En un par de minutos
<https://bcorreamac-cpu.github.io/joy-of-gaming-Dashboard/> queda al día.

---

## Lo que pasa solo, sin que hagas nada

- **Lunes 11:00 UTC**: se bajan del API vistas, suscriptores, tiempo de
  reproducción, ingresos, RPM, duración promedio y porcentaje reproducido, del
  canal y de cada video. Se valida, se compara contra lo publicado y se sube.
- **Todos los días**: un chequeo avisa si el permiso de Google caducó.

Por eso el paso manual **solo pide impresiones y CTR**: pedirle vistas a Studio
sería duplicar algo que ya llega bien, y dos fuentes para el mismo número es la
forma más rápida de que el panel deje de cuadrar.

---

## Lo que el script tolera solo

- **El zip de Studio tal cual**, o el CSV de adentro, o una lista a mano.
- **Español o inglés.** Busca las columnas por nombre, no por posición.
- **Miles con punto o con coma**, y decimal con coma: `1.234.567` y `5,80`.
- **Fechas en cualquiera de las tres formas** que usa Studio: `2026-09-14`,
  `Sep 14, 2026`, `14 sept 2026`.
- **Filas repetidas o ya cargadas.** Se pisan sin duplicar nada.
- **Videos anteriores a 2024.** El panel arranca en 2024: los más viejos quedan
  afuera. Es normal ver varias decenas.
- **El período equivocado.** Si un video trae menos de la mitad de las
  impresiones guardadas, no se pisa: avisa y lo deja como estaba. Esa es la red
  que te salva de bajar "últimos 28 días" por error.

---

## Plan B: la extensión de Claude en Chrome

Sirve si el botón de descargar no está. Es menos confiable —depende de que la
extensión lea bien trescientas filas con scroll—, así que usalo solo si hace
falta. Mismo período: **rango completo**.

> Estoy en la pestaña Contenido de YouTube Studio, viendo la tabla de videos.
>
> Extraé de la tabla, para **cada fila visible**, estos tres datos:
>
> - el **título** del video, completo y exacto como aparece
> - las **impresiones** (columna "Impresiones")
> - el **CTR** (columna "Porcentaje de clics de las impresiones" o similar)
>
> Antes de empezar, **hacé scroll hasta el final de la tabla** para que se
> carguen todas las filas: YouTube las va cargando de a poco a medida que bajás.
>
> Devolvémelo como CSV, sin explicaciones ni texto alrededor, con este formato
> exacto:
>
> ```
> tipo,clave,impresiones,ctr
> video,TÍTULO DEL VIDEO,123456,7.15
> ```
>
> Reglas importantes:
> - La primera columna siempre dice `video`, literal.
> - El título va entre comillas dobles si contiene comas.
> - Usá **punto** como separador decimal en el CTR, nunca coma.
> - Las impresiones van sin separador de miles.
> - No inventes filas ni completes datos que no veas. Si una fila no tiene
>   impresiones o CTR, salteala.
> - **Decime cuántas filas leíste en total**, para poder comparar con las que
>   muestra Studio.

Para la tabla por fecha, lo mismo cambiando la primera columna:

> Igual que antes, pero es la tabla por fecha. La primera columna dice `dia`
> literal, y la clave es la fecha en formato `YYYY-MM-DD`:
>
> ```
> tipo,clave,impresiones,ctr
> dia,2026-09-20,242829,6.92
> ```

Guardá lo que devuelva en `~/Downloads/ctr.csv` y seguí desde el paso 2.

---

## Por qué no se puede automatizar

Probado contra el API de YouTube Analytics con permisos de dueño del canal, en
tres formas distintas (por día, sin dimensión y por video): responde siempre
`The query is not supported`. Las métricas `videoThumbnailImpressions` y
`videoThumbnailImpressionsClickRate` figuran en la documentación desde enero de
2026, pero no funcionan.

Si algún día empiezan a funcionar, el descargador ya las pide: las va a tomar
solas y esta rutina deja de hacer falta.
