"""Play Connect Four in the terminal, with a persistent local leaderboard.

This is the hands-on side of the project, next to the automatic tournament and
the web app: two people at one keyboard, a person against any admitted bot, or
two bots against each other, with every finished game recorded in a local
leaderboard of wins, losses and draws per person and per bot.

The bots are the ones the manifests admit (see :mod:`conecta_cuatro.manifest`),
so a new player merged into ``players/`` shows up here with no extra step. The
user-facing text is in Spanish; the code follows the rest of the package.

Run it with ``conecta-cuatro`` (after ``pip install -e .``) or ``python -m
conecta_cuatro``.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import game
from .manifest import REPO_ROOT, load_players
from .player import Player
from .registry import Registry

#: Where the local leaderboard lives. Ignored by git: it records *your* games,
#: unlike ``results/leaderboard.json``, which the tournament workflow publishes.
DEFAULT_LEADERBOARD = REPO_ROOT / "leaderboard_local.json"

#: Terminal colours for the two pieces (red and yellow, as on the web page).
_COLOURS = {game.PLAYER_1: "\033[91m", game.PLAYER_2: "\033[93m"}
_RESET = "\033[0m"


class Quit(Exception):
    """A person typed ``q``: the game is abandoned and not recorded."""


@dataclass
class Seat:
    """One side of a game: a person (``player is None``) or a bot."""

    name: str
    player: Player | None = None

    @property
    def is_bot(self) -> bool:
        return self.player is not None

    @property
    def key(self) -> str:
        """Leaderboard key. Kept apart by kind, so a person may share a bot's name."""
        return f"{'bot' if self.is_bot else 'humano'}:{self.name}"

    def __str__(self) -> str:
        return f"{self.name} (bot)" if self.is_bot else self.name


@dataclass
class Outcome:
    """How a terminal game ended. ``winner`` is ``None`` for a draw or a quit."""

    winner: Seat | None
    loser: Seat | None
    reason: str  # "cuatro en línea", "empate", "jugada inválida", "abandono"


# --------------------------------------------------------------------------- #
# Leaderboard                                                                  #
# --------------------------------------------------------------------------- #

class Leaderboard:
    """Wins, losses and draws per person and per bot, saved as JSON."""

    def __init__(self, path: Path = DEFAULT_LEADERBOARD) -> None:
        self.path = Path(path)
        self.data: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            print(f"Aviso: no se pudo leer {self.path}; se empieza un leaderboard nuevo.")
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def _entry(self, seat: Seat) -> dict[str, Any]:
        return self.data.setdefault(seat.key, {
            "nombre": seat.name,
            "tipo": "bot" if seat.is_bot else "humano",
            "victorias": 0,
            "derrotas": 0,
            "empates": 0,
        })

    def record(self, outcome: Outcome, first: Seat, second: Seat) -> None:
        """Record a finished game. An abandoned one counts for nobody."""
        if outcome.reason == "abandono":
            return
        if outcome.winner is None or outcome.loser is None:
            self._entry(first)["empates"] += 1
            if second.key != first.key:
                self._entry(second)["empates"] += 1
        else:
            self._entry(outcome.winner)["victorias"] += 1
            self._entry(outcome.loser)["derrotas"] += 1
        self._save()

    def ranking(self, kind: str | None = None) -> list[dict[str, Any]]:
        """Entries best first: by wins, then win rate. ``kind`` filters humans or bots."""
        rows = [e for e in self.data.values() if kind is None or e["tipo"] == kind]

        def rate(e: dict[str, Any]) -> float:
            played = e["victorias"] + e["derrotas"] + e["empates"]
            return e["victorias"] / played if played else 0.0

        return sorted(rows, key=lambda e: (e["victorias"], rate(e)), reverse=True)

    def render(self, kind: str | None = None) -> str:
        rows = self.ranking(kind)
        if not rows:
            return "El leaderboard está vacío. ¡Juega alguna partida!"
        lines = [
            f"{'#':>3}  {'Nombre':<22}{'Tipo':<8}{'V':>5}{'D':>5}{'E':>5}{'% V':>8}",
            "-" * 56,
        ]
        for i, e in enumerate(rows, 1):
            played = e["victorias"] + e["derrotas"] + e["empates"]
            pct = 100 * e["victorias"] / played if played else 0.0
            lines.append(
                f"{i:>3}  {e['nombre'][:21]:<22}{e['tipo']:<8}"
                f"{e['victorias']:>5}{e['derrotas']:>5}{e['empates']:>5}{pct:>7.1f}%"
            )
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Playing one game                                                             #
# --------------------------------------------------------------------------- #

def draw_board(state: game.State, colour: bool = True) -> str:
    """Return the board as text, coloured for a terminal when ``colour``."""
    text = game.render(state)
    if not colour:
        return text
    for piece, symbol in ((game.PLAYER_1, "X"), (game.PLAYER_2, "O")):
        text = text.replace(f" {symbol}", f" {_COLOURS[piece]}{symbol}{_RESET}")
    return text


def ask_human(seat: Seat, state: game.State, read: Callable[[str], str]) -> int:
    """Ask a person for a column (1-based on screen). ``q`` quits the game."""
    width = game.columns(state)
    while True:
        text = read(f"{seat}, elige columna (1-{width}, 'q' para abandonar): ").strip().lower()
        if text == "q":
            raise Quit
        if text.isdigit() and game.is_legal(state, int(text) - 1):
            return int(text) - 1
        print("Columna no válida, prueba otra vez.")


def play_game(
    first: Seat,
    second: Seat,
    *,
    rows: int = game.DEFAULT_ROWS,
    columns: int = game.DEFAULT_COLUMNS,
    show: bool = True,
    pause: float = 0.0,
    read: Callable[[str], str] = input,
    colour: bool = True,
) -> Outcome:
    """Play one game to the end. ``first`` plays ``X`` and moves first.

    A bot that raises or returns an illegal move loses on the spot, as in the
    tournament. A person who types ``q`` (or closes the input) abandons the game,
    which is then not recorded.
    """
    def log(text: str = "") -> None:
        if show:
            print(text)

    state = game.new_board(rows, columns)
    seats = (first, second)
    turn = 0
    log(draw_board(state, colour))
    while not game.is_terminal(state):
        seat, rival = seats[turn], seats[1 - turn]
        if seat.player is None:
            try:
                move: object = ask_human(seat, state, read)
            except (Quit, EOFError):
                log(f"{seat} abandona la partida.")
                return Outcome(None, None, "abandono")
        else:
            try:
                move = seat.player.choose_move([list(row) for row in state])
            except Exception as exc:  # noqa: BLE001 - a broken bot loses, the menu survives
                log(f"{seat} ha fallado ({exc!r}) y pierde la partida.")
                return Outcome(rival, seat, "jugada inválida")
            if not game.is_legal(state, move):
                log(f"{seat} eligió una columna inválida ({move!r}) y pierde la partida.")
                return Outcome(rival, seat, "jugada inválida")
            assert isinstance(move, int)
            log(f"\n{seat} juega en la columna {move + 1}")
        assert isinstance(move, int)
        state = game.apply_move(state, move)
        log(draw_board(state, colour))
        if pause and seat.is_bot:
            time.sleep(pause)
        turn = 1 - turn

    if game.winner(state) is None:
        log("\n¡Empate! El tablero está lleno.")
        return Outcome(None, None, "empate")
    winner, loser = seats[1 - turn], seats[turn]
    log(f"\n¡{winner} gana con cuatro en línea!")
    return Outcome(winner, loser, "cuatro en línea")


# --------------------------------------------------------------------------- #
# The menu                                                                     #
# --------------------------------------------------------------------------- #

class Menu:
    """The interactive menu. ``read`` is injectable so it can be driven in tests."""

    OPTIONS = [
        "Jugador vs Jugador",
        "Jugador vs Bot",
        "Bot vs Bot",
        "Ver leaderboard",
        "Salir",
    ]

    def __init__(
        self,
        registry: Registry,
        leaderboard: Leaderboard,
        read: Callable[[str], str] = input,
        colour: bool = True,
    ) -> None:
        self.registry = registry
        self.leaderboard = leaderboard
        self.read = read
        self.colour = colour

    # -- prompts ------------------------------------------------------------ #

    def choose(self, prompt: str, options: list[str]) -> int:
        while True:
            for i, option in enumerate(options, 1):
                print(f"  {i}. {option}")
            answer = self.read(prompt).strip()
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return int(answer) - 1
            print("Opción no válida.\n")

    def ask_name(self, prompt: str, taken: str | None = None) -> str:
        while True:
            name = self.read(prompt).strip()
            if not name:
                print("El nombre no puede estar vacío.")
            elif name == taken:
                print("Ese nombre ya lo usa el otro jugador.")
            else:
                return name

    def ask_int(self, prompt: str, default: int) -> int:
        answer = self.read(f"{prompt} [{default}]: ").strip()
        return int(answer) if answer.isdigit() and int(answer) > 0 else default

    def yes(self, prompt: str) -> bool:
        return self.read(prompt).strip().lower() == "s"

    def pick_bot(self, prompt: str, seed: int = 0) -> Seat:
        kinds = [type(p) for p in self.registry.all()]
        labels = [f"{k.get_icon()} {k.get_name()} — {k.get_description()}" for k in kinds]
        cls = kinds[self.choose(prompt, labels)]
        return Seat(cls.get_name(), cls.create(seed=seed))

    def play_and_record(self, first: Seat, second: Seat, **kwargs: Any) -> Outcome:
        outcome = play_game(first, second, read=self.read, colour=self.colour, **kwargs)
        self.leaderboard.record(outcome, first, second)
        return outcome

    # -- modes -------------------------------------------------------------- #

    def human_vs_human(self) -> None:
        a = Seat(self.ask_name("Nombre del jugador 1 (X): "))
        b = Seat(self.ask_name("Nombre del jugador 2 (O): ", taken=a.name))
        while True:
            self.play_and_record(a, b)
            if not self.yes("\n¿Revancha? (s/n): "):
                return
            a, b = b, a  # the other one starts

    def human_vs_bot(self) -> None:
        human = Seat(self.ask_name("Tu nombre: "))
        print("\nElige rival:")
        bot = self.pick_bot("Bot: ")
        human_first = not self.read("¿Quieres empezar tú? (s/n): ").strip().lower().startswith("n")
        while True:
            order = (human, bot) if human_first else (bot, human)
            self.play_and_record(*order, pause=0.3)
            if not self.yes("\n¿Revancha? (s/n): "):
                return
            human_first = not human_first

    def bot_vs_bot(self) -> None:
        print("\nPrimer bot:")
        a = self.pick_bot("Bot 1: ", seed=1)
        print("\nSegundo bot:")
        b = self.pick_bot("Bot 2: ", seed=2)
        games = self.ask_int("¿Cuántas partidas?", 10)
        show = self.yes("¿Mostrar el tablero de cada partida? (s/n): ")
        score = {a.name: 0, b.name: 0, "Empates": 0}
        for i in range(games):
            first, second = (a, b) if i % 2 == 0 else (b, a)  # alternate who starts
            if show:
                print(f"\n=== Partida {i + 1}/{games}: {first} (X) vs {second} (O) ===")
            outcome = self.play_and_record(first, second, show=show, pause=0.2 if show else 0.0)
            score["Empates" if outcome.winner is None else outcome.winner.name] += 1
        print("\nResultado del enfrentamiento:")
        for name, count in score.items():
            print(f"  {name}: {count}")

    def show_leaderboard(self) -> None:
        which = self.choose("Mostrar: ", ["Todos", "Solo personas", "Solo bots"])
        print()
        print(self.leaderboard.render([None, "humano", "bot"][which]))

    def run(self) -> None:
        actions = [self.human_vs_human, self.human_vs_bot, self.bot_vs_bot, self.show_leaderboard]
        while True:
            print("\n===== CONECTA CUATRO =====")
            try:
                choice = self.choose("Elige una opción: ", self.OPTIONS)
                if choice == len(actions):
                    print("¡Hasta la próxima!")
                    return
                actions[choice]()
            except KeyboardInterrupt:
                print("\nVolviendo al menú...")
            except EOFError:  # the input was closed (Ctrl+Z / Ctrl+D)
                print("\n¡Hasta la próxima!")
                return


def main(argv: list[str] | None = None) -> int:
    """Entry point of ``conecta-cuatro``."""
    del argv  # no options yet; accepted for symmetry with the tournament CLI
    if os.name == "nt":
        os.system("")  # turns on ANSI colours in the classic Windows console
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    registry = load_players()
    if not len(registry):
        print("No se pudo cargar ningún bot de players/.", file=sys.stderr)
        return 1
    Menu(registry, Leaderboard()).run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
