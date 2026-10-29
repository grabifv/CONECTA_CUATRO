"""The plain minimax bot: a deliberately weak heuristic, little board knowledge.

This is the "medium" rung. It is genuinely imperfect, and the reason is the
heuristic: at the depth limit it looks only at **how many of its pieces sit in
the central columns**. That is a real rule of thumb — central cells take part
in more lines — but it says nothing about threats being built up, which is what
actually decides a Connect Four game.

The practical effect is that it never misses a win or a block it can see inside
its horizon, and otherwise drifts towards the centre without a plan.
"""

from __future__ import annotations

from ..game import EMPTY, State, other
from .minimax import MinimaxBot

#: Weight of the centre heuristic. Deliberately small, so that a proven
#: WIN/LOSS from the search always dominates a heuristic preference.
_HEURISTIC_WEIGHT = 1.0


class BasicMinimaxBot(MinimaxBot):
    """Negamax + alpha-beta, evaluating leaves by pieces near the centre."""

    def evaluate(self, state: State, player: int) -> float:
        """Prefer positions where ``player`` holds more central cells than the rival.

        Each piece scores more the closer its column is to the centre. This is a
        *weak* heuristic on purpose: it cannot tell a winning threat from a
        harmless piece.
        """
        width = len(state[0])
        centre = (width - 1) / 2
        rival = other(player)
        score = 0.0
        for row in state:
            for c, cell in enumerate(row):
                if cell == EMPTY:
                    continue
                weight = centre + 1 - abs(c - centre)
                if cell == player:
                    score += weight
                elif cell == rival:
                    score -= weight
        return _HEURISTIC_WEIGHT * score
