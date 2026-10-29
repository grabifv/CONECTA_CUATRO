"""The `easy` player — difficulty level 1, a one-move lookahead."""

from __future__ import annotations

from conecta_cuatro.bots import GreedyBot


class Easy(GreedyBot):
    """Wins if it can, blocks if it must, otherwise plays the centre."""

    @classmethod
    def get_name(cls) -> str:
        return "easy"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["builtin"]

    @classmethod
    def get_icon(cls) -> str:
        return "🌱"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Looks one move ahead: takes an immediate win, blocks an immediate "
            "loss, and otherwise plays as close to the centre as it can. Walks "
            "straight into any double threat."
        )
