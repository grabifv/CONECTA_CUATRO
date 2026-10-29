"""Bot de ejemplo: gana si puede, bloquea si debe y si no prefiere el centro."""

import random

from ..jugadores import Bot
from ..tablero import ficha_rival


class BotBasico(Bot):
    nombre = "Basico"

    def elegir_columna(self, tablero, ficha):
        validas = tablero.columnas_validas()

        # 1) Si puedo ganar ya, gano. 2) Si el rival gana en esa columna, la bloqueo.
        for objetivo in (ficha, ficha_rival(ficha)):
            for columna in validas:
                tablero.soltar(columna, objetivo)
                gana = tablero.ganador() is not None
                tablero.deshacer()
                if gana:
                    return columna

        # 3) Columnas más cercanas al centro primero.
        centro = tablero.columnas // 2
        mejor = min(abs(c - centro) for c in validas)
        return random.choice([c for c in validas if abs(c - centro) == mejor])
