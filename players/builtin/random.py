"""The `random` player — difficulty level 0, the baseline."""

from __future__ import annotations

from conecta_cuatro.bots import RandomBot


class Random(RandomBot):
    """Picks a legal move uniformly at random."""

    @classmethod
    def get_name(cls) -> str:
        return "random"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["builtin"]

    @classmethod
    def get_icon(cls) -> str:
        return "🎲"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Drops its piece in a random column that still has room. No strategy "
            "at all — the baseline every other player has to beat."
        )
