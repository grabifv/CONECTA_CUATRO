"""The strong minimax bot: deeper search and a heuristic that reads threats.

Same search as :class:`~conecta_cuatro.bots.basic_minimax.BasicMinimaxBot`; the
difference is entirely in what it *knows*. At the depth limit it scores every
**window** — every run of four cells in a line that could still become a
four-in-a-row:

* a window holding pieces of **both** players is dead and scores nothing;
* a window holding only one player's pieces is a *potential* line, worth more
  the fuller it is — three pieces and a gap is a real threat;
* pieces in the central column get a small bonus, since they sit in the most
  windows.

That is the classic Connect Four evaluation. It is not perfect — it does not
understand *zugzwang* or which row a threat sits on (odd/even threats decide
many expert games) — which is deliberate: the top of the ladder stays open.
"""

from __future__ import annotations

from ..game import CONNECT, DIRECTIONS, EMPTY, State, other
from .minimax import MinimaxBot

#: Score of a window holding ``n`` pieces of one player and no rival piece.
#: Three-and-a-gap is a threat; two is a start; one is barely anything.
_WINDOW_SCORE = {1: 1.0, 2: 10.0, 3: 50.0}
#: Bonus per piece in the central column.
_CENTRE_BONUS = 3.0
#: Weight applied to the rival's windows. Slightly above one: blocking a threat
#: matters a little more than building one of the same size.
_DEFENCE_WEIGHT = 1.2


def windows(height: int, width: int) -> list[list[tuple[int, int]]]:
    """Return every line of :data:`~conecta_cuatro.game.CONNECT` cells on the board."""
    found: list[list[tuple[int, int]]] = []
    for r in range(height):
        for c in range(width):
            for dr, dc in DIRECTIONS:
                end_r, end_c = r + dr * (CONNECT - 1), c + dc * (CONNECT - 1)
                if 0 <= end_r < height and 0 <= end_c < width:
                    found.append([(r + dr * i, c + dc * i) for i in range(CONNECT)])
    return found


class SmartMinimaxBot(MinimaxBot):
    """Negamax + alpha-beta, evaluating leaves by open windows (threats)."""

    def __init__(self, depth: int = 4, seed: int | None = None) -> None:
        super().__init__(depth=depth, seed=seed)
        #: Windows depend only on the board size, so they are built once per
        #: size and reused for every leaf.
        self._windows: dict[tuple[int, int], list[list[tuple[int, int]]]] = {}

    def evaluate(self, state: State, player: int) -> float:
        """Score open windows for ``player`` minus (weighted) those of the rival."""
        height, width = len(state), len(state[0])
        lines = self._windows.get((height, width))
        if lines is None:
            lines = self._windows[(height, width)] = windows(height, width)
        rival = other(player)
        score = 0.0
        for line in lines:
            mine = theirs = 0
            for r, c in line:
                cell = state[r][c]
                if cell == player:
                    mine += 1
                elif cell == rival:
                    theirs += 1
            if mine and not theirs:
                score += _WINDOW_SCORE.get(mine, 0.0)
            elif theirs and not mine:
                score -= _DEFENCE_WEIGHT * _WINDOW_SCORE.get(theirs, 0.0)
        centre = width // 2
        for row in state:
            cell = row[centre]
            if cell == player:
                score += _CENTRE_BONUS
            elif cell != EMPTY:
                score -= _CENTRE_BONUS
        return score
