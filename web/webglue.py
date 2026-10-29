"""Thin Python bridge exposed to the browser (via Pyodide).

The web page calls into this module so that the *same* Python game rules and AI
players run in the browser exactly as they do in the CI tournament — there is no
duplicated game logic in JavaScript.

Everything crosses the Python<->JS boundary as **JSON strings** (a state is a
list of rows of ints, a move is a column ``int``). That keeps the boundary dumb
and avoids fragile object marshalling. JavaScript ``JSON.stringify``/``JSON.parse``
on its side; we ``json.loads``/``json.dumps`` on ours.

No timeouts are enforced here — live play is best-effort, by design.
"""

from __future__ import annotations

import json
import time

from conecta_cuatro import game
from conecta_cuatro.bots.smart_minimax import SmartMinimaxBot
from conecta_cuatro.manifest import BUILTIN, CUSTOM, load_players
from conecta_cuatro.player import Player
from conecta_cuatro.registry import Registry

#: Milliseconds per second, used to report per-move timing.
_MS_PER_SECOND = 1000.0
#: Plies the X-ray analysis searches from each column: as deep as `hard`, with
#: the same heuristic, and well under a second per position.
_ANALYSIS_DEPTH = 5

_REGISTRY: Registry | None = None

#: Independent player instances for the bracket on the Tournament page, keyed by
#: slot id. A kind may enter a bracket several times, and each entrant must have
#: its own instance and seed — sharing one would make two `random` entrants
#: correlated, and let one entrant's cache leak into another's game.
_ENTRANTS: dict[str, Player] = {}


class _Analyst(SmartMinimaxBot):
    """The searcher behind X-ray and hints. Never entered as a player."""

    @classmethod
    def get_name(cls) -> str:
        return "x-ray"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["builtin"]

    @classmethod
    def get_description(cls) -> str:
        return "Analysis only."

    @classmethod
    def get_icon(cls) -> str:
        return "🔍"


def _require_registry() -> Registry:
    """Return the loaded registry, or fail with an actionable message.

    Every entry point below goes through this rather than touching the global
    directly: an un-awaited ``init`` otherwise surfaced as
    ``AttributeError: 'NoneType' object has no attribute 'all'``, which says
    nothing about what actually went wrong.
    """
    if _REGISTRY is None:
        raise RuntimeError("webglue.init(base_dir) must be called before using the bridge")
    return _REGISTRY


def init(base_dir: str) -> str:
    """Load players from the manifests under ``base_dir`` and return them as JSON."""
    global _REGISTRY
    _REGISTRY = load_players({
        BUILTIN: f"{base_dir}/players/{BUILTIN}/players.yaml",
        CUSTOM: f"{base_dir}/players/{CUSTOM}/players.yaml",
    })
    return players_json()


def players_json() -> str:
    """Return the registered players as JSON, with their declared identity.

    Each entry is ``{"name", "icon", "authors", "description"}``, read from the
    player's class rather than from any instance, so the UI can label and
    describe an opponent without playing a game.
    """
    return json.dumps(
        [
            {
                "name": type(p).get_name(),
                "icon": type(p).get_icon(),
                "authors": type(p).get_authors(),
                "description": type(p).get_description(),
            }
            for p in _require_registry().all()
        ]
    )


# --- pure game rules (single source of truth) ------------------------------ #

def new_board(rows: int, columns: int) -> str:
    """Return an empty ``rows`` x ``columns`` board as JSON."""
    return json.dumps(game.new_board(int(rows), int(columns)))


def legal_moves(state_json: str) -> str:
    """Return the playable columns for a JSON-encoded state, as a JSON list."""
    return json.dumps(game.legal_moves(json.loads(state_json)))


def apply_move(state_json: str, move_json: str) -> str:
    """Apply a JSON-encoded column to a JSON-encoded state; return the new state."""
    state = json.loads(state_json)
    move = json.loads(move_json)
    return json.dumps(game.apply_move(state, move))


def is_terminal(state_json: str) -> bool:
    """Return ``True`` if somebody has won or the board is full."""
    return game.is_terminal(json.loads(state_json))


def outcome(state_json: str) -> str:
    """Describe how a state stands, as JSON.

    Returns ``{"terminal": bool, "winner": 1|2|null, "line": [[r, c], ...]|null,
    "to_move": 1|2}``. ``line`` is the four-in-a-row to highlight.
    """
    state = json.loads(state_json)
    line = game.winning_line(state)
    return json.dumps({
        "terminal": game.is_terminal(state),
        "winner": game.winner(state),
        "line": [list(cell) for cell in line] if line else None,
        "to_move": game.current_player(state),
    })


# --- tournament entrants --------------------------------------------------- #

def reset_entrants() -> str:
    """Discard every entrant. Called when a new bracket is configured."""
    _ENTRANTS.clear()
    return "ok"


def create_entrant(entrant_id: str, kind: str, seed: int) -> str:
    """Build an independent instance of ``kind`` for one bracket slot.

    Uses :meth:`~conecta_cuatro.player.Player.create`, the same factory the real
    tournament uses, so a bot may configure itself from the seed.

    Raises:
        KeyError: if ``kind`` is not a registered player.
    """
    cls = type(_require_registry().get(kind))
    _ENTRANTS[entrant_id] = cls.create(seed=seed)
    return entrant_id


def _entrant(entrant_id: str) -> Player:
    """Return a built entrant, or explain that the bracket was not set up."""
    try:
        return _ENTRANTS[entrant_id]
    except KeyError:
        raise KeyError(f"unknown entrant {entrant_id!r}; call create_entrant first") from None


def entrant_move(entrant_id: str, state_json: str) -> str:
    """Ask one bracket entrant for its move. Same payload as :func:`ask_move`."""
    return _timed_move(_entrant(entrant_id), json.loads(state_json))


def play_auto(a_id: str, b_id: str, state_json: str, max_moves: int = 400) -> str:
    """Play a whole game between two entrants and return it in one call.

    Running the loop here rather than move-by-move from JavaScript keeps a
    bot-vs-bot match to a single crossing of the Python/JS boundary.

    A player that raises or returns an illegal move **forfeits**, mirroring the
    real tournament: the browser enforces no timeout, so a page must never be
    taken down by one bad player.

    Returns JSON ``{"moves": [column, ...], "winner_seat": 0|1|null,
    "result": ..., "detail": str, "elapsed_ms": [a_total, b_total]}``, where a
    ``null`` winner is a draw.
    """
    state = [list(row) for row in json.loads(state_json)]
    players = [_entrant(a_id), _entrant(b_id)]
    moves: list[int] = []
    spent = [0.0, 0.0]
    turn = 0

    while not game.is_terminal(state):
        if len(moves) >= max_moves:  # pragma: no cover - defensive
            return json.dumps({
                "moves": moves, "winner_seat": 1 - turn, "result": "forfeit_error",
                "detail": f"game exceeded {max_moves} moves", "elapsed_ms": spent,
            })
        t0 = time.perf_counter()
        try:
            move = players[turn].choose_move([list(row) for row in state])
        except BaseException as exc:  # noqa: BLE001 - any failure forfeits
            spent[turn] += (time.perf_counter() - t0) * _MS_PER_SECOND
            return json.dumps({
                "moves": moves, "winner_seat": 1 - turn, "result": "forfeit_error",
                "detail": f"raised: {exc!r}", "elapsed_ms": spent,
            })
        spent[turn] += (time.perf_counter() - t0) * _MS_PER_SECOND

        if not game.is_legal(state, move):
            return json.dumps({
                "moves": moves, "winner_seat": 1 - turn, "result": "forfeit_illegal",
                "detail": f"returned illegal move {move!r}",
                "elapsed_ms": spent,
            })
        moves.append(int(move))
        state = game.apply_move(state, int(move))
        turn = 1 - turn

    # Only the last mover can have completed a line; otherwise the board is full.
    return json.dumps({
        "moves": moves,
        "winner_seat": (1 - turn) if game.winner(state) is not None else None,
        "result": "normal", "detail": "", "elapsed_ms": spent,
    })


# --- AI moves -------------------------------------------------------------- #

def _timed_move(player: Player, state: list[list[int]]) -> str:
    """Ask ``player`` for a move on ``state`` and report it with its timing."""
    if game.is_terminal(state):
        raise ValueError("no move to make: the game is over")
    t0 = time.perf_counter()
    move = player.choose_move([list(row) for row in state])
    elapsed_ms = (time.perf_counter() - t0) * _MS_PER_SECOND
    info = getattr(player, "last_info", None)
    return json.dumps({"move": move, "elapsed_ms": elapsed_ms, "info": info})


def ask_move(name: str, state_json: str) -> str:
    """Ask the registered player ``name`` for its move on ``state``.

    Returns JSON ``{"move": column, "elapsed_ms": float, "info": {...}|null}``
    where ``info`` is the player's optional ``last_info`` (used by the "Why did
    it do that?" panel).
    """
    # The terminal guard lives in _timed_move: reference bots raise on a
    # finished board rather than returning something illegal, and the tournament
    # never asks — but the browser can, so the UI gets a clear error either way.
    return _timed_move(_require_registry().get(name), json.loads(state_json))


def analysis(state_json: str) -> str:
    """Score every column for the side to move, for X-ray mode and hints.

    Each playable column is searched :data:`_ANALYSIS_DEPTH` plies deep with the
    threat-counting heuristic of the ``hard`` player. Returns JSON::

        {"scores": [float|null, ...],   # one per column; null = column full
         "best": column|null,
         "verdict": "win"|"loss"|"unclear"|"over"}

    ``verdict`` is ``"win"`` when some column forces a win inside the horizon and
    ``"loss"`` when every column loses against best play inside it.
    """
    state = json.loads(state_json)
    width = game.columns(state)
    if game.is_terminal(state):
        return json.dumps({"scores": [None] * width, "best": None, "verdict": "over"})
    analyst = _Analyst(depth=_ANALYSIS_DEPTH, seed=0)
    board = [list(row) for row in state]
    me = game.current_player(board)
    scores: list[float | None] = [None] * width
    for column in game.legal_moves(board):
        row = analyst._drop(board, column, me)
        if game.line_through(board, row, column) is not None:
            scores[column] = analyst.WIN
        else:
            scores[column] = -analyst._negamax(
                board, game.other(me), _ANALYSIS_DEPTH - 1, 1, float("-inf"), float("inf")
            )
        analyst._lift(board, row, column)
    playable = [(score, c) for c, score in enumerate(scores) if score is not None]
    best_score, best = max(playable, key=lambda sc: (sc[0], -abs(sc[1] - (width - 1) / 2)))
    if best_score >= analyst.WIN - _ANALYSIS_DEPTH:
        verdict = "win"
    elif best_score <= analyst.LOSS + _ANALYSIS_DEPTH:
        verdict = "loss"
    else:
        verdict = "unclear"
    return json.dumps({"scores": scores, "best": best, "verdict": verdict})
