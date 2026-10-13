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

Requiere **Python 3.10 o superior**. No usa bibliotecas externas, así que no hay nada
que instalar:

```bash
git clone https://github.com/Camionerou/tp2-saldivia.git
cd tp2-saldivia
python3 --version   # 3.10 o superior
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

82 pruebas: el caso normal con resultados exactos, cada punto de ruptura (entradas
inválidas y casos límite), propiedades que el resultado tiene que cumplir siempre
(conservación de filas y unidades, equivalencia CSV/JSON, reproducibilidad, rangos y
orden) y un test que verifica que cada punto documentado tenga su prueba.

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
82,0002-00001103,aviso,remito,0002-00001103,"remito reutilizado: ya se usó en la fila 3 (2026-01-09, Proveedor 01)"
```

## Organización del código

```
tp2-saldivia/
├── README.md
├── requirements.txt          sin dependencias externas
├── .gitignore
├── src/
│   ├── main.py               línea de comandos: argumentos, pantalla y códigos de salida
│   ├── fuentes.py            FuenteDatos (abstracta), FuenteCSV y FuenteJSON
│   ├── validacion.py         limpieza y validación de cada campo; expresiones regulares
│   ├── modelos.py            Devolucion, ResumenProveedor y RegistroLimpieza
│   ├── pipeline.py           duplicados, fecha de corte, umbral, ranking y salidas
│   └── generar_datos.py      genera el extracto simulado
├── tests/                    pruebas con unittest
├── data/                     extracto en CSV y JSON, y su README
├── docs/
│   └── puntos_de_ruptura.md  qué puede fallar, cómo se defiende y con qué test
└── outputs/                  se genera al ejecutar; no se versiona
```

El flujo es `leer → validar → limpiar → analizar → comunicar`:

1. `fuente_para(ruta)` elige `FuenteCSV` o `FuenteJSON`, y `cargar()` devuelve filas
   crudas con las columnas normalizadas.
2. `validar_fila` convierte cada fila en una `Devolucion` o la rechaza, anotando el motivo.
3. `quitar_duplicados`, `avisar_remitos_reutilizados` y `filtrar_por_corte` terminan la limpieza.
4. `armar_ranking` agrupa las abiertas por proveedor en `ResumenProveedor` y las ordena.
5. `main.py` muestra el resultado y `guardar_salidas` lo escribe en `outputs/`.

## Decisiones de diseño

- **`FuenteDatos` y sus dos implementaciones.** Lo que es igual para los dos formatos
  (verificar que el archivo exista, decodificarlo, revisar columnas, detectar que esté
  vacío) está una sola vez en la clase base. Cada subclase solo implementa
  `_interpretar()`, que es lo que de verdad cambia entre CSV y JSON. El resto de la
  aplicación usa `cargar()` sin saber de qué formato viene; por eso el mismo extracto
  da exactamente el mismo resultado en los dos.
- **`Devolucion`** es inmutable (`frozen=True`) y valida sus propios valores al
  construirse. Es una segunda barrera: aunque una devolución se cree sin pasar por la
  validación, no puede existir una con cantidad 0 o estado desconocido. Sus métodos
  (`esta_abierta`, `dias_abierta`, `clave`) son las preguntas que el análisis le hace.
- **`ResumenProveedor`** acumula las devoluciones abiertas de un proveedor y define el
  criterio de orden del ranking en un solo lugar (`orden()`).
- **`RegistroLimpieza`** concentra todo lo que la limpieza hace, para que ninguna fila
  desaparezca sin rastro.
- **Expresiones regulares** (`src/validacion.py`):
  - `\d{4}-\d{8}` valida el número de remito (punto de venta y número).
  - `(\d{4})-(\d{2})-(\d{2})` y `(\d{2})/(\d{2})/(\d{4})` reconocen las fechas en
    formato ISO y argentino. Como una regex no puede saber si el 30 de febrero existe,
    sus grupos se pasan a `datetime.date()`, que sí lo comprueba.
  - `\d{1,3}(\.\d{3})+` detecta cantidades con separador de miles (`1.000`), que se
    rechazan por ambiguas.

  Todas se aplican con `fullmatch`, para que validen el valor completo y no solo una parte.

## Decisiones de limpieza

El criterio general: **si el archivo completo no es confiable, la aplicación se detiene;
si una fila no sirve, se rechaza y se registra; si un valor se puede corregir sin
adivinar, se corrige y se registra.** Los datos que faltan pero no intervienen en la
pregunta (motivo, artículo, dato de stock) no hacen perder la fila.

Las más importantes:

| Situación | Decisión |
|---|---|
| Fecha `2026-02-30`, cantidad `"dos"`, `0` o `"1.000"`, estado desconocido, proveedor vacío, remito mal formado | Se rechaza la fila |
| Estado `" Abierta "`, fecha `07/03/2026`, espacios de más | Se corrige y se registra |
| Motivo vacío, dato de stock vacío | Se conserva la fila con un aviso |
| Renglón idéntico repetido | Se conserva el primero |
| Mismo número de remito con otros datos | **Se conservan los dos**: un remito puede tener varios renglones y la numeración se reutiliza |
| Más del 50 % de filas rechazadas | Se detiene: el problema es el archivo |

El detalle completo (46 puntos de ruptura con su justificación y su test) está en
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
- Los nombres de proveedor que solo difieren en mayúsculas no se unifican (se avisa),
  porque decidir si son la misma empresa le corresponde a Compras.
- Las fechas con barra se interpretan siempre como día/mes/año.
