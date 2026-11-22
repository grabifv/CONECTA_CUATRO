"""Inés's depth-4 minimax player for Conecta Cuatro."""

from __future__ import annotations

from conecta_cuatro.bots import SmartMinimaxBot

DEPTH = 4


class Ines(SmartMinimaxBot):
    """Search four plies ahead and evaluate open lines and centre control."""

    @classmethod
    def get_name(cls) -> str:
        return "ines"

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Inés"]

    @classmethod
    def get_description(cls) -> str:
        return (
            f"Minimax de profundidad {DEPTH}: busca líneas de cuatro abiertas "
            "y favorece el control del centro."
        )

    @classmethod
    def get_icon(cls) -> str:
        return "🐙"

    @classmethod
    def create(cls, seed: int) -> Ines:
        return cls(depth=DEPTH, seed=seed)
