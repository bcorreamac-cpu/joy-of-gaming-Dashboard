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

**Tiene que ser desde MODO AVANZADO**, el botón de arriba a la derecha. La vista
simple exporta solo las columnas que están en pantalla, y ahí no figuran las
impresiones: el archivo baja igual, con vistas y tiempo de reproducción, o sea
justo lo que el API ya trae solo. Si el encabezado no dice "Impresiones", ese
export no sirve para nada acá.

Ya en Modo avanzado, agregá las columnas que faltan: el **+** a la derecha de
los encabezados de la tabla → **Impresiones** y **Porcentaje de clics de las
impresiones**.

### Qué trae el zip de Studio

Adentro vienen varios CSV y solo uno sirve:

| Archivo | Qué es |
|---------|--------|
| `Datos de la tabla.csv` | la tabla. **Es el que importa**, y viene **cortado en 500 filas** |
| `Totales.csv` | la serie del gráfico: todas las fechas, pero una métrica sola, sin CTR |
| `Datos del gráfico.csv` | un cruce fecha × video, inservible acá |

Studio corta las tablas largas sin avisar: 995 días volvieron 500. Por eso las
dos descargas van armadas para no acercarse a esa raya. No hay que abrir ni
tocar nada: el cargador los lee todos y se queda con el que sirve.

### Las dos descargas

**1 · Pestaña Fecha** — período **los últimos 15 días**.

No el rango completo. Un día cerrado no cambia nunca, así que los que ya están
en el histórico están bien para siempre; solo hacen falta los nuevos. Quince
días son quince filas, ni cerca del corte, y dejan margen por si alguna semana
te la salteás.

**2 · Pestaña Contenido** — período **1 de enero de 2024 → hoy**, y **ordená la
tabla por "Tiempo de publicación del video", los más nuevos primero**.

Acá sí va el rango completo, porque un video acumula impresiones para siempre y
el histórico guarda ese acumulado. El orden es lo que salva las 500 filas: los
videos del panel son unos 290, así que ordenados por fecha de publicación entran
todos antes del corte. Sin ordenar, el export se llena de videos de 2017 —pasó,
282 de las 500 filas— y se saltea los nuevos, que son los que interesan.

En cada una, el botón **Descargar** → **Valores separados por comas (.csv)**.
Bajan dos `.zip` a `~/Downloads`.

> **No los abras ni los toques.** El script los lee tal cual, zip incluido, y
> saca de adentro el archivo que corresponde.

Si el botón de descargar no aparece, andá al **Plan B** del final.

### Si preferís que lo haga la extensión de Claude

Apretar botones la extensión lo hace bien; lo que no conviene es pedirle que lea
la tabla (ver Plan B). Abrí Studio en Estadísticas y pegale esto:

> Estás en YouTube Studio, canal **Joy of Gaming**, en Estadísticas → **MODO
> AVANZADO**. Si no estás en Modo avanzado, entrá: la vista simple no exporta
> impresiones y el archivo no sirve.
>
> Necesito dos descargas. Hacelas en orden y contame qué ves en cada paso.
>
> **Paso 1 · Las columnas.** En el selector de **Métricas** (el **+** al final
> de la fila de encabezados de la tabla), asegurate de que estén activadas:
>
> - **Impresiones de miniaturas** (puede aparecer como "Impresiones" o
>   "Impresiones de la miniatura")
> - **Tasa de clics de las miniaturas (%)** (o "Porcentaje de clics de las
>   impresiones" / "de las miniaturas")
>
> Se desactivan solas al cambiar de desglose, así que revisalo aunque la semana
> pasada estuvieran. Las demás columnas podés dejarlas, no molestan.
>
> **Decime la lista de columnas que quedó, y si esas dos no están, pará acá y
> avisame.** Sin ellas el resto del trabajo se tira.
>
> **Paso 2 · La tabla de días.** Pestaña **Fecha**, período **últimos 15 días**.
> Botón de **descargar** → **Valores separados por comas (.csv)**.
>
> **Paso 3 · La tabla de videos.** Pestaña **Contenido**, período
> **personalizado: del 1 de enero de 2024 a hoy**. Antes de descargar, **ordená
> la tabla por "Tiempo de publicación del video", los más nuevos primero**
> —haciendo clic en el encabezado de esa columna—. Después: descargar → .csv.
>
> El orden importa: Studio corta el export en 500 filas, y sin ordenar se llena
> de videos viejos y se saltea los nuevos.
>
> **Al terminar decime:**
>
> - el nombre de los dos archivos que bajaron
> - las columnas de cada tabla
> - cuántas filas tiene cada una (la de Fecha, unas 15; la de Contenido, 500)
> - por qué columna quedó ordenada la de Contenido
>
> **No leas las tablas fila por fila.** Los archivos ya traen todo; solo
> necesito los encabezados y los conteos.

Lo que devuelve no es un adorno: los conteos y las columnas se cruzan contra lo
que informa `ctr_revisar.py` en el paso 2. Si no coinciden, bajó otra cosa.


---

## 2. Cargarlos

**Primero revisá, después cargá.** `ctr_revisar.py` no escribe nada: abre los
archivos, dice qué trae cada uno y compara contra lo que ya hay. Si falta algo,
te dice exactamente qué período volver a pedir.

```bash
cd ~/Documents/joy-of-gaming-Dashboard
git pull
python3 scripts/ctr_revisar.py ~/Downloads/*.zip
```

Termina en un veredicto. Si dice **Sirve**, te deja escrito el comando para
cargar. Si dice **FALTA**, no cargues: te dice qué pedir de nuevo.

Studio le pone el período al nombre del archivo, así que un export viejo
olvidado en Downloads entra igual que el de hoy: pasó, y sumó todo 2023 sin que
se notara hasta contar las filas. El revisor nombra cada archivo que abre; si
ves alguno que no bajaste recién, sacalo de Downloads y volvé a correrlo.

La salida dice qué archivo está leyendo, cuántos videos y días entraron, **de qué
fecha a qué fecha**, y cuáles no reconoció. Tres cosas que hay que mirar:

- **El rango de días.** Tiene que llegar hasta hace dos o tres días. Los conteos
  solos no delatan un período equivocado: un día de más se ve igual que uno de
  menos.
- **La cobertura del panel.** Dice cuántos de los videos que el panel muestra
  quedaron con impresiones. Ese número, no la cantidad de filas del export, es
  el que dice si la descarga sirvió.
- **El aviso de 500 filas.** Si aparece, el export está cortado y hay que
  rehacerlo más chico.

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

Sirve solo si el botón de descargar no está. Acá la extensión no aprieta
botones sino que **lee la tabla**, y eso es otra cosa: depende de que cargue
bien trescientas filas con scroll. Usalo como último recurso. Mismo período: **rango completo**.

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
