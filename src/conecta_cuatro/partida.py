"""Desarrollo de una partida entre dos jugadores cualesquiera."""

import time
from dataclasses import dataclass

from .jugadores import Abandono
from .tablero import FICHA_1, FICHA_2, Tablero


@dataclass
class Resultado:
    ganador: object = None  # Jugador o None si empate/abandono
    perdedor: object = None
    motivo: str = ""  # "cuatro en línea", "empate", "jugada inválida", "abandono"
    movimientos: int = 0

    @property
    def empate(self):
        return self.motivo == "empate"

    @property
    def abandonada(self):
        return self.motivo == "abandono"


def jugar_partida(jugador1, jugador2, mostrar=True, pausa=0.0):
    """Juega una partida completa. jugador1 empieza con la ficha X."""
    tablero = Tablero()
    jugadores = {FICHA_1: jugador1, FICHA_2: jugador2}
    jugador1.nueva_partida(FICHA_1)
    jugador2.nueva_partida(FICHA_2)

    def log(texto=""):
        if mostrar:
            print(texto)

    ficha = FICHA_1
    log(tablero.dibujar())
    while True:
        actual = jugadores[ficha]
        rival = jugadores[FICHA_2 if ficha == FICHA_1 else FICHA_1]

        try:
            columna = actual.elegir_columna(
                tablero.copia() if actual.es_bot else tablero, ficha
            )
        except (Abandono, EOFError):
            log(f"{actual} abandona la partida.")
            return Resultado(motivo="abandono", movimientos=len(tablero.historial))
        except Exception as error:  # un bot con fallos pierde la partida
            if not actual.es_bot:
                raise
            log(f"{actual} ha fallado ({error!r}) y pierde la partida.")
            return Resultado(rival, actual, "jugada inválida", len(tablero.historial))

        if not tablero.es_valida(columna):
            log(f"{actual} eligió una columna inválida ({columna!r}) y pierde la partida.")
            return Resultado(rival, actual, "jugada inválida", len(tablero.historial))

        tablero.soltar(columna, ficha)
        if actual.es_bot:
            log(f"\n{actual} juega en la columna {columna + 1}")
        log(tablero.dibujar())

        if tablero.ganador():
            log(f"\n¡{actual} gana!")
            return Resultado(actual, rival, "cuatro en línea", len(tablero.historial))
        if tablero.lleno():
            log("\n¡Empate!")
            return Resultado(motivo="empate", movimientos=len(tablero.historial))

        ficha = FICHA_2 if ficha == FICHA_1 else FICHA_1
        if pausa and mostrar:
            time.sleep(pausa)
