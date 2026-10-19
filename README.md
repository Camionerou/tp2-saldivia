# Devoluciones abiertas a proveedores

Trabajo Práctico 2: Programación Orientada a Datos (UCA, 2026).
Autor: **Enzo Saldivia**.

Una aplicación de línea de comandos que lee el extracto de devoluciones a proveedores
de una fábrica, lo valida y lo limpia, y arma el ranking de proveedores con
devoluciones pendientes. Está pensada para no romperse en silencio: cada cosa que puede
salir mal está documentada, defendida y probada en
[`docs/puntos_de_ruptura.md`](docs/puntos_de_ruptura.md).

## Problema

Cuando el material que entrega un proveedor no sirve (no funciona, llega roto o no
corresponde a lo pedido), Calidad lo devuelve con un remito de devolución. La
devolución queda **abierta** hasta que el proveedor repone el material o emite una
nota de crédito.

Hoy nadie sigue esas devoluciones. Muchas quedan abiertas durante meses, la numeración
de los remitos se repite y no hay una forma rápida de saber a quién reclamarle. Es
material que la fábrica ya pagó o va a pagar y no recibió en condiciones.

## Usuarios

- **Compras**: necesita saber a qué proveedor reclamarle primero.
- **Administración**: necesita saber a qué proveedor convendría frenarle un pago
  mientras tenga devoluciones pendientes.

## Pregunta

> **¿Qué proveedores tienen más devoluciones abiertas y hace cuántos días que esperan?**

## Algoritmo

```
 archivo .csv / .json
        │
        ▼
 1. LEER ──────────── FuenteCSV / FuenteJSON  ──► filas crudas      (fuentes.py)
        │
        ▼
 2. VALIDAR ───────── campo por campo         ──► filas válidas     (validacion.py)
        │                                         + rechazos y correcciones al registro
        ▼
 3. LIMPIAR ───────── duplicados, avisos,     ──► filas limpias     (pipeline.py)
        │             filtro por fecha de corte
        ▼
 4. ANALIZAR ──────── agrupar por proveedor   ──► ranking ordenado  (pipeline.py, modelos.py)
        │
        ▼
 5. COMUNICAR ─────── pantalla + 2 archivos CSV                     (main.py, pipeline.py)
```

## Resultado y cómo leerlo

Un ranking de proveedores con devoluciones abiertas a una fecha de corte:

| Columna | Significado |
|---|---|
| `renglones_abiertos` | Cuántos renglones de devolución siguen sin resolverse |
| `unidades` | Cuántas unidades suman esos renglones |
| `devolucion_mas_vieja` | Fecha de la devolución abierta más antigua |
| `dias_abierta` | Días entre esa devolución y la fecha de corte |

El primero del ranking es el que tiene más renglones pendientes; si hay empate, el que
espera hace más tiempo. Se muestra en pantalla y se guarda en `outputs/ranking.csv`.
Junto con el ranking se guarda `outputs/registro_limpieza.csv`, con cada fila
rechazada, corregida, duplicada o con aviso, y el motivo.

Ninguna fila desaparece sin explicación: válidas + rechazadas + duplicadas siempre
da las filas leídas (lo verifica el test P01). Si el ranking no le cierra al usuario,
el registro muestra exactamente qué se descartó y por qué.

## Alcance

**Incluye:** lectura de un extracto en CSV o JSON, validación del esquema y de cada
campo, limpieza con registro, ranking por proveedor a una fecha de corte y pruebas
automáticas.

**Queda fuera:** conexión con el sistema real de la empresa, montos, notas de crédito,
pagos, alertas automáticas e interfaz gráfica.

## Datos

Extracto **simulado** de 83 renglones, en CSV y JSON equivalentes: `data/devoluciones.csv`
y `data/devoluciones.json`. Lo genera `src/generar_datos.py` con semilla fija. El
extracto real no se puede publicar porque contiene nombres de proveedores y de
personas; la simulación conserva su estructura, sus proporciones y sus errores de carga
típicos.

- **Unidad de análisis:** un renglón de un remito de devolución (un artículo devuelto a
  un proveedor).
- **Variables:** `remito`, `fecha`, `proveedor`, `articulo`, `cantidad`, `motivo`,
  `estado`, `descuenta_stock`.
- **Licencia:** datos ficticios generados para este trabajo; uso libre con fines académicos.

Procedencia, variables, errores incluidos y limitaciones en [`data/README.md`](data/README.md).

## Instalación

Requiere **Python 3.10 o superior** y nada más: no usa bibliotecas externas.

```bash
git clone https://github.com/Camionerou/tp2-saldivia.git && cd tp2-saldivia
```

## Uso

Desde la raíz del proyecto:

```bash
python3 src/main.py data/devoluciones.csv
python3 src/main.py data/devoluciones.json                    # mismo resultado
python3 src/main.py data/devoluciones.csv --corte 2026-06-30  # otra fecha de corte
python3 src/main.py data/devoluciones.csv --salida otra_carpeta
python3 src/generar_datos.py                                  # regenera los datos (idénticos)
```

Si no se indica `--corte`, se usa la fecha más reciente del extracto. Así el resultado
depende solo de la entrada y no del día en que se ejecuta.

| Código de salida | Significado |
|---|---|
| `0` | Terminó bien (aunque haya filas rechazadas: están en el registro) |
| `1` | El archivo de entrada no se puede usar, o no se pudieron escribir las salidas |
| `2` | Argumentos incorrectos (por ejemplo, una fecha de corte inválida) |

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

| Qué se prueba | Dónde | Ejemplos |
|---|---|---|
| Caso normal, con resultados exactos | `test_pipeline.py`, `test_validacion.py`, `test_main.py` | 83 leídas, 75 válidas, 7 rechazadas; primer puesto del ranking |
| Entradas inválidas y casos límite | `test_fuentes.py`, `test_validacion.py`, `test_pipeline.py` | archivo inexistente, JSON mal formado, fecha `2026-02-30`, cantidad `"1.000"`, umbral justo en el 50 % |
| Propiedades del resultado | `test_propiedades.py` | conservación de filas (P01) y unidades (P02), equivalencia CSV/JSON (P03), reproducibilidad (P04), rangos (P05), orden (P06) |
| Trazabilidad | `test_trazabilidad.py` | cada punto de ruptura documentado tiene su test (T01) |

## Ejemplo de resultado

```
$ python3 src/main.py data/devoluciones.csv
Filas leídas: 83 | válidas: 75 | rechazadas: 7 | duplicadas: 1 | corregidas: 5
Fecha de corte: 2026-09-30

  #  Proveedor              Renglones  Unidades    Más vieja   Días
  1  Proveedor 01                  17       179   2026-01-09    264
  2  Proveedor 02                  10       152   2026-01-07    266
  3  Proveedor 04                   6        69   2026-01-05    268
  4  Proveedor 06                   6        65   2026-02-10    232
  5  Proveedor 09                   4        44   2026-02-15    227
  ...
 15  Proveedor 18                   1         8   2026-09-26      4

Resultados guardados en outputs/ranking.csv y outputs/registro_limpieza.csv
```

Extracto de `outputs/registro_limpieza.csv`:

```
fila,remito,accion,campo,valor_original,motivo
5,0002-00001105,corregida,estado, Abierta ,estado ' Abierta ' normalizado a 'abierta'
12,0002-00001110,rechazada,fecha,2026-02-30,la fecha 2026-02-30 no existe en el calendario
35,0002-00001132,duplicada,fila,,renglón idéntico al de la fila 34
```

## Organización del código

```
tp2-saldivia/
├── README.md
├── requirements.txt          sin dependencias externas
├── .gitignore
├── src/
│   ├── fuentes.py            1. leer: FuenteDatos (abstracta), FuenteCSV y FuenteJSON
│   ├── validacion.py         2. validar cada campo; expresiones regulares
│   ├── pipeline.py           3-4. duplicados, fecha de corte, umbral, ranking y salidas
│   ├── modelos.py            Devolucion, ResumenProveedor y RegistroLimpieza
│   ├── main.py               5. comunicar: línea de comandos, pantalla, códigos de salida
│   └── generar_datos.py      genera el extracto simulado
├── tests/                    pruebas con unittest
├── data/                     extracto en CSV y JSON, y su README
├── docs/
│   └── puntos_de_ruptura.md  qué puede fallar, cómo se defiende y con qué test
└── outputs/                  se genera al ejecutar; no se versiona
```

Los números marcan la etapa del flujo `leer → validar → limpiar → analizar → comunicar`.

## Decisiones de diseño

- **`FuenteDatos` y sus dos implementaciones.** Lo que es igual para los dos formatos
  (verificar que el archivo exista, decodificarlo, revisar columnas, detectar que esté
  vacío) está una sola vez en la clase base; cada subclase solo implementa
  `_interpretar()`. El resto de la aplicación usa `cargar()` sin saber de qué formato
  viene, y por eso el mismo extracto da exactamente el mismo resultado en los dos.
- **`Devolucion`** es un renglón ya validado e inmutable (`frozen=True`). Sus métodos
  (`esta_abierta`, `dias_abierta`, `clave`) son las preguntas que el análisis le hace.
- **`ResumenProveedor`** acumula las abiertas de un proveedor y define el orden del
  ranking en un solo lugar. **`RegistroLimpieza`** junta todo lo que hace la limpieza,
  para que ninguna fila desaparezca sin rastro.
- **Expresiones regulares** (`src/validacion.py`):
  - `\d{4}-\d{8}` valida el número de remito (punto de venta y número).
  - `(\d{4})-(\d{2})-(\d{2})` y `(\d{2})/(\d{2})/(\d{4})` reconocen las fechas en
    formato ISO y argentino. Como una regex no puede saber si el 30 de febrero existe,
    sus grupos se pasan a `datetime.date()`, que sí lo comprueba.

  Todas se aplican con `fullmatch`, para que validen el valor completo y no solo una parte.

## Decisiones de limpieza

Criterio general: **si el archivo completo no es confiable, la aplicación se detiene; si
una fila no sirve, se rechaza y se registra; si un valor se puede corregir sin adivinar,
se corrige y se registra.**

- **Se rechaza la fila:** fecha inexistente (`2026-02-30`), cantidad `"dos"`, `0` o
  `"1.000"` (¿mil o uno?), estado desconocido, proveedor vacío, remito mal formado.
- **Se corrige:** estado `" Abierta "`, fecha `07/03/2026`, espacios de más.
- **Se conserva con aviso:** motivo, artículo o dato de stock vacíos; no intervienen en la pregunta.
- **Duplicados:** de un renglón idéntico se conserva el primero. El mismo número de
  remito con otros datos **no** es duplicado: un remito tiene varios renglones y la
  numeración se reutiliza.
- **Más del 50 % rechazado:** se detiene, porque el problema es el archivo.

Los 45 puntos de ruptura, con su justificación y su test, están en
[`docs/puntos_de_ruptura.md`](docs/puntos_de_ruptura.md).

## Interpretación y limitaciones

- Con el extracto simulado, dos proveedores concentran el 44 % de los renglones
  abiertos (27 de 62) y los tres primeros del ranking tienen devoluciones de enero sin
  resolver: más de 260 días. Esa es la situación que la aplicación busca hacer visible.
  **Los datos son ficticios**: el resultado muestra que el flujo funciona, no describe
  a proveedores reales.
- El ranking cuenta renglones y unidades, no dinero: un proveedor con pocas
  devoluciones caras puede quedar abajo. El extracto no tiene montos.
- "Abierta" significa abierta en el sistema. Si alguien resolvió una devolución pero no
  la cerró, la aplicación no puede saberlo.
- Los nombres de proveedor que solo difieren en mayúsculas no se unifican,
  porque decidir si son la misma empresa le corresponde a Compras.
- Las fechas con barra se interpretan siempre como día/mes/año.
