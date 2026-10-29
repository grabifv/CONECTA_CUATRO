"""Tests for the pure game engine."""

from __future__ import annotations

import pytest

from conecta_cuatro import game


def play(*columns: int, rows: int = 6, cols: int = 7) -> list[list[int]]:
    """Return the board after playing ``columns`` in order from an empty board."""
    state = game.new_board(rows, cols)
    for c in columns:
        state = game.apply_move(state, c)
    return state


def test_new_board_is_empty_and_sized():
    board = game.new_board()
    assert len(board) == game.DEFAULT_ROWS
    assert all(len(row) == game.DEFAULT_COLUMNS for row in board)
    assert game.count_pieces(board) == 0


@pytest.mark.parametrize(("rows", "cols"), [(3, 3), (0, 7), (2, 3)])
def test_a_board_too_small_for_four_is_rejected(rows, cols):
    with pytest.raises(ValueError):
        game.new_board(rows, cols)


def test_pieces_fall_to_the_bottom_and_stack():
    state = play(3, 3)
    assert state[-1][3] == game.PLAYER_1
    assert state[-2][3] == game.PLAYER_2
    assert game.count_pieces(state) == 2


def test_turns_alternate_from_the_board_alone():
    assert game.current_player(game.new_board()) == game.PLAYER_1
    assert game.current_player(play(0)) == game.PLAYER_2
    assert game.current_player(play(0, 1)) == game.PLAYER_1


def test_legal_moves_are_the_columns_with_room():
    assert game.legal_moves(game.new_board()) == list(range(7))
    full_first_column = play(0, 0, 0, 0, 0, 0)
    assert game.legal_moves(full_first_column) == [1, 2, 3, 4, 5, 6]


def test_is_legal_bounds_and_types():
    state = play(0, 0, 0, 0, 0, 0)
    assert game.is_legal(state, 1)
    assert not game.is_legal(state, 0)  # full
    assert not game.is_legal(state, -1)
    assert not game.is_legal(state, 7)
    assert not game.is_legal(state, "3")
    assert not game.is_legal(state, 3.0)
    assert not game.is_legal(state, True)  # a bool is not a column
    assert not game.is_legal(state, (3,))


def test_apply_move_returns_new_state_and_does_not_mutate():
    state = game.new_board()
    new = game.apply_move(state, 2)
    assert new[-1][2] == game.PLAYER_1
    assert state == game.new_board()  # original untouched
    assert new is not state
    assert all(a is not b for a, b in zip(new, state, strict=True))


def test_apply_illegal_move_raises():
    with pytest.raises(ValueError):
        game.apply_move(play(0, 0, 0, 0, 0, 0), 0)


@pytest.mark.parametrize(
    "moves",
    [
        (0, 0, 1, 1, 2, 2, 3),                    # horizontal, bottom row
        (0, 1, 0, 1, 0, 1, 0),                    # vertical
        (0, 1, 1, 2, 2, 3, 2, 3, 3, 6, 3),        # diagonal /
        (6, 5, 5, 4, 4, 3, 4, 3, 3, 0, 3),        # diagonal \
    ],
)
def test_four_in_a_row_wins_in_every_direction(moves):
    state = play(*moves)
    assert game.winner(state) == game.PLAYER_1
    assert game.is_terminal(state)
    line = game.winning_line(state)
    assert line is not None and len(line) >= 4
    assert game.legal_moves(state) == [], "no move after the game is won"
    assert not game.is_legal(state, 4)


def test_three_in_a_row_is_not_a_win():
    state = play(0, 0, 1, 1, 2, 2)
    assert game.winner(state) is None
    assert not game.is_terminal(state)


def test_the_winning_line_holds_the_winning_cells():
    state = play(0, 0, 1, 1, 2, 2, 3)
    assert game.winning_line(state) == [(5, 0), (5, 1), (5, 2), (5, 3)]
    assert game.line_through(state, 5, 0) == [(5, 0), (5, 1), (5, 2), (5, 3)]
    assert game.line_through(state, 4, 0) is None  # an O, part of no line


DRAWN_GAME = [1, 4, 6, 6, 6, 0, 2, 0, 3, 6, 3, 3, 5, 3, 6, 1, 0, 3, 0, 4, 3,
              5, 0, 6, 5, 2, 2, 5, 1, 2, 2, 0, 2, 5, 4, 5, 4, 4, 4, 1, 1, 1]


def test_a_full_board_with_no_line_is_a_draw():
    state = play(*DRAWN_GAME)
    assert game.is_full(state)
    assert game.is_draw(state)
    assert game.is_terminal(state)
    assert game.winner(state) is None
    assert game.legal_moves(state) == []


def test_a_full_game_always_terminates():
    state = game.new_board()
    turns = 0
    while not game.is_terminal(state):
        state = game.apply_move(state, game.legal_moves(state)[-1])
        turns += 1
        assert turns <= 42
    assert game.is_terminal(state)


def test_other_board_sizes_are_playable():
    state = play(0, 0, 1, 1, 2, 2, 3, rows=4, cols=5)
    assert game.winner(state) == game.PLAYER_1


def test_validate_state_accepts_reachable_boards():
    assert game.validate_state(play(3, 3, 4)) == play(3, 3, 4)
    as_tuples = tuple(tuple(r) for r in play(3))
    assert game.validate_state(as_tuples) == play(3)


@pytest.mark.parametrize(
    ("board", "reason"),
    [
        ([], "non-empty"),
        ([[0] * 7, [0] * 6] + [[0] * 7] * 4, "same number"),
        ([[0] * 7] * 5 + [[3, 0, 0, 0, 0, 0, 0]], "0, 1 or 2"),
        ([[1, 0, 0, 0, 0, 0, 0]] + [[0] * 7] * 5, "floating"),
        ([[0] * 7] * 5 + [[2, 0, 0, 0, 0, 0, 0]], "one more"),
        ([[0] * 7] * 5 + [[1, 1, 0, 0, 0, 0, 0]], "one more"),
    ],
)
def test_validate_state_explains_what_is_wrong(board, reason):
    with pytest.raises(ValueError, match=reason):
        game.validate_state(board)


def test_render_draws_pieces():
    text = game.render(play(3, 3))
    assert "X" in text and "O" in text
    assert text.splitlines()[-1].split() == [str(c) for c in range(1, 8)]
