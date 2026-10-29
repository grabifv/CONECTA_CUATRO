# Referencia de la API

Todos los nombres públicos del paquete `conecta_cuatro`, **generados desde el código
fuente** por [mkdocstrings](https://mkdocstrings.github.io/) cada vez que se
construye este sitio. Cambia un docstring y esta página cambia con él, así que
la referencia y el código nunca pueden contradecirse.

!!! info "Estos bloques están en inglés"
    Salen directamente de los docstrings del paquete, que están escritos en
    inglés. La prosa que los rodea sí está traducida.

---

## El juego

Las reglas, como funciones puras sobre una lista de enteros.

::: conecta_cuatro.game

---

## El contrato del jugador

La única clase que implementa alguien de fuera.

::: conecta_cuatro.player.Player

---

## El registro

Cómo se descubren los jugadores y cómo se buscan por nombre.

::: conecta_cuatro.registry.Registry

::: conecta_cuatro.manifest.load_players

---

## El torneo

Ejecutar partidas, construir la plantilla y puntuarlas.

::: conecta_cuatro.tournament.run_tournament

::: conecta_cuatro.tournament.copies_for

::: conecta_cuatro.tournament.build_roster

::: conecta_cuatro.tournament.play_match

---

## Puntuación Elo

::: conecta_cuatro.elo

---

## Estrategias reutilizables

Las piezas con las que están montados los jugadores de referencia.

::: conecta_cuatro.bots.minimax.MinimaxBot

::: conecta_cuatro.bots.smart_minimax.SmartMinimaxBot
