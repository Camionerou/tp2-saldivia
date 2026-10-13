"""Lectura del extracto de devoluciones desde CSV o JSON.

`FuenteDatos` define el contrato común: `cargar()` devuelve una lista de
`FilaCruda` con columnas ya normalizadas, o lanza `ErrorEntrada` si el archivo
completo no se puede usar. Todo lo que es igual para los dos formatos (verificar
que el archivo exista, decodificar el texto, revisar las columnas) vive en la clase
base; cada subclase solo resuelve cómo se interpreta su formato.

Los comentarios `# Rxx` remiten a docs/puntos_de_ruptura.md.
"""
import csv
import io
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

COLUMNAS_OBLIGATORIAS = ("remito", "fecha", "proveedor", "articulo", "cantidad",
                         "motivo", "estado", "descuenta_stock")


class ErrorEntrada(Exception):
    """El archivo de entrada no se puede usar. El mensaje es para el usuario."""


@dataclass
class FilaCruda:
    """Una fila tal como vino del archivo, antes de validar sus valores.

    `numero_fila` es la posición de la devolución en el archivo, empezando en 1 y
    sin contar el encabezado ni las líneas vacías. Se numera igual en CSV y en
    JSON para que el mismo extracto produzca el mismo registro en los dos formatos
    (P03). En Excel, la fila N es la fila N + 1 de la hoja, porque la 1 es el
    encabezado. Si la fila no tiene la forma esperada, `problema` explica por qué y
    `valores` puede estar incompleto.
    """
    numero_fila: int
    valores: dict
    problema: str | None = None


def normalizar_columna(nombre):
    """' Proveedor ' -> 'proveedor'. # R10b"""
    return str(nombre).strip().lower()


class FuenteDatos(ABC):
    """Contrato común para leer el extracto, sin importar el formato."""

    def __init__(self, ruta):
        self.ruta = Path(ruta)
        self.avisos = []          # mensajes generales sobre el archivo
        self.codificacion = None

    def cargar(self):
        """Lee el archivo y devuelve la lista de `FilaCruda`."""
        self._verificar_archivo()
        texto = self._leer_texto()
        columnas, filas = self._interpretar(texto)
        if not filas:
            raise ErrorEntrada(f"El archivo '{self.ruta}' no tiene devoluciones.")  # R04
        self._verificar_columnas(columnas)
        return filas

    @abstractmethod
    def _interpretar(self, texto):
        """Devuelve (columnas encontradas, lista de FilaCruda)."""

    def _verificar_archivo(self):
        if not self.ruta.exists():
            raise ErrorEntrada(f"No se encontró el archivo '{self.ruta}'.")  # R01
        if not self.ruta.is_file():
            raise ErrorEntrada(f"'{self.ruta}' es una carpeta, no un archivo.")  # R02

    def _leer_texto(self):
        datos = self.ruta.read_bytes()
        if not datos.strip():
            raise ErrorEntrada(f"El archivo '{self.ruta}' está vacío.")  # R04
        # R06: 'utf-8-sig' descarta el BOM que agrega Excel al principio.
        try:
            self.codificacion = "utf-8"
            return datos.decode("utf-8-sig")
        except UnicodeDecodeError:
            pass
        # R05: Excel en Windows guarda en cp1252.
        try:
            texto = datos.decode("cp1252")
        except UnicodeDecodeError:
            raise ErrorEntrada(
                f"No se pudo leer '{self.ruta}': no está en UTF-8 ni en Windows-1252. "
                "Volvé a exportarlo como 'CSV UTF-8'.") from None
        self.codificacion = "cp1252"
        self.avisos.append("El archivo no está en UTF-8; se leyó como Windows-1252 (cp1252).")
        return texto

    def _verificar_columnas(self, columnas):
        faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in columnas]
        if faltantes:  # R10
            raise ErrorEntrada(
                f"Al archivo '{self.ruta}' le faltan columnas obligatorias: "
                f"{', '.join(faltantes)}. Se esperaban: {', '.join(COLUMNAS_OBLIGATORIAS)}.")
        sobrantes = [c for c in columnas if c not in COLUMNAS_OBLIGATORIAS]
        if sobrantes:  # R10c
            self.avisos.append(f"Se ignoran columnas que no se usan: {', '.join(sobrantes)}.")


class FuenteCSV(FuenteDatos):
    """Extracto en CSV, separado por coma o por punto y coma."""

    def _interpretar(self, texto):
        separador = self._detectar_separador(texto)
        lector = csv.reader(io.StringIO(texto, newline=""), delimiter=separador)
        columnas = None
        filas = []
        vacias = 0
        for campos in lector:
            # R10e: líneas en blanco o con solo separadores (';;;;;;;' de Excel).
            # R10f: también pueden aparecer antes del encabezado.
            if all(not c.strip() for c in campos):
                vacias += 1
            elif columnas is None:
                columnas = [normalizar_columna(c) for c in campos]
            else:
                valores = dict(zip(columnas, campos))
                problema = None
                if len(campos) != len(columnas):  # R10d
                    problema = (f"tiene {len(campos)} campos y el encabezado tiene "
                                f"{len(columnas)}; los valores quedarían corridos de columna")
                filas.append(FilaCruda(len(filas) + 1, valores, problema))
        if vacias:
            self.avisos.append(f"Se ignoraron {vacias} líneas vacías.")
        return columnas or [], filas

    def _detectar_separador(self, texto):
        """R07: Excel con configuración argentina separa con ';'."""
        primera = texto.lstrip(" \t\r\n;,").split("\n", 1)[0]  # R10f
        if primera.count(";") > primera.count(","):
            self.avisos.append("El CSV usa ';' como separador.")
            return ";"
        return ","


class FuenteJSON(FuenteDatos):
    """Extracto en JSON: una lista de objetos, uno por renglón."""

    def _interpretar(self, texto):
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError as error:  # R08
            raise ErrorEntrada(
                f"El JSON '{self.ruta}' está mal formado (línea {error.lineno}, "
                f"columna {error.colno}): {error.msg}.") from None
        if not isinstance(datos, list):  # R09
            raise ErrorEntrada(
                f"El JSON '{self.ruta}' debe ser una lista de devoluciones "
                f"([{{...}}, {{...}}]) y es un {type(datos).__name__}.")

        columnas = []
        filas = []
        for posicion, elemento in enumerate(datos, start=1):
            if not isinstance(elemento, dict):  # R09
                filas.append(FilaCruda(posicion, {}, "no es un objeto JSON"))
                continue
            valores = {normalizar_columna(k): v for k, v in elemento.items()}
            for clave in valores:
                if clave not in columnas:
                    columnas.append(clave)
            faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in valores]
            problema = f"le faltan los campos {', '.join(faltantes)}" if faltantes else None
            filas.append(FilaCruda(posicion, valores, problema))
        # Si una columna falta en todos los objetos, `_verificar_columnas` aborta (R10);
        # si falta solo en algunos, esas filas se rechazan (R10d).
        return columnas, filas


def fuente_para(ruta):
    """Elige la implementación de `FuenteDatos` según la extensión."""
    ruta = Path(ruta)
    extension = ruta.suffix.lower()
    if extension == ".csv":
        return FuenteCSV(ruta)
    if extension == ".json":
        return FuenteJSON(ruta)
    raise ErrorEntrada(  # R03
        f"No se puede leer '{ruta}': el formato '{extension or 'sin extensión'}' "
        "no está soportado. Usá .csv o .json (desde Excel: 'Guardar como' > CSV).")
