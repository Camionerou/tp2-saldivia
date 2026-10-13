# Datos: extracto simulado de devoluciones a proveedores

## Procedencia

| | |
|---|---|
| Fuente | Simulación propia: `src/generar_datos.py` |
| Responsable | Enzo Saldivia |
| Licencia / condiciones de uso | Datos ficticios generados para este trabajo; uso libre con fines académicos |
| Fecha de generación | 13/10/2026 |
| Reproducción | `python3 src/generar_datos.py` (semilla fija `20261013`: siempre produce los mismos archivos) |

Los datos son **simulados** a propósito. El extracto real del sistema de la fábrica tiene
nombres de proveedores y de personas y no se puede publicar. La simulación conserva lo
que importa para la pregunta: su estructura, sus proporciones (la mayoría de las
devoluciones sigue abierta y unos pocos proveedores concentran casi todas) y sus
errores de carga típicos.

`devoluciones.csv` y `devoluciones.json` contienen **el mismo extracto** en los dos
formatos: la aplicación tiene que producir el mismo resultado con cualquiera de los dos.

## Unidad de análisis

Cada fila es **un renglón de un remito de devolución**: un artículo que Calidad le
devolvió a un proveedor. Un remito puede tener varios renglones, uno por artículo.

83 filas, 18 proveedores, del 05/01/2026 al 30/09/2026.

## Variables

| Variable | Tipo | Descripción | Usada en la pregunta |
|---|---|---|---|
| `remito` | texto `0000-00000000` | Punto de venta (4 dígitos) y número (8 dígitos) del remito de devolución | Sí: identifica qué reclamar |
| `fecha` | fecha `aaaa-mm-dd` | Fecha de emisión del remito | Sí: antigüedad |
| `proveedor` | texto | Proveedor al que se le devolvió el material | Sí: agrupa el ranking |
| `articulo` | texto | Artículo devuelto | No (contexto del reclamo) |
| `cantidad` | entero ≥ 1 | Unidades devueltas | Sí: unidades pendientes |
| `motivo` | texto | Por qué se devolvió, según Calidad | No |
| `estado` | `abierta` / `cerrada` | Abierta: el proveedor todavía no repuso ni emitió nota de crédito | Sí: filtra lo pendiente |
| `descuenta_stock` | sí / no | Si la devolución se descontó del stock | No |

En el CSV los booleanos se escriben `si`/`no` y los faltantes como texto vacío; en el
JSON son `true`/`false` y `null`.

## Errores incluidos a propósito

El extracto trae los errores que aparecen en uno real, para que la validación tenga
algo que detectar. Cada uno está anotado en `src/generar_datos.py` con el punto de
ruptura que lo cubre (ver `docs/puntos_de_ruptura.md`): estados con espacios o en
mayúsculas, fechas en formato `dd/mm/aaaa`, una fecha inexistente (`2026-02-30`), un
remito mal formado, cantidades `0`, `"dos"` y `"1.000"`, un estado desconocido, un
proveedor vacío, un renglón cargado dos veces, motivos y datos de stock faltantes y
dos números de remito reutilizados.

## Limitaciones y sesgos

- Al ser simulados, los resultados **no describen a proveedores reales**: sirven para
  mostrar que el flujo funciona, no para sacar conclusiones sobre la fábrica.
- Las proporciones (cuántas devoluciones se cierran, cuánto se concentran en pocos
  proveedores) imitan lo observado en el extracto real, pero son aproximadas.
- El extracto no tiene montos: el ranking mide cantidad de renglones, unidades y
  antigüedad, no el dinero involucrado.
- El estado depende de que alguien lo actualice en el sistema. Una devolución
  resuelta pero no cerrada en el sistema aparece como abierta; es una limitación del
  dato de origen que la aplicación no puede detectar.
