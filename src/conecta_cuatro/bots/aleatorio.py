"""Bot de ejemplo: juega en una columna válida al azar."""

import random

from ..jugadores import Bot


class BotAleatorio(Bot):
    nombre = "Aleatorio"

    def elegir_columna(self, tablero, ficha):
        return random.choice(tablero.columnas_validas())
