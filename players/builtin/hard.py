"""The `hard` player — difficulty level 3: deeper search, real threat knowledge.

The same search as `medium`, one ply deeper and with a much better idea of
what it is looking at: it counts open lines (threats) for both players. Still not
perfect: see :mod:`conecta_cuatro.bots.smart_minimax` for what it does not
understand, and why that gap is deliberate.
"""

from __future__ import annotations

from conecta_cuatro.bots import SmartMinimaxBot

#: Plies searched before the heuristic takes over. Affordable at this depth only
#: because of alpha-beta pruning and centre-first move ordering: under 0.6 s for a
#: whole game on a laptop, well inside the tournament's 2 s budget. Odd on
#: purpose — measured against `medium`, depth 5 wins far more often than 6, whose
#: horizon ends on the opponent's move.
DEPTH = 5


class Hard(SmartMinimaxBot):
    """Depth-5 minimax with alpha-beta and a threat-counting heuristic."""

    @classmethod
    def get_name(cls) -> str:
        return "hard"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["builtin"]

    @classmethod
    def get_icon(cls) -> str:
        return "⚔️"

    @classmethod
    def get_description(cls) -> str:
        return (
            f"Minimax with alpha-beta pruning, searching {DEPTH} plies and then "
            "scoring every open line of four: two and three in a row with room to "
            "grow, for itself and against its rival. Strong, but blind to the "
            "long-term (odd/even row) threats experts play for."
        )

    @classmethod
    def create(cls, seed: int) -> Hard:
        return cls(depth=DEPTH, seed=seed)
