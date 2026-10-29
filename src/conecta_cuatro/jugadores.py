"""Jugadores: clase base, jugador humano y clase base para bots."""

from abc import ABC, abstractmethod


class Jugador(ABC):
    es_bot = False

    def __init__(self, nombre):
        self.nombre = nombre

    @property
    def clave(self):
        """Identificador único en el leaderboard (separa humanos de bots)."""
        return f"{'bot' if self.es_bot else 'humano'}:{self.nombre}"

    def nueva_partida(self, ficha):
        """Se llama al empezar cada partida. Opcional de sobrescribir."""

    @abstractmethod
    def elegir_columna(self, tablero, ficha):
        """Devuelve la columna (0..columnas-1) donde soltar la ficha."""

    def __str__(self):
        return f"{self.nombre} (bot)" if self.es_bot else self.nombre


class Abandono(Exception):
    """El jugador humano abandona la partida."""


class Humano(Jugador):
    def elegir_columna(self, tablero, ficha):
        while True:
            texto = input(
                f"{self.nombre}, elige columna (1-{tablero.columnas}, 'q' para abandonar): "
            ).strip().lower()
            if texto == "q":
                raise Abandono()
            if texto.isdigit() and tablero.es_valida(int(texto) - 1):
                return int(texto) - 1
            print("Columna no válida, prueba otra vez.")


class Bot(Jugador):
    """Clase base para bots.

    Para crear un bot nuevo, añade un archivo en la carpeta ``bots/`` con una
    subclase de ``Bot`` que defina ``nombre`` y ``elegir_columna``. Se detecta
    automáticamente al arrancar el juego.

    ``elegir_columna`` recibe una COPIA del tablero, así que el bot puede
    probar jugadas con ``tablero.soltar`` / ``tablero.deshacer`` sin riesgo.
    Si devuelve una columna inválida o lanza una excepción, pierde la partida.
    """

    es_bot = True
    nombre = "Bot sin nombre"

    def __init__(self, nombre=None):
        super().__init__(nombre or type(self).nombre)
