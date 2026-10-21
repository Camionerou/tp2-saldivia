# Puntos de ruptura y cómo se defiende la aplicación

Este documento enumera todo lo que puede salir mal desde que se lee el extracto de
devoluciones hasta que se escribe el ranking, qué hace la aplicación en cada caso,
**por qué** se eligió esa respuesta y qué prueba lo verifica.

Cada punto tiene un identificador (`R01`, `R02`, ...). El mismo identificador aparece:

- en este documento,
- como comentario junto a la defensa en el código (`# R14`),
- en el test que lo comprueba: en su nombre (`test_R10f_lineas_vacias_antes_del_encabezado`)
  o como primera columna de una tabla de casos (`("R14", limpiar_fecha, "2026-02-30", ...)`).

Así, `grep -rn R14 src tests docs` encuentra la regla, la defensa y la prueba. El test
`T01` verifica que todo identificador de este documento tenga al menos un test y que
no haya tests de puntos que no estén documentados: si alguno de los dos se
desactualiza, la batería de pruebas falla.

---

## 1. Principio general: tres respuestas posibles

Ante cada problema la aplicación responde de una de tres maneras, y siempre de la misma:

| Respuesta | Cuándo se usa | Qué hace | Por qué |
|---|---|---|---|
| **ABORTAR** | El archivo completo no es confiable (no existe, no se puede leer, le falta una columna necesaria). | Termina con un mensaje en castellano que dice qué pasó y cómo arreglarlo, y con código de salida `1`. No escribe el ranking. | Un ranking armado sobre un archivo roto es peor que ningún ranking: Administración podría frenarle un pago al proveedor equivocado. |
| **RECHAZAR FILA** | Una fila no se puede usar para responder la pregunta, pero el resto sí. | Saca la fila del análisis y la anota en el registro de limpieza con su número de fila, el valor problemático y el motivo. Si la fila tiene varios problemas, se anotan todos. | Un renglón mal cargado por Calidad no debería impedirle a Compras ver a quién reclamarle. Pero tampoco puede desaparecer en silencio. |
| **CORREGIR Y AVISAR** | El valor se puede recuperar **sin adivinar** (espacios, mayúsculas, formato de fecha argentino). | Normaliza el valor, sigue y anota la corrección en el registro. | Corregir lo obvio evita rechazos inútiles; dejar registro evita esconder la falla. |

Regla de desempate entre "rechazar" y "corregir": **si para corregir hay que suponer
algo que el dato no dice, se rechaza.** Por ejemplo, completar `0002-1127` como
`0002-00001127` supone que el número está bien y solo faltan ceros, pero puede ser un
error de tipeo de cualquier otro tipo: se rechaza (R11).

Hay una cuarta respuesta para datos que faltan pero **no intervienen en la pregunta**
(motivo, artículo, dato de stock): la fila se **conserva** y se deja un aviso. Rechazarla
haría desaparecer una devolución real del reclamo por un dato que no se usa.

### Contrato de la aplicación

| Situación | Código de salida | Salidas |
|---|---|---|
| Corrida correcta (aunque haya filas rechazadas) | `0` | `outputs/ranking.csv`, `outputs/registro_limpieza.csv` y el ranking en pantalla; con `--grafico`, también `outputs/ranking.png` |
| Error en la entrada (archivo o esquema) o al escribir las salidas | `1` | Ninguna; mensaje por `stderr` |
| Demasiadas filas rechazadas (R34) | `1` | Solo `registro_limpieza.csv`, para poder diagnosticar |
| Error de uso (argumentos de la línea de comandos) | `2` | Ninguna; mensaje de uso |

Una excepción de Python sin capturar (*traceback*) **se considera un bug**, nunca un
comportamiento esperado: todo error previsible tiene su mensaje.

### Registro de limpieza

`outputs/registro_limpieza.csv` tiene una fila por cada evento:

| Columna | Contenido |
|---|---|
| `fila` | Posición de la devolución en el archivo, empezando en 1, sin contar el encabezado ni las líneas vacías. En Excel corresponde a la fila `fila + 1` de la hoja. Se numera igual en CSV y en JSON para que el mismo extracto produzca exactamente el mismo registro (P03). |
| `remito` | Remito de la fila, tal como venía |
| `accion` | `rechazada`, `corregida`, `duplicada` o `aviso` |
| `campo` | Campo afectado |
| `valor_original` | Valor tal como venía |
| `motivo` | Explicación en castellano |

---

## 2. Puntos de ruptura

Faltan R19 y R25 porque se retiraron durante el desarrollo; los demás identificadores
no se renumeraron para que sigan coincidiendo con el historial de Git.

### 2.1 Lectura del archivo (`src/fuentes.py`)

| ID | Qué puede romperse | Ejemplo | Respuesta | Por qué |
|---|---|---|---|---|
| R01 | El archivo no existe o la ruta está mal | `data/devolucion.csv` | ABORTAR: `No se encontró el archivo ...` | Es el error más común al ejecutar; un `FileNotFoundError` con traceback no le sirve a un usuario de Compras. |
| R02 | La ruta es una carpeta | `data/` renombrada `x.csv` | ABORTAR | Mismo motivo que R01. |
| R03 | Extensión no soportada | `devoluciones.xlsx` | ABORTAR: indica que se acepta `.csv` o `.json` y cómo exportar desde Excel. La extensión no distingue mayúsculas. | La fuente (`FuenteCSV` o `FuenteJSON`) se elige por la extensión. Adivinar el formato mirando el contenido agrega complejidad sin beneficio. |
| R04 | Archivo vacío, solo con espacios, solo con encabezado o lista JSON vacía | `[]` | ABORTAR: `El archivo ... no tiene devoluciones.` | Un extracto sin filas casi seguro es una exportación fallida. Mostrar un ranking vacío haría creer que no hay nada que reclamar (distinto de R35). |
| R05 | Codificación distinta de UTF-8 | Excel en Windows guarda en `cp1252` y la `é` no es UTF-8 válido | ABORTAR pidiendo exportar como "CSV UTF-8". | Leer con otra codificación sería adivinar: un byte mal interpretado cambia letras sin avisar. Excel tiene la opción "CSV UTF-8", así que el arreglo es fácil para el usuario. |
| R06 | BOM al inicio del archivo | El encabezado llega como `"﻿remito"` | CORREGIR: se decodifica con `utf-8-sig`, que lo descarta. | Sin esto la app abortaría por "falta la columna remito" en un archivo que está bien. Es un error clásico y difícil de ver. |
| R07 | Separador `;` en lugar de `,` | `remito;fecha;...` | CORREGIR Y AVISAR: se detecta mirando el encabezado (solo `,` o `;`). Una coma dentro de un campo entre comillas no confunde la lectura. | En Argentina la coma es el separador decimal, por eso Excel exporta con `;`. Es el formato que va a tener el extracto real. |
| R08 | JSON mal formado | Sobra una coma | ABORTAR: el mensaje incluye línea y columna del error. | No hay forma segura de recuperar parte de un JSON roto; la posición le permite al usuario encontrarlo. |
| R09 | JSON con estructura distinta | `{"devoluciones": [...]}` o un elemento que es una lista | ABORTAR si la raíz no es una lista. RECHAZAR FILA si un elemento no es un objeto. | La estructura definida es "lista de objetos". Si la raíz está mal es otro tipo de archivo; si un elemento está mal, el resto puede servir. |

### 2.2 Esquema (`src/fuentes.py`)

Columnas obligatorias: `remito`, `fecha`, `proveedor`, `articulo`, `cantidad`, `motivo`, `estado`, `descuenta_stock`.

| ID | Qué puede romperse | Ejemplo | Respuesta | Por qué |
|---|---|---|---|---|
| R10 | Falta una columna obligatoria (en JSON: falta en todos los objetos) | No viene `proveedor` | ABORTAR, listando **todas** las faltantes juntas. | Sin esa columna no se puede responder la pregunta. Listarlas todas evita el ciclo "arreglo una, aparece otra". |
| R10b | Encabezados con mayúsculas o espacios | `" Remito "`, `"CANTIDAD"` | CORREGIR: se pasan a minúscula y se quitan los espacios antes de compararlos. | Es la misma columna; rechazarla sería pedantería. |
| R10c | Columnas de más | Viene `observaciones` | AVISAR y se ignora. | No afecta la pregunta, pero el usuario tiene que saber que esa información no se usa. |
| R10d | Fila con más o menos campos que el encabezado, u objeto JSON al que le falta un campo | Una coma de más en el motivo sin comillas | RECHAZAR FILA | `csv` no se queja: completa o junta lo que sobra, y los valores quedarían corridos de columna (la cantidad podría terminar en el motivo). |
| R10e | Líneas vacías o con solo separadores | `,,,,,,,` o `;;;;;;;` al final de una exportación de Excel | Se IGNORAN y se avisa cuántas fueron. No cuentan como filas. | Excel las agrega al exportar hojas con formato. No son devoluciones; rechazarlas llenaría el registro de ruido. |
| R10f | Líneas vacías **antes** del encabezado | El archivo empieza con una línea en blanco y recién después viene `remito;fecha;...` | Se IGNORAN igual que R10e: el encabezado es la primera línea con contenido, y el separador también se detecta en ella | Sin esto la app tomaba la línea vacía como encabezado y abortaba diciendo que faltaban todas las columnas, en un archivo que estaba bien. Este error se encontró revisando el código y se agregó con su test. |

### 2.3 Campos de cada fila (`src/validacion.py`)

| ID | Campo | Qué puede romperse | Ejemplo | Respuesta | Por qué |
|---|---|---|---|---|---|
| R11 | `remito` | No respeta el formato *punto de venta - número* | `0002-1127`, `A002-00001127` | RECHAZAR FILA | Regex `\d{4}-\d{8}` aplicada con `fullmatch` (la cadena completa, no una parte): 4 dígitos de punto de venta, guion y 8 de número, como los comprobantes argentinos. Completar con ceros sería adivinar. |
| R12 | `remito` | Vacío | `""` o `null` | RECHAZAR FILA | Sin remito no hay forma de reclamar esa devolución. |
| R13 | `fecha` | Formato no reconocido | `15-09-2026`, `2026/09/15`, `2026-9-15` | RECHAZAR FILA | Se aceptan dos formatos, cada uno con su regex: ISO `(\d{4})-(\d{2})-(\d{2})` y argentino `(\d{2})/(\d{2})/(\d{4})`. |
| R13b | `fecha` | Viene en formato argentino | `07/03/2026` | CORREGIR a `2026-03-07` y avisar | La barra se interpreta **siempre** como día/mes/año (convención argentina); nunca se intenta adivinar si es mes/día. |
| R14 | `fecha` | Respeta el formato pero no existe | `2026-02-30`, `31/04/2026`, `2025-02-29` | RECHAZAR FILA | **La regex no alcanza**: `2026-02-30` tiene la forma correcta. Los grupos de la regex se pasan a `datetime.date(...)`, que verifica que el día exista (incluye bisiestos). Es el caso que pide la consigna. |
| R15 | `fecha` | Posterior a la fecha de corte | Devolución del 20/03 con corte al 10/03 | RECHAZAR FILA ("posterior a la fecha de corte") | A la fecha de corte esa devolución todavía no existía; incluirla daría una antigüedad negativa. |
| R16 | `cantidad` | No numérica o vacía | `"dos"`, `""`, `null`, `"1e3"` | RECHAZAR FILA | No se pueden sumar unidades. |
| R17 | `cantidad` | Cero o negativa | `0`, `-3` | RECHAZAR FILA | Una devolución de 0 unidades no existe; una negativa sería una reposición mal cargada. |
| R18 | `cantidad` | Con decimales o separador de miles | `2.5`, `"2,5"`, `"1.000"` | RECHAZAR FILA. Excepción: un número JSON entero escrito como real (`3.0`) se CORRIGE a `3`. | Se devuelven piezas enteras. `"1.000"` es ambiguo (mil con formato argentino, uno con formato inglés), así que no se adivina. `3.0` es un artefacto típico de exportar desde planillas y no hay ambigüedad. |
| R20 | `cantidad` | Booleano en JSON | `true` | RECHAZAR FILA | **Trampa de Python:** `bool` es subclase de `int`; `isinstance(True, int)` da `True` y `True + 1 == 2`. Sin un chequeo explícito, `true` pasaría como una unidad. |
| R21 | `estado` | Espacios o mayúsculas | `" Abierta "`, `"CERRADA"` | CORREGIR y avisar | Es el mismo valor escrito distinto. |
| R22 | `estado` | Valor desconocido | `"anulada"`, `""` | RECHAZAR FILA | Solo existen `abierta` y `cerrada`. Una devolución con otro estado no se puede contar como abierta ni descartar como cerrada sin adivinar. |
| R23 | `proveedor` | Vacío | `""` | RECHAZAR FILA | Sin proveedor la fila no entra en el ranking; es el corazón de la pregunta. |
| R23b | `articulo` | Vacío | `""` | Se CONSERVA la fila y se avisa ("sin artículo") | No interviene en la pregunta; rechazar la fila haría perder una devolución que hay que reclamar. |
| R24 | Campos de texto | Espacios de más | `"Proveedor 01 "`, `"Proveedor   01"` | CORREGIR (se quitan al inicio y al final y se colapsan los repetidos) y avisar | No cambia el significado y evita que un mismo proveedor aparezca dos veces en el ranking. |
| R26 | `motivo` | Vacío | `""` | Se CONSERVA la fila y se avisa ("sin motivo") | El motivo no interviene en la pregunta. Rechazar la fila haría desaparecer una devolución real del reclamo porque Calidad no escribió el motivo. |
| R27 | `descuenta_stock` | Distintas formas de escribir sí/no | `si`, `SI`, `sí`, `true`, `1`, `no`, `false`, `0` | Se interpretan como `True`/`False` sin aviso | Son representaciones del mismo dato según la exportación (el CSV usa `si`/`no`; el JSON, `true`/`false`); avisar cada una llenaría el registro de ruido. |
| R27b | `descuenta_stock` | Vacío o desconocido | `""`, `null`, `"tal vez"` | Se CONSERVA la fila con valor "sin dato" (`None`) y se avisa | Igual que el motivo: no interviene en la pregunta. |
| R28 | Cualquier campo | `null` en JSON | `"motivo": null` | Se trata como texto vacío y se aplica la regla del campo | Unifica los dos formatos: un faltante es un faltante, venga como venga. |

### 2.4 Duplicados (`src/pipeline.py`)

| ID | Qué puede romperse | Ejemplo | Respuesta | Por qué |
|---|---|---|---|---|
| R29 | Renglón cargado dos veces | Dos filas iguales en **todos** los campos (comparados después de limpiar, así `" ABIERTA "` y `abierta` cuentan como iguales) | Se conserva la primera; la segunda se registra como `duplicada` indicando de qué fila es copia | Contarla dos veces inflaría las unidades reclamadas al proveedor. |
| R30 | **Mismo remito en varias filas con datos distintos** | El remito `0002-00001108` tiene tres renglones, uno por artículo | Se CONSERVAN todas, sin aviso | **No se deduplica por número de remito.** Un remito puede tener varios renglones; si se usara el remito como clave se perderían devoluciones reales. |
| R31 | Numeración de remitos reutilizada | El `0002-00001103` aparece en enero para un proveedor y en septiembre para otro | Se CONSERVAN las dos y se AVISA ("remito reutilizado"), indicando dónde se usó primero | Pasa en el sistema real. Se distingue de R30 porque cambia la fecha o el proveedor. Se avisa porque Administración lo necesita para conciliar con el proveedor. |

### 2.5 Análisis (`src/pipeline.py`, `src/main.py`)

| ID | Qué puede romperse | Ejemplo | Respuesta | Por qué |
|---|---|---|---|---|
| R32 | La antigüedad depende del día en que se corre | Calcular contra `date.today()` | La fecha de corte es un parámetro (`--corte AAAA-MM-DD`). Si no se indica, se usa **la fecha más reciente del extracto**. | Con `today()`, correr el mismo archivo mañana da otro resultado y los tests se rompen solos. La última fecha del extracto es determinística: mismas entradas, misma salida. |
| R33 | Fecha de corte inválida | `--corte 2026-13-01`, `--corte 15/09/2026` | Error de uso, código `2` | Es un error de quien ejecuta, no del archivo. En la línea de comandos se pide ISO para que no haya ambigüedad. |
| R34 | Demasiadas filas rechazadas | Se rechaza más del 50 % del archivo | ABORTAR con el motivo de rechazo más frecuente. Se guarda solo el registro, y si había un `ranking.csv` de una corrida anterior se borra | Pasado ese punto el problema es el archivo (o la fecha de corte), no unas filas sueltas, y un ranking armado con lo que quedó sería engañoso. Un ranking viejo al lado de un registro nuevo también lo sería. Con exactamente el 50 % todavía se procesa. |
| R35 | No hay devoluciones abiertas | Todas cerradas | Código `0`, mensaje `No hay devoluciones abiertas al <corte>.` y `ranking.csv` con solo el encabezado | Es una respuesta válida (no hay a quién reclamarle), no un error. Distinto de R04. |
| R36 | Empates en el ranking | Dos proveedores con la misma cantidad de renglones | Orden total: renglones abiertos ↓, días de la más vieja ↓, unidades ↓, nombre ↑ | Sin desempate total el orden podría variar y el ranking no sería reproducible. Desempatar primero por antigüedad prioriza al que hace más que espera. |
| R40 | La devolución más vieja esconde cómo se reparte el resto | Un proveedor con 17 abiertas y la más vieja de enero: ¿son 17 viejas o 16 de la semana pasada? | Cada proveedor cuenta sus renglones abiertos en cuatro tramos de antigüedad: `0-30`, `31-90`, `91-180` y `+180` días. Cada límite pertenece al tramo de abajo (30 días cae en `0-30`; 31, en `31-90`) | Es el formato con que Compras y Administración miran deudas pendientes. Sin límites explícitos, un renglón de exactamente 30 días podría contarse en dos tramos o en ninguno. |
| R41 | Muchas abiertas no distinguen al que no resuelve del que tiene mucho volumen | Dos proveedores con 6 abiertas: uno cerró 3, el otro ninguna | Se informan las cerradas y el porcentaje resuelto: cerradas / (abiertas + cerradas), redondeado a entero. Un proveedor que tiene solo cerradas no entra al ranking | Para Administración no es lo mismo frenarle un pago a quien nunca resuelve que a quien resuelve pero recibe muchas devoluciones. El porcentaje no cambia el orden (R36), que sigue respondiendo a quién reclamarle primero. |

### 2.6 Salidas (`src/pipeline.py`, `src/modelos.py`)

| ID | Qué puede romperse | Ejemplo | Respuesta | Por qué |
|---|---|---|---|---|
| R37 | No existe la carpeta de salida | Repositorio recién clonado (`outputs/` está en `.gitignore`) | Se crea, con las carpetas intermedias | `outputs/` no se versiona, así que en un clon nuevo nunca existe. |
| R38 | No se puede escribir la salida | `ranking.csv` abierto en Excel (en Windows queda bloqueado) o carpeta sin permisos | ABORTAR: `No se pudo escribir ... ¿Está abierto en Excel o la carpeta no tiene permisos?` | Un `PermissionError` con traceback no le dice al usuario qué hacer. |
| R39 | Acentos rotos al abrir el CSV de salida en Excel | `Válvula` se ve como `VÃ¡lvula` | Se escribe en `utf-8-sig` (UTF-8 con BOM) | Excel solo reconoce UTF-8 si el archivo trae BOM, y el usuario final abre esto en Excel. |
| R42 | Se pide `--grafico` y matplotlib no está instalado | Un clon nuevo sin `pip install` | ABORTAR antes de procesar, con un mensaje que dice cómo instalarlo. Sin `--grafico`, matplotlib no se importa nunca | El gráfico es lo único que usa una biblioteca externa: el ranking y el registro no pueden depender de ella. Se verifica antes de leer el archivo para que la corrida no falle a mitad de camino dejando salidas incompletas. |
| R43 | Se pide `--grafico` y no hay devoluciones abiertas | Todas cerradas | No se genera el gráfico y se avisa en pantalla; el código sigue siendo `0`. Un `ranking.png` de una corrida anterior se borra, igual que el `ranking.csv` (R34) | Un gráfico vacío no dice nada, y uno viejo al lado de un ranking nuevo diría algo falso. |
| R44 | Demasiados proveedores para un gráfico legible | 40 proveedores: desde el puesto 20 las barras son astillas | El gráfico muestra los 20 primeros del ranking y lo dice en el título y en pantalla. La tabla y `ranking.csv` siguen completos | El gráfico responde a quién reclamarle primero; los últimos puestos no cambian esa respuesta y achican todo lo demás. Avisarlo evita que alguien crea que el gráfico es el ranking entero. |

---

## 3. Propiedades del resultado (`tests/test_propiedades.py`)

Además de cada caso puntual hay propiedades que tienen que cumplirse **siempre**. Se
verifican sobre el extracto de `data/` en los dos formatos y sobre cinco extractos
generados al azar con semilla fija, que mezclan filas válidas, inválidas y duplicadas.
Son la red de seguridad contra errores que no anticipamos.

| ID | Propiedad | Por qué importa |
|---|---|---|
| P01 | **Conservación de filas:** leídas = válidas + rechazadas + duplicadas, y ninguna fila está a la vez entre las válidas y las rechazadas | Ninguna fila desaparece sin dejar rastro en el registro. La suma también la verifica `procesar()` en cada corrida. |
| P02 | **Conservación de unidades y renglones:** lo que suma el ranking es igual a lo que suman las devoluciones válidas abiertas | El agrupamiento no pierde ni inventa unidades. |
| P03 | **Equivalencia CSV/JSON:** el mismo extracto en los dos formatos produce `ranking.csv` y `registro_limpieza.csv` idénticos byte a byte | Demuestra que `FuenteCSV` y `FuenteJSON` cumplen el mismo contrato. |
| P04 | **Reproducibilidad:** dos corridas con la misma entrada producen archivos idénticos byte a byte | Es lo que pide el paso 3 de la consigna. |
| P05 | **Rangos válidos:** toda cantidad es ≥ 1, ninguna fecha supera el corte, toda antigüedad es ≥ 0, todo proveedor del ranking tiene al menos un renglón y su porcentaje resuelto está entre 0 y 99 (si estuviera en 100 no tendría abiertas) | Detecta errores de cálculo y de filtrado. |
| P06 | **Orden:** el ranking respeta el criterio de R36, sin proveedores repetidos | El primero es efectivamente al que más hay que reclamarle. |
| P07 | **Tramos completos:** los tramos de antigüedad de cada proveedor suman sus renglones abiertos, y el último tramo con renglones es el de su devolución más vieja | Ningún renglón queda fuera de los tramos ni se cuenta en dos (R40). |
| T01 | **Trazabilidad:** todo identificador de este documento tiene un test con ese identificador en el nombre, y viceversa | Este documento no puede quedar desactualizado respecto de las pruebas. |

---

## 4. Cómo se prueba

- Framework: `unittest`, de la biblioteca estándar (matplotlib solo hace falta para el gráfico; sin él, el test que lo genera se saltea).
- Comando, desde la raíz del proyecto: `python3 -m unittest discover -s tests -v`
- Cada punto se prueba con un test llamado `test_<ID>_<descripcion>` o con una fila de
  una **tabla de casos**, cuyo primer valor es el ID. Las tablas (`RECHAZOS`,
  `ACEPTADOS`, `CONSERVADOS` en `test_validacion.py`; `ABORTOS` en `test_fuentes.py`)
  juntan los casos que tienen la misma forma (valor → resultado esperado). Agregar un
  caso es agregar una fila, y si un caso falla, `subTest` indica cuál.
- Cada test arma **su propio archivo mínimo** en una carpeta temporal que se borra al
  terminar (`tests/ayuda.py`). Así cada prueba muestra en el mismo lugar qué entrada
  produce qué resultado, y prueba una sola cosa.
- `tests/test_main.py` ejecuta la aplicación como un proceso aparte, igual que el
  usuario, para verificar los códigos de salida y que nunca aparezca un traceback.
- El extracto completo de `data/` se usa para el caso normal y para las propiedades.

### Resultado esperado sobre `data/devoluciones.csv`

El generador inyecta errores conocidos, así que la limpieza del extracto completo
tiene un resultado exacto, que `tests/test_pipeline.py` comprueba:

| Concepto | Cantidad | Filas | Punto |
|---|---|---|---|
| Filas leídas | 83 | — | — |
| Rechazadas | 7 | 12 (`2026-02-30`), 26 (`0002-1127`), 32 (cantidad `dos`), 38 (cantidad `0`), 46 (cantidad `1.000`), 49 (estado `anulada`), 57 (proveedor vacío) | R14, R11, R16, R17, R18, R22, R23 |
| Duplicadas | 1 | 35, copia de la 34 | R29 |
| Válidas | 75 | 83 − 7 − 1 | P01 |
| Corregidas | 5 | 5 y 10 (estado), 15 y 52 (fecha `dd/mm/aaaa`), 23 (espacio en el proveedor) | R21, R13b, R24 |
| Conservadas con aviso | 6 | 4 sin motivo, 2 sin dato de stock | R26, R27b |
| Remitos reutilizados | 2 | `0002-00001103`, `0002-00001115` | R31 |
| Remitos con varios renglones (no son error) | 4 | `0002-00001108`, `...1137`, `...1167`, `...1168` | R30 |
| Fecha de corte por defecto | `2026-09-30` | — | R32 |
| Proveedores en el ranking | 15 | primero: Proveedor 01, 17 renglones, 179 unidades | R36 |
