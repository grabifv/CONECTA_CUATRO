# API reference

Every public name in the `conecta_cuatro` package, **generated from the source** by
[mkdocstrings](https://mkdocstrings.github.io/) every time this site is built.
Change a docstring and this page changes with it, so the reference and the code
can never contradict each other.

---

## The game

The rules, as pure functions over a list of ints.

::: conecta_cuatro.game

---

## The player contract

The one class an outsider implements.

::: conecta_cuatro.player.Player

---

## The registry

How players are discovered and looked up by name.

::: conecta_cuatro.registry.Registry

::: conecta_cuatro.manifest.load_players

---

## The tournament

Running games, building the roster and scoring them.

::: conecta_cuatro.tournament.run_tournament

::: conecta_cuatro.tournament.copies_for

::: conecta_cuatro.tournament.build_roster

::: conecta_cuatro.tournament.play_match

---

## Elo rating

::: conecta_cuatro.elo

---

## Reusable strategies

The pieces the reference players are built from.

::: conecta_cuatro.bots.minimax.MinimaxBot

::: conecta_cuatro.bots.smart_minimax.SmartMinimaxBot
