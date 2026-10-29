"""The `medium` player — difficulty level 2: real search, weak heuristic."""

from __future__ import annotations

from conecta_cuatro.bots import BasicMinimaxBot

#: Plies searched before the heuristic takes over. Deep enough to clearly beat
#: `easy`; what keeps `medium` well below `hard` is mostly what it knows at the
#: leaves (and one ply less).
DEPTH = 4


class Medium(BasicMinimaxBot):
    """Depth-4 minimax with alpha-beta and a centre-control heuristic."""

    @classmethod
    def get_name(cls) -> str:
        return "medium"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["builtin"]

    @classmethod
    def get_icon(cls) -> str:
        return "🧠"

    @classmethod
    def get_description(cls) -> str:
        return (
            f"Minimax with alpha-beta pruning, searching {DEPTH} plies and then "
            "guessing from how many of its pieces sit near the centre. Never "
            "misses what it can see, but builds no threats of its own."
        )

    @classmethod
    def create(cls, seed: int) -> Medium:
        return cls(depth=DEPTH, seed=seed)
