# Seguimiento de devoluciones a proveedores

Trabajo Práctico 2 – Programación Orientada a Datos (UCA, 2026).
Autor: Enzo Saldivia.

## Problema

En una fábrica, cuando el material recibido de un proveedor no sirve (no funciona,
llega roto o no corresponde a lo pedido), Calidad lo devuelve con un remito de
devolución. Esas devoluciones quedan abiertas hasta que el proveedor repone el
material o emite una nota de crédito.

Hoy nadie las sigue: la mayoría queda abierta durante meses, la numeración de los
remitos de devolución se repite y no hay forma rápida de saber a qué proveedor hay
que reclamarle.

## Usuario

Compras y Administración. Compras necesita saber a qué proveedor reclamarle;
Administración, a qué proveedor convendría frenarle un pago mientras tenga
devoluciones pendientes.

## Pregunta

**¿Qué proveedores tienen más devoluciones abiertas y hace cuántos días que esperan?**

## Resultado esperado

Un ranking de proveedores con devoluciones abiertas: cantidad de renglones abiertos,
unidades devueltas y antigüedad de la devolución más vieja a una fecha de corte. Se
muestra en pantalla y se guarda en `outputs/`, junto con un registro de las filas
rechazadas o corregidas durante la limpieza.

## Alcance de la primera versión

Incluye: lectura de un extracto de devoluciones en CSV o JSON, validación, limpieza,
ranking por proveedor y pruebas.

Queda fuera: conexión con el sistema real de la empresa, notas de crédito, pagos,
alertas automáticas e interfaz gráfica.

## Datos

Los datos son **simulados**: reproducen la estructura y los problemas de un extracto
real (numeración repetida, motivos vacíos, pocas devoluciones cerradas) sin incluir
nombres de proveedores ni de personas. Ver `data/README.md`.
