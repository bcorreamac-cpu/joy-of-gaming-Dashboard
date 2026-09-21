# Prompt semanal para sacar el CTR

El API de YouTube no entrega impresiones ni CTR, así que esa parte se junta a
mano una vez por semana con la extensión de Claude en Chrome. Todo lo demás del
panel se actualiza solo los lunes.

Toma unos cinco minutos.

---

## 1. Abrí YouTube Studio

Entrá con la cuenta de **Joy of Gaming** a:

```
https://studio.youtube.com
```

Menú izquierdo → **Estadísticas** → pestaña **Contenido**.

Arriba a la derecha, el período tiene que ser **el rango completo**:
**Personalizado → desde 2024-01-01 hasta hoy**. Si hay una opción tipo
*Máximo*, *Todo el tiempo* o *Desde la publicación*, también sirve.

> **Esto no es un detalle.** El histórico guarda el acumulado de cada video
> desde que salió. Si el export sale con "últimos 28 días", las impresiones
> vienen mucho más chicas y pisarían años de datos con una ventana de un mes.
> El script lo detecta y frena, pero es tiempo perdido.

---

## 2. Abrí la extensión de Claude y pegá este prompt

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
> - Si la tabla tiene más filas de las que podés leer, decime cuántas leíste.

---

## 3. Para el CTR del canal por día (opcional)

En la misma pantalla, pestaña **Fecha** en vez de Contenido. Acá sí conviene un
período corto —la última semana o el último mes—, porque cada fila es un día y
un día no acumula: su cifra ya no cambia. Mismo prompt, cambiando la primera
columna:

> Igual que antes, pero es la tabla por fecha. La primera columna dice `dia`
> literal, y la clave es la fecha en formato `YYYY-MM-DD`:
>
> ```
> tipo,clave,impresiones,ctr
> dia,2026-09-20,242829,6.92
> ```

---

## 4. Guardá lo que te devolvió

Copiá el CSV a un archivo, por ejemplo `~/Downloads/ctr.csv`.

---

## 5. Cargalo

```bash
cd ~/Documents/joy-of-gaming-Dashboard
git pull
python3 scripts/ctr_actualizar.py ~/Downloads/ctr.csv
```

Te va a decir cuántos entraron, cuántos se actualizaron y cuáles no pudo
identificar. Después:

```bash
git add data/historico
git commit -m "CTR semanal"
git push
```

Y en GitHub, pestaña **Actions** → **Actualizar el panel** → **Run workflow**.

---

## Lo que el script tolera solo

No hace falta que el CSV venga perfecto:

- **Título o ID.** Acepta el título tal cual aparece y lo resuelve contra el
  catálogo. Si preferís el ID de 11 caracteres, también sirve.
- **Miles con punto o con coma.** `1.234.567` y `1,234,567` se leen igual.
- **Decimal con coma.** `5,80` se entiende, aunque el prompt pida punto.
- **Filas repetidas o ya cargadas.** Se pisan sin duplicar nada.
- **Basura.** Fechas con formato raro, CTR imposibles y títulos que no existen
  en el catálogo se descartan, y el script dice cuáles.
- **Videos anteriores a 2024.** El panel arranca en 2024, así que los más viejos
  no están en el catálogo y quedan afuera. Es normal ver varias decenas.
- **El período equivocado.** Si un video trae menos de la mitad de las
  impresiones guardadas, no se pisa: el script avisa y lo deja como estaba.

Es incremental: lo que mandes se suma a lo que ya había. Podés cargar diez
videos una semana y el catálogo entero la siguiente.

---

## Por qué no se puede automatizar

Probado contra el API de YouTube Analytics con permisos de dueño del canal, en
tres formas distintas (por día, sin dimensión y por video): responde siempre
`The query is not supported`. Las métricas `videoThumbnailImpressions` y
`videoThumbnailImpressionsClickRate` figuran en la documentación desde enero de
2026, pero no funcionan.

Si algún día empiezan a funcionar, el descargador ya las pide: las va a tomar
solas y este proceso deja de hacer falta.
