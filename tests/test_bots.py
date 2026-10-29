"""Tests for the reusable strategies in :mod:`conecta_cuatro.bots`.

These cover the search engine and the heuristics directly, rather than through a
tournament, so a regression points at the responsible rule.
"""

from __future__ import annotations

import random

import pytest

from conecta_cuatro import game
from conecta_cuatro.bots import BasicMinimaxBot, GreedyBot, MinimaxBot, RandomBot, SmartMinimaxBot
from conecta_cuatro.bots.smart_minimax import windows


class _Meta:
    """Supplies the identity every concrete player must declare."""

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["tests"]

    @classmethod
    def get_description(cls) -> str:
        return f"Test subject {cls.__name__}."

    @classmethod
    def get_icon(cls) -> str:
        return "🧪"


class Plain(_Meta, MinimaxBot):
    pass


class Basic(_Meta, BasicMinimaxBot):
    pass


class Smart(_Meta, SmartMinimaxBot):
    pass


class Greedy(_Meta, GreedyBot):
    pass


class Rand(_Meta, RandomBot):
    pass


def play(*columns: int) -> list[list[int]]:
    state = game.new_board()
    for c in columns:
        state = game.apply_move(state, c)
    return state


#: X to move, and column 3 completes the bottom row.
X_WINS_AT_3 = play(0, 0, 1, 1, 2, 2)
#: O to move, and X threatens to complete the bottom row at column 3.
O_MUST_BLOCK_3 = play(0, 6, 1, 6, 2)


def random_positions(count: int, seed: int = 0) -> list[list[list[int]]]:
    """Non-terminal positions reached by random play, for property checks."""
    rng = random.Random(seed)
    found: list[list[list[int]]] = []
    while len(found) < count:
        state = game.new_board()
        for _ in range(rng.randrange(0, 30)):
            if game.is_terminal(state):
                break
            state = game.apply_move(state, rng.choice(game.legal_moves(state)))
        if not game.is_terminal(state):
            found.append(state)
    return found


# --------------------------------------------------------------------------- #
# The library classes stay abstract until a subclass names them                #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "cls", [MinimaxBot, BasicMinimaxBot, SmartMinimaxBot, GreedyBot, RandomBot]
)
def test_library_bots_cannot_be_entered_without_an_identity(cls):
    with pytest.raises(TypeError):
        cls()


# --------------------------------------------------------------------------- #
# Search engine                                                               #
# --------------------------------------------------------------------------- #

def test_depth_must_be_at_least_one():
    with pytest.raises(ValueError):
        Basic(depth=0)


def test_deeper_search_visits_more_nodes():
    """Regression guard for the `<= 0` cutoff: depth must actually bound the search."""
    shallow = Basic(depth=1)
    shallow.choose_move(game.new_board())
    deep = Basic(depth=4)
    deep.choose_move(game.new_board())
    assert shallow._nodes < deep._nodes


def test_alpha_beta_does_not_change_the_chosen_value():
    """Pruning is a speed optimisation; the root value must be identical."""
    board = play(3, 3, 2)
    pruned = Smart(depth=4, seed=0)
    pruned.choose_move(board)

    class NoPrune(Smart):
        def _negamax(self, board, player, depth, ply, alpha, beta):
            # Same recursion with the cutoff disabled.
            self._nodes += 1
            moves = [c for c in range(len(board[0])) if board[0][c] == game.EMPTY]
            if not moves:
                return self.DRAW
            if depth <= 0:
                return self.evaluate(board, player)
            best = -float("inf")
            for move in moves:
                row = self._drop(board, move, player)
                if game.line_through(board, row, move) is not None:
                    value = self.WIN - ply
                else:
                    value = -self._negamax(board, game.other(player), depth - 1, ply + 1,
                                           -float("inf"), float("inf"))
                self._lift(board, row, move)
                best = max(best, value)
            return best

    plain = NoPrune(depth=4, seed=0)
    plain.choose_move(board)
    assert pruned.last_info["score"] == plain.last_info["score"]
    assert pruned._nodes < plain._nodes, "pruning should visit fewer nodes"


@pytest.mark.parametrize("cls", [Plain, Basic, Smart])
def test_search_takes_an_immediate_win(cls):
    bot = cls(depth=2, seed=0)
    assert bot.choose_move(X_WINS_AT_3) == 3
    assert bot.last_info["score"] >= bot.WIN - bot.depth


@pytest.mark.parametrize("cls", [Plain, Basic, Smart])
def test_search_blocks_an_immediate_loss(cls):
    assert cls(depth=2, seed=0).choose_move(O_MUST_BLOCK_3) == 3


def test_search_prefers_the_quicker_win():
    """A win now beats a win later: the score is discounted by depth."""
    bot = Smart(depth=4, seed=0)
    assert bot.choose_move(X_WINS_AT_3) == 3
    assert bot.last_info["score"] == bot.WIN


def test_search_never_mutates_the_board_it_was_given():
    for state in random_positions(15):
        before = [list(row) for row in state]
        Smart(depth=3, seed=0).choose_move(state)
        assert state == before


def test_last_info_is_populated_for_the_web_panel():
    bot = Basic(depth=3, seed=0)
    bot.choose_move(game.new_board())
    info = bot.last_info
    assert {"player", "depth", "score", "nodes", "chosen", "note"} <= set(info)
    assert info["depth"] == 3
    assert info["nodes"] > 0


def test_search_refuses_a_terminal_board_loudly():
    with pytest.raises(ValueError):
        Smart(depth=2).choose_move(play(0, 0, 1, 1, 2, 2, 3))


# --------------------------------------------------------------------------- #
# Heuristics                                                                   #
# --------------------------------------------------------------------------- #

def test_a_standard_board_has_69_windows():
    """24 horizontal + 21 vertical + 12 + 12 diagonal lines of four."""
    assert len(windows(6, 7)) == 69


@pytest.mark.parametrize("cls", [Basic, Smart])
def test_heuristics_stay_inside_the_win_loss_band(cls):
    """A heuristic guess must never outrank a proven result."""
    bot = cls(depth=1, seed=0)
    for state in random_positions(40):
        for player in (game.PLAYER_1, game.PLAYER_2):
            assert bot.LOSS + 100 < bot.evaluate(state, player) < bot.WIN - 100


def test_smart_heuristic_values_an_open_three():
    bot = Smart(depth=1, seed=0)
    three = play(0, 6, 1, 6, 2, 5)  # X has three on the bottom row, open at column 3
    assert bot.evaluate(three, game.PLAYER_1) > 0
    assert bot.evaluate(three, game.PLAYER_2) < 0


def test_basic_heuristic_prefers_the_centre():
    bot = Basic(depth=1, seed=0)
    centre, edge = play(3), play(0)
    assert bot.evaluate(centre, game.PLAYER_1) > bot.evaluate(edge, game.PLAYER_1)


# --------------------------------------------------------------------------- #
# The simple strategies                                                       #
# --------------------------------------------------------------------------- #

def test_greedy_wins_blocks_and_otherwise_plays_the_centre():
    assert Greedy().choose_move(X_WINS_AT_3) == 3
    assert Greedy().choose_move(O_MUST_BLOCK_3) == 3
    assert Greedy().choose_move(game.new_board()) == 3


def test_greedy_refuses_a_terminal_board_loudly():
    """There is no legal move to return, so it must not invent one."""
    with pytest.raises(ValueError):
        Greedy().choose_move(play(0, 0, 1, 1, 2, 2, 3))


def test_random_only_returns_legal_moves():
    bot = Rand.create(seed=3)
    for state in random_positions(30):
        assert game.is_legal(state, bot.choose_move([list(r) for r in state]))
