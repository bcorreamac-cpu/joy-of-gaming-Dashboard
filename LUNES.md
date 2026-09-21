# Lunes

Tres minutos. Dos cosas: pegarle el prompt a la extensión de Claude en Chrome, y
correr tres comandos.

El detalle de por qué cada cosa es como es está en `PROMPT_CTR.md`. Acá solo
está lo que hay que hacer.

---

## 1 · Abrí Studio

<https://studio.youtube.com> con la cuenta de **Joy of Gaming** →
**Estadísticas** → botón **MODO AVANZADO** (arriba a la derecha).

## 2 · Pegale esto a la extensión

```
Estás en YouTube Studio, canal Joy of Gaming, en Estadísticas → MODO AVANZADO.
Si no estás en Modo avanzado, entrá: la vista simple no exporta impresiones y el
archivo no sirve.

Necesito dos descargas. Hacelas en orden y contame qué ves en cada paso.

PASO 1 · LAS COLUMNAS.
En el selector de Métricas (el + al final de la fila de encabezados de la
tabla), asegurate de que estén activadas:

  - Impresiones de miniaturas
    (puede aparecer como "Impresiones" o "Impresiones de la miniatura")
  - Tasa de clics de las miniaturas (%)
    (o "Porcentaje de clics de las impresiones" / "de las miniaturas")

Se desactivan solas al cambiar de desglose, así que revisalo aunque la semana
pasada estuvieran. Las demás columnas podés dejarlas, no molestan.

Decime la lista de columnas que quedó, y si esas dos no están, pará acá y
avisame. Sin ellas el resto del trabajo se tira.

PASO 2 · LA TABLA DE DÍAS.
Pestaña Fecha, período últimos 15 días. Botón de descargar → Valores separados
por comas (.csv).

PASO 3 · LA TABLA DE VIDEOS.
Pestaña Contenido, período personalizado: del 1 de enero de 2024 a hoy. Antes de
descargar, ordená la tabla por "Tiempo de publicación del video", los más nuevos
primero, haciendo clic en el encabezado de esa columna. Después: descargar →
.csv.

El orden importa: Studio corta el export en 500 filas, y sin ordenar se llena de
videos viejos y se saltea los nuevos.

AL TERMINAR DECIME:
  - el nombre de los dos archivos que bajaron
  - las columnas de cada tabla
  - cuántas filas tiene cada una (la de Fecha, unas 15; la de Contenido, 500)
  - por qué columna quedó ordenada la de Contenido

No leas las tablas fila por fila. Los archivos ya traen todo; solo necesito los
encabezados y los conteos.
```

## 3 · Revisá

```bash
cd ~/Documents/joy-of-gaming-Dashboard
git pull
python3 scripts/ctr_revisar.py ~/Downloads/*.zip
```

Tiene que decir **`COMPLETA: no falta ningún día`**.

Si dice que falta algo, te nombra el período a pedir de nuevo: volvé al paso 2
con ese período y repetí.

## 4 · Cargá

El revisor termina dejándote escrito el comando. **Copialo y corrélo** — ese es
el que escribe; el del paso 3 no toca nada.

```bash
python3 scripts/ctr_actualizar.py "…lo que te dejó escrito…"
```

## 5 · Publicá

```bash
git add data/historico && git commit -m "CTR" && git push
```

Dos minutos después el panel está al día:
<https://bcorreamac-cpu.github.io/joy-of-gaming-Dashboard/>

Si el push se rechaza —el bot publicó mientras tanto—:

```bash
git pull --rebase && git push
```

---

## Si alguna semana no lo hacés

No se rompe nada. El resto del panel —vistas, suscriptores, tiempo de
reproducción, ingresos, RPM— se actualiza solo todos los lunes por su cuenta.
Lo único que queda atrasado es el CTR, y la próxima vez se pone al día solo:
los quince días del paso 2 dejan margen justamente para eso.
