"""Menú principal de Conecta Cuatro."""

import os
from pathlib import Path

from .bots import cargar_bots
from .jugadores import Humano
from .leaderboard import Leaderboard
from .partida import jugar_partida

RUTA_LEADERBOARD = Path(__file__).resolve().parents[2] / "leaderboard.json"


def pedir_opcion(texto, opciones):
    """Pide un número entre 1 y len(opciones). Devuelve el índice (0-based)."""
    while True:
        for i, opcion in enumerate(opciones, 1):
            print(f"  {i}. {opcion}")
        respuesta = input(texto).strip()
        if respuesta.isdigit() and 1 <= int(respuesta) <= len(opciones):
            return int(respuesta) - 1
        print("Opción no válida.\n")


def pedir_entero(texto, defecto):
    respuesta = input(f"{texto} [{defecto}]: ").strip()
    return int(respuesta) if respuesta.isdigit() and int(respuesta) > 0 else defecto


def pedir_nombre(texto, ocupado=None):
    while True:
        nombre = input(texto).strip()
        if not nombre:
            print("El nombre no puede estar vacío.")
        elif nombre == ocupado:
            print("Ese nombre ya lo usa el otro jugador.")
        else:
            return nombre


def elegir_bot(bots, texto):
    nombres = list(bots)
    return bots[nombres[pedir_opcion(texto, nombres)]]()


def jugar_y_registrar(leaderboard, jugador1, jugador2, **kwargs):
    resultado = jugar_partida(jugador1, jugador2, **kwargs)
    leaderboard.registrar(resultado, jugador1, jugador2)
    return resultado


def modo_humano_vs_humano(leaderboard):
    j1 = Humano(pedir_nombre("Nombre del jugador 1 (X): "))
    j2 = Humano(pedir_nombre("Nombre del jugador 2 (O): ", ocupado=j1.nombre))
    while True:
        jugar_y_registrar(leaderboard, j1, j2)
        if input("\n¿Revancha? (s/n): ").strip().lower() != "s":
            return
        j1, j2 = j2, j1  # alterna quién empieza


def modo_humano_vs_bot(leaderboard, bots):
    humano = Humano(pedir_nombre("Tu nombre: "))
    print("\nElige rival:")
    bot = elegir_bot(bots, "Bot: ")
    empiezas = input("¿Quieres empezar tú? (s/n): ").strip().lower() != "n"
    while True:
        orden = (humano, bot) if empiezas else (bot, humano)
        jugar_y_registrar(leaderboard, *orden, pausa=0.3)
        if input("\n¿Revancha? (s/n): ").strip().lower() != "s":
            return
        empiezas = not empiezas


def modo_bot_vs_bot(leaderboard, bots):
    print("\nPrimer bot:")
    bot1 = elegir_bot(bots, "Bot 1: ")
    print("\nSegundo bot:")
    bot2 = elegir_bot(bots, "Bot 2: ")
    if bot1.nombre == bot2.nombre:
        print("(Mismo bot contra sí mismo: sus victorias y derrotas se anotan a la misma entrada.)")
    partidas = pedir_entero("¿Cuántas partidas?", 10)
    mostrar = input("¿Mostrar el tablero de cada partida? (s/n): ").strip().lower() == "s"

    marcador = {bot1.nombre: 0, bot2.nombre: 0, "Empates": 0}
    for i in range(partidas):
        orden = (bot1, bot2) if i % 2 == 0 else (bot2, bot1)  # alterna quién empieza
        if mostrar:
            print(f"\n=== Partida {i + 1}/{partidas}: {orden[0]} (X) vs {orden[1]} (O) ===")
        resultado = jugar_y_registrar(leaderboard, *orden, mostrar=mostrar, pausa=0.2)
        clave = "Empates" if resultado.empate else resultado.ganador.nombre
        marcador[clave] += 1

    print("\nResultado del enfrentamiento:")
    for nombre, cantidad in marcador.items():
        print(f"  {nombre}: {cantidad}")


def modo_torneo(leaderboard, bots):
    """Todos los bots contra todos (ida y vuelta)."""
    if len(bots) < 2:
        print("Hacen falta al menos dos bots para un torneo.")
        return
    rondas = pedir_entero("¿Partidas por cada cruce (ida y vuelta)?", 2)
    instancias = {nombre: clase() for nombre, clase in bots.items()}
    puntos = {nombre: 0 for nombre in instancias}
    nombres = list(instancias)
    for a in range(len(nombres)):
        for b in range(a + 1, len(nombres)):
            for r in range(rondas):
                j1, j2 = instancias[nombres[a]], instancias[nombres[b]]
                if r % 2:
                    j1, j2 = j2, j1
                resultado = jugar_y_registrar(leaderboard, j1, j2, mostrar=False)
                if resultado.empate:
                    puntos[j1.nombre] += 1
                    puntos[j2.nombre] += 1
                else:
                    puntos[resultado.ganador.nombre] += 3

    print("\nClasificación del torneo (3 pts victoria, 1 empate):")
    for nombre, pts in sorted(puntos.items(), key=lambda x: x[1], reverse=True):
        print(f"  {nombre:<20} {pts} pts")


def modo_leaderboard(leaderboard):
    filtro = pedir_opcion("Mostrar: ", ["Todos", "Solo humanos", "Solo bots"])
    leaderboard.mostrar([None, "humano", "bot"][filtro])


def main():
    if os.name == "nt":
        os.system("")  # activa los colores ANSI en la consola de Windows
    leaderboard = Leaderboard(str(RUTA_LEADERBOARD))
    bots = cargar_bots()

    opciones = [
        "Jugador vs Jugador",
        "Jugador vs Bot",
        "Bot vs Bot",
        "Torneo de bots (todos contra todos)",
        "Ver leaderboard",
        "Salir",
    ]
    while True:
        print("\n===== CONECTA CUATRO =====")
        eleccion = pedir_opcion("Elige una opción: ", opciones)
        try:
            if eleccion == 0:
                modo_humano_vs_humano(leaderboard)
            elif eleccion in (1, 2, 3) and not bots:
                print("No hay bots disponibles. Añade uno en la carpeta bots/.")
            elif eleccion == 1:
                modo_humano_vs_bot(leaderboard, bots)
            elif eleccion == 2:
                modo_bot_vs_bot(leaderboard, bots)
            elif eleccion == 3:
                modo_torneo(leaderboard, bots)
            elif eleccion == 4:
                modo_leaderboard(leaderboard)
            else:
                print("¡Hasta la próxima!")
                return
        except KeyboardInterrupt:
            print("\nVolviendo al menú...")
        except EOFError:  # se cerró la entrada (Ctrl+Z / fin de fichero)
            print("\n¡Hasta la próxima!")
            return


if __name__ == "__main__":
    main()
