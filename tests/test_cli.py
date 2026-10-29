"""Tests for the terminal game and its local leaderboard."""

from __future__ import annotations

import json

import pytest

from conecta_cuatro import game
from conecta_cuatro.cli import Leaderboard, Menu, Outcome, Seat, play_game
from conecta_cuatro.manifest import BUILTIN, BUILTIN_MANIFEST, load_players
from conecta_cuatro.player import Player
from conecta_cuatro.registry import Registry


def feeder(*answers: str):
    """Return a fake ``input`` that hands out ``answers`` in order, then EOF."""
    queue = list(answers)

    def read(prompt: str) -> str:
        if not queue:
            raise EOFError
        return queue.pop(0)

    return read


@pytest.fixture
def registry():
    return load_players({BUILTIN: BUILTIN_MANIFEST}, registry=Registry(), strict=True)


@pytest.fixture
def board(tmp_path):
    return Leaderboard(tmp_path / "lb.json")


class Cheat(Player):
    @classmethod
    def get_name(cls):
        return "cheat"

    @classmethod
    def get_authors(cls):
        return ["tests"]

    @classmethod
    def get_description(cls):
        return "Always column 99."

    @classmethod
    def get_icon(cls):
        return "🃏"

    def choose_move(self, state):
        return 99


def test_two_people_play_to_four_in_a_row():
    ana, luis = Seat("Ana"), Seat("Luis")
    outcome = play_game(ana, luis, show=False, read=feeder("1", "2", "1", "2", "1", "2", "1"))
    assert outcome.winner is ana and outcome.loser is luis
    assert outcome.reason == "cuatro en línea"


def test_a_bad_column_is_asked_again(capsys):
    ana, luis = Seat("Ana"), Seat("Luis")
    answers = feeder("9", "x", "1", "2", "1", "2", "1", "2", "1")
    assert play_game(ana, luis, show=False, read=answers).winner is ana
    assert capsys.readouterr().out.count("no válida") == 2


def test_quitting_abandons_the_game():
    outcome = play_game(Seat("Ana"), Seat("Luis"), show=False, read=feeder("1", "q"))
    assert outcome.reason == "abandono" and outcome.winner is None


def test_closed_input_abandons_instead_of_crashing():
    outcome = play_game(Seat("Ana"), Seat("Luis"), show=False, read=feeder("1"))
    assert outcome.reason == "abandono"


def test_a_cheating_bot_loses_on_the_spot():
    cheat, ana = Seat("cheat", Cheat()), Seat("Ana")
    outcome = play_game(cheat, ana, show=False, read=feeder())
    assert outcome.winner is ana and outcome.reason == "jugada inválida"


def test_bots_play_a_whole_game(registry):
    hard = Seat("hard", type(registry.get("hard")).create(seed=0))
    rnd = Seat("random", type(registry.get("random")).create(seed=0))
    outcome = play_game(hard, rnd, show=False, colour=False)
    assert outcome.winner is hard


def test_the_leaderboard_counts_wins_losses_and_draws(board, tmp_path):
    ana, bot = Seat("Ana"), Seat("hard", object())  # type: ignore[arg-type]
    board.record(Outcome(ana, bot, "cuatro en línea"), ana, bot)
    board.record(Outcome(None, None, "empate"), ana, bot)
    board.record(Outcome(None, None, "abandono"), ana, bot)  # not counted
    again = Leaderboard(tmp_path / "lb.json")  # reloaded from disk
    rows = {r["nombre"]: r for r in again.ranking()}
    assert (rows["Ana"]["victorias"], rows["Ana"]["derrotas"], rows["Ana"]["empates"]) == (1, 0, 1)
    assert (rows["hard"]["victorias"], rows["hard"]["derrotas"], rows["hard"]["empates"]) == (0, 1, 1)
    assert rows["hard"]["tipo"] == "bot"
    assert [r["nombre"] for r in again.ranking("humano")] == ["Ana"]
    assert "Ana" in again.render()


def test_a_person_and_a_bot_may_share_a_name(board):
    person, bot = Seat("hard"), Seat("hard", object())  # type: ignore[arg-type]
    board.record(Outcome(person, bot, "cuatro en línea"), person, bot)
    assert len(board.ranking()) == 2


def test_a_corrupt_leaderboard_file_starts_fresh(tmp_path, capsys):
    path = tmp_path / "lb.json"
    path.write_text("{not json", encoding="utf-8")
    assert Leaderboard(path).ranking() == []
    assert "Aviso" in capsys.readouterr().out


def test_menu_human_vs_human_records_the_winner(registry, board, capsys):
    read = feeder("1", "Ana", "Luis", "1", "2", "1", "2", "1", "2", "1", "n", "4", "1", "5")
    Menu(registry, board, read=read, colour=False).run()
    out = capsys.readouterr().out
    assert "¡Ana gana con cuatro en línea!" in out
    rows = {r["nombre"]: r for r in board.ranking()}
    assert rows["Ana"]["victorias"] == 1 and rows["Luis"]["derrotas"] == 1


def test_menu_bot_vs_bot_alternates_and_records_every_game(registry, board, capsys):
    names = [type(p).get_name() for p in registry.all()]
    hard, rnd = str(names.index("hard") + 1), str(names.index("random") + 1)
    read = feeder("3", hard, rnd, "4", "n", "5")
    Menu(registry, board, read=read, colour=False).run()
    assert "Resultado del enfrentamiento" in capsys.readouterr().out
    rows = {r["nombre"]: r for r in board.ranking()}
    assert rows["hard"]["victorias"] == 4
    assert rows["random"]["derrotas"] == 4


def test_menu_human_vs_bot_lets_the_person_play_and_quit(registry, board, capsys):
    names = [type(p).get_name() for p in registry.all()]
    rnd = str(names.index("random") + 1)
    read = feeder("2", "Ana", rnd, "s", "4", "q", "n", "5")
    Menu(registry, board, read=read, colour=False).run()
    out = capsys.readouterr().out
    assert "random (bot) juega en la columna" in out, "the bot replied to the person"
    assert "Ana abandona la partida." in out
    assert board.ranking() == [], "an abandoned game is not recorded"


def test_the_board_is_drawn_with_or_without_colour():
    state = game.apply_move(game.new_board(), 3)
    from conecta_cuatro.cli import draw_board

    assert "\033[" in draw_board(state, colour=True)
    assert "\033[" not in draw_board(state, colour=False)
    assert json.dumps(state)  # still a plain board
