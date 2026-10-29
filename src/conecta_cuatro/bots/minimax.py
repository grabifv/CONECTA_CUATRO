"""A generic depth-limited minimax search, with **no domain knowledge at all**.

This module knows how to *search*. It does not know anything about what makes a
Connect Four position good — that is supplied by a subclass through one hook:

* :meth:`MinimaxBot.evaluate` — score a position once the depth limit is hit.

Wins, losses and draws found *inside* the search horizon are exact and need no
hook: the search itself sees four-in-a-row and full boards.

Why the search works on one mutable grid
----------------------------------------
:func:`conecta_cuatro.game.apply_move` is pure — it copies the board — which is
what the tournament and the web app want. A search visits thousands of nodes per
move, and copying a 6x7 grid at every one of them is the single biggest cost.
So the search copies the board **once**, then drops and lifts pieces on that
private copy (:meth:`MinimaxBot._drop` / :meth:`MinimaxBot._lift`). The board the
caller passed in is never touched.

For the same reason a win is detected by looking only at the lines through the
piece just played (:func:`conecta_cuatro.game.line_through`), not by scanning the
whole board.

Negamax sign convention
-----------------------
Every value is from the perspective of the **side to move**. When the previous
move completed four in a row, the side to move has lost: that is
:attr:`MinimaxBot.LOSS`, softened by how deep it was found so that a quick win
is preferred to a slow one (and a slow loss to a quick one). A full board with
no winner is a draw, worth ``0``. A child's value is negated when it is brought
back to the parent.
"""

from __future__ import annotations

import random
from typing import Any

from ..game import EMPTY, Move, State, current_player, legal_moves, line_through, other
from ..player import Player

_INF = float("inf")


class MinimaxBot(Player):
    """Depth-limited negamax with alpha-beta pruning.

    Subclass it and override :meth:`evaluate` to build a player. Left alone, the
    search finds a forced win or loss within ``depth`` plies and is indifferent
    to everything else.

    Like every class in this package it stays abstract until a subclass declares
    its identity (:meth:`~conecta_cuatro.player.Player.get_name` and friends), so
    it cannot be entered in a tournament by accident.
    """

    #: Value of a position the side to move has already won (before the depth
    #: discount).
    WIN = 10_000.0
    #: Value of a position the side to move has already lost.
    LOSS = -10_000.0
    #: Value of a full board with no four-in-a-row.
    DRAW = 0.0

    def __init__(self, depth: int = 3, seed: int | None = None) -> None:
        """Create the searcher.

        Args:
            depth: plies to search before falling back to :meth:`evaluate`.
                Must be at least 1.
            seed: seed for the private RNG used only to break ties between
                equally-valued moves. A private RNG keeps the bot reproducible
                without touching global random state.

        Raises:
            ValueError: if ``depth`` is less than 1.
        """
        if depth < 1:
            raise ValueError(f"depth must be >= 1, got {depth}")
        self.depth = depth
        self._rng = random.Random(seed)
        #: Populated after each search, for the web "Why did it do that?" panel.
        #: An optional extra, not part of the Player contract. ``Any`` because it
        #: is serialised straight to JSON and crosses into JavaScript.
        self.last_info: dict[str, Any] = {}
        self._nodes = 0

    # ------------------------------------------------------------------ #
    # Hook for subclasses                                                #
    # ------------------------------------------------------------------ #

    def evaluate(self, state: State, player: int) -> float:
        """Score ``state`` for ``player`` (the side to move) at the depth limit.

        Return a value strictly between :attr:`LOSS` and :attr:`WIN`, so that a
        proven win or loss always dominates a heuristic guess. The board is the
        search's working copy: read it, never modify it.

        The default is indifferent (``0.0``): with no heuristic, the search still
        finds forced wins and losses inside ``depth`` plies.
        """
        return 0.0

    # ------------------------------------------------------------------ #
    # Search                                                             #
    # ------------------------------------------------------------------ #

    def choose_move(self, state: State) -> Move:
        """Return the best move found, breaking ties randomly.

        Each root move is searched with a **full window**. Tightening alpha at
        the root would make later moves return bounds rather than values, which
        would corrupt the set of equally-best moves used for tie-breaking.

        Raises:
            ValueError: if ``state`` is terminal, so no move exists.
        """
        moves = legal_moves(state)
        if not moves:
            raise ValueError("no legal move on a terminal board")
        board = [list(row) for row in state]
        me = current_player(board)
        self._nodes = 0
        best_value = -_INF
        best_moves: list[Move] = []

        for move in self._ordered(board, moves):
            row = self._drop(board, move, me)
            if line_through(board, row, move) is not None:
                value = self.WIN
            else:
                value = -self._negamax(board, other(me), self.depth - 1, 1, -_INF, _INF)
            self._lift(board, row, move)
            if value > best_value:
                best_value = value
                best_moves = [move]
            elif value == best_value:
                best_moves.append(move)

        chosen = self._rng.choice(best_moves)
        self.last_info = {
            "player": self.name,
            "depth": self.depth,
            "score": best_value,
            "nodes": self._nodes,
            "chosen": chosen,
            "note": self._explain(best_value),
        }
        return chosen

    def _negamax(
        self, board: State, player: int, depth: int, ply: int, alpha: float, beta: float
    ) -> float:
        """Return the negamax value of ``board`` for ``player``, ``depth`` plies deep.

        Args:
            board: the working grid; restored to its original contents on return.
            player: the side to move.
            depth: remaining plies before falling back to :meth:`evaluate`.
            ply: plies already played below the root, used to prefer quick wins.
            alpha: best value the side to move can already guarantee.
            beta: best value the opponent can already guarantee.

        Returns:
            The value of ``board``; higher is better for ``player``.
        """
        self._nodes += 1
        moves = [c for c in range(len(board[0])) if board[0][c] == EMPTY]
        if not moves:
            return self.DRAW
        # `<= 0`, not `== 0`: choose_move enters the recursion at `depth - 1`, so
        # a depth of 0 would otherwise skip the cutoff and search the whole tree.
        if depth <= 0:
            return self.evaluate(board, player)

        value = -_INF
        for move in self._ordered(board, moves):
            row = self._drop(board, move, player)
            if line_through(board, row, move) is not None:
                # The side to move wins right now; sooner is better.
                child = self.WIN - ply
            else:
                child = -self._negamax(board, other(player), depth - 1, ply + 1, -beta, -alpha)
            self._lift(board, row, move)
            value = max(value, child)
            alpha = max(alpha, value)
            if alpha >= beta:
                break  # alpha-beta cutoff
        return value

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _ordered(board: State, moves: list[Move]) -> list[Move]:
        """Return ``moves`` centre-first.

        Central columns take part in more lines, so they are usually the best
        moves; trying them first makes alpha-beta cut off far more often. The
        result is the same, only reached faster.
        """
        centre = (len(board[0]) - 1) / 2
        return sorted(moves, key=lambda c: abs(c - centre))

    @staticmethod
    def _drop(board: State, column: int, player: int) -> int:
        """Drop ``player``'s piece into ``column`` of the working grid; return its row."""
        for row in range(len(board) - 1, -1, -1):
            if board[row][column] == EMPTY:
                board[row][column] = player
                return row
        raise ValueError(f"column {column} is full")  # pragma: no cover - guarded

    @staticmethod
    def _lift(board: State, row: int, column: int) -> None:
        """Undo :meth:`_drop`."""
        board[row][column] = EMPTY

    def _explain(self, score: float) -> str:
        """Return a human-readable note about a root ``score``, for the web panel."""
        if score >= self.WIN - self.depth:
            return f"Found a forced win within {self.depth} plies."
        if score <= self.LOSS + self.depth:
            return (
                f"Every move loses against perfect play within {self.depth} plies; "
                "playing on in the hope of a mistake."
            )
        return f"No forced result within {self.depth} plies; went with the heuristic."
