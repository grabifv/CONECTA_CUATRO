"""Tests for the browser bridge — including the Tournament page's entrants.

``web/webglue.py`` is shipped code: it is what the page calls into for every rule
query and every AI move. Its forfeit handling matters especially, because the
browser enforces no timeout and a page must never be taken down by one bad player.
"""

from __future__ import annotations

import json

import pytest
import webglue

from conecta_cuatro import game
from conecta_cuatro.player import Player

#: The reference players that ship with the repository. ``players.yaml`` is an
#: open admission list, so the page may legitimately offer more than these — a
#: test may check that they are *present*, never that they are all there is.
REFERENCE_PLAYERS = {"random", "easy", "medium", "hard"}

EMPTY = json.dumps(game.new_board())


def board(*columns: int) -> str:
    state = game.new_board()
    for c in columns:
        state = game.apply_move(state, c)
    return json.dumps(state)


@pytest.fixture(autouse=True)
def loaded():
    """Load the real manifest once per test and start from a clean entrant table."""
    webglue.init(".")
    webglue.reset_entrants()
    yield
    webglue.reset_entrants()


class Boom(Player):
    """Raises instead of moving."""

    @classmethod
    def get_name(cls):
        return "boom"

    @classmethod
    def get_authors(cls):
        return ["tests"]

    @classmethod
    def get_description(cls):
        return "Always raises."

    @classmethod
    def get_icon(cls):
        return "💥"

    def choose_move(self, state):
        raise RuntimeError("kaboom")


class Cheat(Boom):
    """Returns a move that is never legal."""

    @classmethod
    def get_name(cls):
        return "cheat"

    def choose_move(self, state):
        return 99


# --------------------------------------------------------------------------- #
# Rules and identity                                                          #
# --------------------------------------------------------------------------- #

def test_players_json_carries_identity():
    entries = json.loads(webglue.players_json())
    assert REFERENCE_PLAYERS <= {e["name"] for e in entries}
    for e in entries:
        assert e["icon"].strip() and e["authors"] and e["description"].strip()


def test_rules_come_from_the_engine():
    assert json.loads(webglue.new_board(5, 6)) == game.new_board(5, 6)
    assert json.loads(webglue.legal_moves(EMPTY)) == list(range(7))
    after = json.loads(webglue.apply_move(EMPTY, "3"))
    assert after[-1][3] == 1
    assert webglue.is_terminal(EMPTY) is False
    assert webglue.is_terminal(board(0, 0, 1, 1, 2, 2, 3)) is True


def test_outcome_reports_the_winner_and_the_line():
    out = json.loads(webglue.outcome(board(0, 0, 1, 1, 2, 2, 3)))
    assert out["terminal"] is True and out["winner"] == 1
    assert out["line"] == [[5, 0], [5, 1], [5, 2], [5, 3]]
    out = json.loads(webglue.outcome(board(3)))
    assert out == {"terminal": False, "winner": None, "line": None, "to_move": 2}


def test_ask_move_refuses_a_terminal_board():
    with pytest.raises(ValueError, match="over"):
        webglue.ask_move("hard", board(0, 0, 1, 1, 2, 2, 3))


def test_ask_move_reports_a_column_and_its_reasoning():
    res = json.loads(webglue.ask_move("hard", board(0, 0, 1, 1, 2, 2)))
    assert res["move"] == 3
    assert res["elapsed_ms"] >= 0
    assert res["info"]["note"]


def test_analysis_finds_the_win_and_scores_every_column():
    an = json.loads(webglue.analysis(board(0, 0, 1, 1, 2, 2)))
    assert an["verdict"] == "win"
    assert an["best"] == 3
    assert len(an["scores"]) == 7 and all(s is not None for s in an["scores"])


def test_analysis_marks_full_columns_and_finished_games():
    an = json.loads(webglue.analysis(board(0, 0, 0, 0, 0, 0)))
    assert an["scores"][0] is None
    assert an["best"] != 0
    over = json.loads(webglue.analysis(board(0, 0, 1, 1, 2, 2, 3)))
    assert over["verdict"] == "over" and over["best"] is None


# --------------------------------------------------------------------------- #
# Tournament entrants                                                         #
# --------------------------------------------------------------------------- #

def test_the_same_kind_can_enter_twice_independently():
    webglue.create_entrant("a", "random", 1)
    webglue.create_entrant("b", "random", 2)
    assert webglue._ENTRANTS["a"] is not webglue._ENTRANTS["b"]


def test_an_unknown_entrant_says_what_to_do():
    with pytest.raises(KeyError, match="create_entrant"):
        webglue.entrant_move("nobody", EMPTY)


def test_reset_entrants_clears_the_table():
    webglue.create_entrant("a", "hard", 0)
    webglue.reset_entrants()
    assert not webglue._ENTRANTS


def test_play_auto_returns_a_complete_game():
    webglue.create_entrant("a", "hard", 0)
    webglue.create_entrant("b", "easy", 1)
    res = json.loads(webglue.play_auto("a", "b", EMPTY))
    assert res["result"] == "normal"
    # Replaying the moves must end the game, and the last mover must have won.
    state = game.new_board()
    for column in res["moves"]:
        state = game.apply_move(state, column)
    assert game.is_terminal(state)
    if res["winner_seat"] is None:
        assert game.is_draw(state)
    else:
        assert res["winner_seat"] == (len(res["moves"]) - 1) % 2


#: A real game that fills the board with no four-in-a-row.
DRAWN_GAME = [1, 4, 6, 6, 6, 0, 2, 0, 3, 6, 3, 3, 5, 3, 6, 1, 0, 3, 0, 4, 3,
              5, 0, 6, 5, 2, 2, 5, 1, 2, 2, 0, 2, 5, 4, 5, 4, 4, 4, 1, 1, 1]


def test_play_auto_reports_a_draw_as_no_winner():
    webglue.create_entrant("a", "random", 0)
    webglue.create_entrant("b", "random", 1)
    res = json.loads(webglue.play_auto("a", "b", board(*DRAWN_GAME[:-1])))
    assert res["result"] == "normal"
    assert res["winner_seat"] is None
    assert res["moves"] == [DRAWN_GAME[-1]]


def test_play_auto_is_reproducible_for_a_seed():
    def run():
        webglue.reset_entrants()
        webglue.create_entrant("a", "random", 7)
        webglue.create_entrant("b", "random", 8)
        return json.loads(webglue.play_auto("a", "b", EMPTY))["moves"]

    assert run() == run()


@pytest.mark.parametrize(
    ("cls", "expected"),
    [(Boom, "forfeit_error"), (Cheat, "forfeit_illegal")],
)
def test_a_misbehaving_entrant_forfeits_instead_of_breaking_the_page(cls, expected):
    webglue._ENTRANTS["bad"] = cls.create(seed=0)
    webglue.create_entrant("good", "hard", 0)
    res = json.loads(webglue.play_auto("bad", "good", EMPTY))
    assert res["result"] == expected
    assert res["winner_seat"] == 1, "the opponent wins"
    assert res["detail"]
