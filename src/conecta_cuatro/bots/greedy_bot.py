"""A greedy player: win if it can, block if it must, otherwise play the centre.

Simple, legal and clearly beatable — a realistic picture of what a first attempt
looks like. It looks exactly **one** move ahead, so it never misses an immediate
win or an immediate block, but it walks straight into a double threat and never
sets one up.
"""

from __future__ import annotations

import random

from ..game import Move, State, apply_move, current_player, legal_moves, other, winner
from ..player import Player


class GreedyBot(Player):
    """Wins at once if possible, blocks an immediate loss, else goes central."""

    def __init__(self, seed: int | None = None) -> None:
        """Create the bot.

        Args:
            seed: seed for the private RNG used to break ties between equally
                central columns.
        """
        self._rng = random.Random(seed)

    @classmethod
    def create(cls, seed: int) -> GreedyBot:
        """Build an instance seeded for one game."""
        return cls(seed=seed)

    def choose_move(self, state: State) -> Move:
        """Return a winning move, else a blocking move, else the most central one.

        Raises:
            ValueError: if ``state`` is terminal. No legal move exists, so there
                is nothing correct to return; failing loudly beats returning an
                illegal column.
        """
        moves = legal_moves(state)
        if not moves:
            raise ValueError(f"no legal move on a terminal board: {state}")
        me = current_player(state)

        # 1) A move that wins right now.
        for move in moves:
            if winner(apply_move(state, move)) == me:
                return move

        # 2) A column where the rival would win next turn: take it first. The
        #    board is re-read with the rival to move by dropping their piece in
        #    our place, which is exactly "what if they played here?".
        rival = other(me)
        for move in moves:
            board = [list(row) for row in state]
            for row in range(len(board) - 1, -1, -1):
                if board[row][move] == 0:
                    board[row][move] = rival
                    break
            if winner(board) == rival:
                return move

        # 3) Otherwise, the most central column.
        centre = (len(state[0]) - 1) / 2
        best = min(abs(c - centre) for c in moves)
        return self._rng.choice([c for c in moves if abs(c - centre) == best])
