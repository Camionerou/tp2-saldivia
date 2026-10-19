"""Clases del dominio: la devolución, el resumen por proveedor y el registro de limpieza."""
from collections import Counter
from dataclasses import dataclass
from datetime import date

ESTADOS = ("abierta", "cerrada")


@dataclass(frozen=True)
class Devolucion:
    """Un renglón de un remito de devolución, ya validado.

    `motivo` vale "" si Calidad no lo escribió y `descuenta_stock` vale None si
    no se cargó: ninguno de los dos interviene en el ranking (R26, R27b).
    `numero_fila` indica de dónde salió la fila en el archivo.
    """
    remito: str
    fecha: date
    proveedor: str
    articulo: str
    cantidad: int
    motivo: str
    estado: str
    descuenta_stock: bool   # o None si no se cargó
    numero_fila: int = 0

    def esta_abierta(self):
        return self.estado == "abierta"

    def dias_abierta(self, corte):
        """Días transcurridos entre la devolución y la fecha de corte."""
        dias = (corte - self.fecha).days
        if dias < 0:
            raise ValueError(f"la devolución del {self.fecha} es posterior al corte {corte}")
        return dias

    def clave(self):
        """Todos los datos del renglón: dos filas con la misma clave son un duplicado (R29)."""
        return (self.remito, self.fecha, self.proveedor, self.articulo, self.cantidad,
                self.motivo, self.estado, self.descuenta_stock)


@dataclass
class ResumenProveedor:
    """Devoluciones abiertas de un proveedor a una fecha de corte."""
    proveedor: str
    renglones: int = 0
    unidades: int = 0
    fecha_mas_vieja: date = None
    dias_mas_vieja: int = 0

    def agregar(self, devolucion, corte):
        """Suma una devolución abierta de este proveedor."""
        self.renglones += 1
        self.unidades += devolucion.cantidad
        if self.fecha_mas_vieja is None or devolucion.fecha < self.fecha_mas_vieja:
            self.fecha_mas_vieja = devolucion.fecha
            self.dias_mas_vieja = devolucion.dias_abierta(corte)

    def orden(self):
        """Criterio del ranking (R36): más renglones, más antigüedad, más unidades, nombre."""
        return (-self.renglones, -self.dias_mas_vieja, -self.unidades, self.proveedor)


@dataclass(frozen=True)
class Evento:
    """Una cosa que la limpieza le hizo (o notó) a una fila."""
    numero_fila: int     # None en avisos que no son de una fila
    remito: str
    accion: str          # rechazada, corregida, duplicada o aviso
    campo: str
    valor_original: str
    motivo: str


class RegistroLimpieza:
    """Lleva la cuenta de todo lo que la limpieza rechazó, corrigió o advirtió."""

    COLUMNAS = ("fila", "remito", "accion", "campo", "valor_original", "motivo")

    def __init__(self):
        self.eventos = []

    def anotar(self, numero_fila, remito, accion, campo, valor_original, motivo):
        """`accion` es rechazada, corregida, duplicada o aviso."""
        valor = "" if valor_original is None else str(valor_original)
        self.eventos.append(Evento(numero_fila, str(remito or ""), accion, campo, valor, motivo))

    def filas_con(self, accion):
        """Filas (sin repetir) que tuvieron al menos un evento de esa acción."""
        return sorted({e.numero_fila for e in self.eventos
                       if e.accion == accion and e.numero_fila is not None})

    def contar(self, accion):
        return len(self.filas_con(accion))

    def motivo_mas_frecuente(self, accion):
        motivos = Counter(e.motivo for e in self.eventos if e.accion == accion)
        return motivos.most_common(1)[0][0] if motivos else None

    def como_filas(self):
        """Los eventos como filas para escribir en registro_limpieza.csv."""
        return [["" if e.numero_fila is None else e.numero_fila, e.remito, e.accion,
                 e.campo, e.valor_original, e.motivo] for e in self.eventos]
