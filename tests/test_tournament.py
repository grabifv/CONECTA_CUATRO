"""Tests for tournament robustness: timeouts, errors, illegal moves -> forfeits."""

from __future__ import annotations

import time

import pytest

from conecta_cuatro import game
from conecta_cuatro.player import Player
from conecta_cuatro.tournament import (
    BUILTIN_PLAYER_COPIES,
    CUSTOM_PLAYER_COPIES,
    POINTS_DRAW,
    UNLIMITED,
    Budgets,
    PlayerSpec,
    _fork_context,
    board_from_opening,
    build_roster,
    copies_for,
    main,
    play_match,
    run_tournament,
    validate_starting_states,
)

#: The tests that kill a hung player need fork(): without it the runner falls
#: back to soft, in-process budgets (by design), and an infinite loop would hang
#: the test run itself. They run in CI, on Linux.
requires_fork = pytest.mark.skipif(
    _fork_context() is None, reason="killing a hung player needs fork() (POSIX only)"
)

EMPTY = game.new_board()

#: A real game that fills the board with no four-in-a-row, minus its last move:
#: whatever goes in the one free column, the game is a draw.
DRAWN_GAME = [1, 4, 6, 6, 6, 0, 2, 0, 3, 6, 3, 3, 5, 3, 6, 1, 0, 3, 0, 4, 3,
              5, 0, 6, 5, 2, 2, 5, 1, 2, 2, 0, 2, 5, 4, 5, 4, 4, 4, 1, 1, 1]
ONE_MOVE_FROM_DRAW = board_from_opening(DRAWN_GAME[:-1])


class _Stub(Player):
    """Base for test players: derives the required identity from the class name.

    Keeps each stub below to just its ``choose_move``, which is the behaviour
    under test.
    """

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["tests"]

    @classmethod
    def get_description(cls) -> str:
        return f"Test stub {cls.__name__}."

    @classmethod
    def get_icon(cls) -> str:
        return "🧪"


class LeftBot(_Stub):
    """Always plays the leftmost column with room (legal, simple)."""

    def choose_move(self, state):
        return min(game.legal_moves(state))


class RightBot(_Stub):
    """Always plays the rightmost column with room (legal, distinct from LeftBot)."""

    def choose_move(self, state):
        return max(game.legal_moves(state))


class CrashBot(_Stub):
    def choose_move(self, state):
        raise RuntimeError("boom")


class CheatBot(_Stub):
    def choose_move(self, state):
        return 99  # illegal: no such column


class SlowBot(_Stub):
    def choose_move(self, state):
        while True:  # never returns -> must be killed by the subprocess timeout
            pass


def test_normal_game_has_a_winner():
    # Two LeftBots fill the columns left to right; the first player completes
    # four in a row along the bottom row when the fourth column starts.
    result = play_match(LeftBot(), LeftBot(), EMPTY, UNLIMITED)
    assert result.result == "normal"
    assert result.winner == result.player_first
    assert not result.is_draw


def test_a_full_board_with_no_line_is_a_draw():
    result = play_match(LeftBot(), RightBot(), ONE_MOVE_FROM_DRAW, UNLIMITED)
    assert result.result == "normal"
    assert result.is_draw
    assert result.winner == "" and result.loser == ""


def test_exception_forfeits_and_opponent_wins():
    result = play_match(CrashBot(), LeftBot(), EMPTY, UNLIMITED)
    assert result.result == "forfeit_error"
    assert result.winner == "LeftBot"


def test_illegal_move_forfeits():
    result = play_match(CheatBot(), LeftBot(), EMPTY, UNLIMITED)
    assert result.result == "forfeit_illegal"
    assert result.winner == "LeftBot"


@requires_fork
def test_hung_bot_is_killed_and_forfeits():
    # Uses the process-based hard timeout; the infinite loop must be terminated.
    result = play_match(SlowBot(), LeftBot(), EMPTY, Budgets(game_ms=300, build_ms=300))
    assert result.result == "forfeit_timeout"
    assert result.winner == "LeftBot"


def test_run_tournament_survives_a_bad_bot():
    players = [LeftBot(), CrashBot(), CheatBot()]
    lb = run_tournament(
        players, starting_states=[EMPTY], repetitions=1,
        budgets=UNLIMITED, use_subprocess=False,
    )
    # The run completes and produces standings for everyone despite bad bots.
    assert {r["player"] for r in lb["standings"]} == {"LeftBot", "CrashBot", "CheatBot"}
    good = next(r for r in lb["standings"] if r["player"] == "LeftBot")
    assert good["rank"] == 1


def test_draws_count_for_both_players():
    """A draw is a point each, and half a game each in the Elo rating."""
    lb = run_tournament(
        [LeftBot(), RightBot()], mode="league", starting_states=[ONE_MOVE_FROM_DRAW],
        repetitions=1, budgets=UNLIMITED, use_subprocess=False,
    )
    for row in lb["standings"]:
        assert (row["wins"], row["losses"], row["draws"]) == (0, 0, 2)
        assert row["points"] == 2 * POINTS_DRAW
        assert row["elo"] == pytest.approx(1500.0)
    assert lb["matches"][0]["draws"] == 2
    assert lb["matches"][0]["winner"] == ""
    assert lb["totals"]["draws"] == 2
    h2h = lb["player_stats"][0]["opponents"][0]
    assert (h2h["wins"], h2h["losses"], h2h["draws"]) == (0, 0, 2)


def test_build_roster_duplicates_each_kind_with_seed_suffixes():
    # A deterministic bot ignores the seed but is still duplicated so it faces itself.
    # Every count below is passed explicitly: these tests are about build_roster's
    # behaviour, not about whatever BUILTIN/CUSTOM_PLAYER_COPIES happen to be.
    roster = build_roster([LeftBot()], repetition=2)
    assert [p.name for p in roster] == ["LeftBot_0", "LeftBot_1"]


def test_build_roster_takes_a_per_kind_copy_count():
    """The count is per kind, and the caller decides it — see `copies_for`."""
    roster = build_roster([LeftBot(), RightBot()], repetition=1, copies={"RightBot": 3})
    assert [p.name for p in roster] == ["LeftBot_0", "RightBot_0", "RightBot_1", "RightBot_2"]


def test_build_roster_ignores_copies_for_kinds_not_entered():
    """A stale name in the mapping is harmless: only the given players are built."""
    roster = build_roster([LeftBot()], repetition=1, copies={"NotEntered": 5})
    assert [p.name for p in roster] == ["LeftBot_0"]


def test_build_roster_rejects_a_zero_copy_count():
    with pytest.raises(ValueError):
        build_roster([LeftBot()], copies={"LeftBot": 0})


def test_copies_follow_the_manifest_that_admitted_the_player():
    """Roster copies are a tournament decision, taken from a player's origin."""
    from conecta_cuatro.manifest import BUILTIN, CUSTOM
    from conecta_cuatro.registry import Registry

    reg = Registry()
    reg.register(LeftBot(), origin=BUILTIN)
    reg.register(RightBot(), origin=CUSTOM)
    assert copies_for(reg) == {
        "LeftBot": BUILTIN_PLAYER_COPIES,
        "RightBot": CUSTOM_PLAYER_COPIES,
    }


def test_build_roster_defaults_to_a_single_copy():
    """The default is a plain 1, independent of the policy constants."""
    assert [p.name for p in build_roster([LeftBot()])] == ["LeftBot_0"]


def test_build_roster_assigns_one_seed_per_copy():
    roster = build_roster([LeftBot()], repetition=3)
    assert [s.seed for s in roster] == [0, 1, 2]
    assert all(s.cls is LeftBot for s in roster)


def test_players_are_built_through_the_create_factory():
    """Construction must go through create(), and happen once per game."""
    built_with: list[int] = []

    class Recording(_Stub):
        @classmethod
        def create(cls, seed: int):
            built_with.append(seed)
            return cls()

        def choose_move(self, state):
            return min(game.legal_moves(state))

    # In-process, so the recording list is visible to the test.
    play_match(Recording(), LeftBot(), EMPTY, UNLIMITED, use_subprocess=False)
    assert built_with == [0], "create() should be called exactly once per game"


def test_build_roster_seeds_random_bots_reproducibly():
    from players.builtin.random import Random

    a, b = build_roster([Random.create(seed=0)], repetition=2)
    assert (a.name, a.seed) == ("random_0", 0)
    assert (b.name, b.seed) == ("random_1", 1)
    # A copy built from its spec behaves exactly like a fresh instance with that seed.
    assert a.cls.create(seed=a.seed).choose_move(game.new_board()) == (
        Random.create(seed=0).choose_move(game.new_board())
    )


def test_build_roster_respects_repetition_count():
    roster = build_roster([LeftBot()], repetition=3)
    assert [p.name for p in roster] == ["LeftBot_0", "LeftBot_1", "LeftBot_2"]


def test_build_roster_rejects_zero_repetition():
    with pytest.raises(ValueError):
        build_roster([LeftBot()], repetition=0)


def test_build_roster_lets_a_kind_play_itself():
    # Two seeded copies of the same kind are distinct opponents in the roster.
    roster = build_roster([LeftBot()], repetition=2)
    lb = run_tournament(
        roster, starting_states=[EMPTY], repetitions=1,
        budgets=UNLIMITED, use_subprocess=False,
    )
    assert {r["player"] for r in lb["standings"]} == {"LeftBot_0", "LeftBot_1"}
    # They played each other (both ways) -> one win and one loss each.
    assert all(r["games"] == 2 for r in lb["standings"])
    assert all((r["wins"], r["losses"]) == (1, 1) for r in lb["standings"])


def test_leaderboard_schema_shape():
    lb = run_tournament(
        [LeftBot(), CheatBot()],
        starting_states=[EMPTY],
        repetitions=2,
        budgets=UNLIMITED,
        use_subprocess=False,
        now=lambda: __import__("datetime").datetime(2026, 3, 1, 12, 0, 0),
    )
    assert lb["generated_at"] == "2026-03-01T12:00:00Z"
    assert lb["config"]["starting_states"] == [EMPTY]
    assert lb["config"]["tournament"] == "simple"
    assert lb["config"]["repetitions"] == 2
    for block in ("standings", "matches", "player_stats", "totals", "structure"):
        assert block in lb
    match = lb["matches"][0]
    assert set(match) >= {
        "player_a", "player_b", "phase", "games", "a_wins", "b_wins", "draws", "winner",
    }
    # One board, both first-mover orders, 2 reps -> 4 games in the single match.
    assert match["games"] == 4
    assert lb["totals"]["matches"] == 1 and lb["totals"]["players"] == 2
    assert {"wins", "losses", "draws", "points"} <= set(lb["standings"][0])


def test_timing_is_aggregated_and_never_per_move():
    """Timing ships as mean/std/max only — never a per-move array."""
    lb = run_tournament(
        [LeftBot(), RightBot()],
        starting_states=[EMPTY], repetitions=2,
        budgets=UNLIMITED, use_subprocess=False,
    )
    match = lb["matches"][0]
    for key in ("a_avg_move_ms", "b_avg_move_ms", "a_std_move_ms",
                "b_std_move_ms", "a_max_move_ms", "b_max_move_ms"):
        assert key in match, key
    assert "moves" not in match
    for row in lb["standings"]:
        assert {"avg_move_ms", "std_move_ms", "max_move_ms"} <= set(row)
    for row in lb["player_stats"]:
        assert {"avg_move_ms", "std_move_ms", "max_move_ms"} <= set(row)
    # Nothing anywhere in the payload carries a per-move log.
    assert "state_before" not in repr(lb)


def test_league_mode_ranks_by_elo():
    lb = run_tournament(
        [LeftBot(), CheatBot()],
        mode="league",
        starting_states=[EMPTY],
        repetitions=1,
        budgets=UNLIMITED,
        use_subprocess=False,
    )
    assert lb["config"]["tournament"] == "league"
    assert lb["config"]["elo"] is True
    assert all("elo" in row for row in lb["standings"])
    # LeftBot always beats CheatBot (illegal move) -> higher Elo, rank 1.
    top = lb["standings"][0]
    assert top["player"] == "LeftBot"
    assert top["elo"] > lb["standings"][1]["elo"]


def test_league_without_elo_falls_back_to_points():
    lb = run_tournament(
        [LeftBot(), CheatBot()],
        mode="league",
        elo=False,
        starting_states=[EMPTY],
        repetitions=1,
        budgets=UNLIMITED,
        use_subprocess=False,
    )
    assert lb["config"]["elo"] is False
    assert all("elo" not in row for row in lb["standings"])


def test_championship_builds_groups_and_bracket():
    # Four kinds x 2 copies = 8 players -> two groups of four, top two advance.
    roster = build_roster([LeftBot(), RightBot(), CheatBot(), CrashBot()], repetition=2)
    lb = run_tournament(
        roster,
        mode="championship",
        starting_states=[EMPTY],
        repetitions=1,
        budgets=UNLIMITED,
        use_subprocess=False,
    )
    structure = lb["structure"]
    assert structure["type"] == "championship"
    assert len(structure["groups"]) == 2
    assert all(len(g["advance"]) == 2 for g in structure["groups"])
    assert all("draws" in row for g in structure["groups"] for row in g["table"])
    bracket = structure["bracket"]
    assert bracket["rounds"], "expected at least one knockout round"
    assert bracket["champion"] in {p.name for p in roster}


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        run_tournament([LeftBot()], mode="bogus", use_subprocess=False)


# --------------------------------------------------------------------------- #
# Time budgets, hangs, and attribution                                         #
# --------------------------------------------------------------------------- #

class SlowBuildBot(_Stub):
    """Hangs while being constructed, not while playing."""

    def __init__(self):
        while True:
            pass

    def choose_move(self, state):
        return 0


class BadBuildBot(_Stub):
    """Raises while being constructed."""

    def __init__(self):
        raise RuntimeError("bad build")

    def choose_move(self, state):
        return 0


class GeneratorBot(_Stub):
    """Returns a single-use iterable instead of a column."""

    def choose_move(self, state):
        return (x for x in (0,))


class BoolBot(_Stub):
    """Returns ``True``: an ``int`` to Python, but not a column."""

    def choose_move(self, state):
        return True


class RenamerBot(_Stub):
    """Tries to rename itself mid-game."""

    def choose_move(self, state):
        self.name = "somethingElse"
        return min(game.legal_moves(state))


@requires_fork
def test_a_hung_constructor_is_attributed_to_its_own_player():
    """The build phase must be killable, and blamed on the player being built."""
    # Passed as a spec and never instantiated here: constructing it would hang the
    # test process itself. That is exactly why the child does the building.
    result = play_match(
        PlayerSpec(SlowBuildBot, 0, "SlowBuildBot"), LeftBot(), EMPTY,
        Budgets(game_ms=200, build_ms=200),
    )
    assert result.result == "forfeit_build_timeout"
    assert result.winner == "LeftBot"
    assert "SlowBuildBot" in result.detail


def test_a_raising_constructor_forfeits():
    result = play_match(PlayerSpec(BadBuildBot, 0, "BadBuildBot"), LeftBot(), EMPTY, UNLIMITED)
    assert result.result == "forfeit_build_error"
    assert result.winner == "LeftBot"


def test_build_time_is_measured_and_reported():
    result = play_match(LeftBot(), RightBot(), EMPTY, UNLIMITED)
    assert set(result.build_ms) == {"LeftBot", "RightBot"}
    assert all(v >= 0.0 for v in result.build_ms.values())


@pytest.mark.parametrize("cls", [GeneratorBot, BoolBot])
def test_a_move_that_is_not_a_column_forfeits_instead_of_crashing_the_run(cls):
    result = play_match(cls(), LeftBot(), EMPTY, UNLIMITED)
    assert result.result == "forfeit_illegal"
    assert result.winner == "LeftBot"
    # And it must not abort a whole run either.
    lb = run_tournament(
        [cls(), LeftBot()], starting_states=[EMPTY], repetitions=1,
        budgets=UNLIMITED, use_subprocess=False,
    )
    assert lb["totals"]["games"] == 2


def test_a_player_renaming_itself_cannot_corrupt_the_standings():
    """Regression: names came from the player, so a rename raised KeyError."""
    lb = run_tournament(
        [RenamerBot(), LeftBot()], starting_states=[EMPTY], repetitions=1,
        budgets=UNLIMITED, use_subprocess=False,
    )
    assert {r["player"] for r in lb["standings"]} == {"RenamerBot", "LeftBot"}


def test_a_player_cannot_corrupt_the_game_by_mutating_its_board():
    """Each move gets a fresh copy, so scribbling on it changes nothing."""

    class Vandal(_Stub):
        def choose_move(self, state):
            move = min(game.legal_moves(state))
            for row in state:
                row[:] = [1] * len(row)
            return move

    result = play_match(Vandal(), RightBot(), EMPTY, UNLIMITED, use_subprocess=False)
    assert result.result == "normal"


def test_game_budget_is_cumulative_across_moves_not_per_move():
    """A chess clock: many cheap moves must not each get the full budget."""

    class Dawdler(_Stub):
        def choose_move(self, state):
            time.sleep(0.05)
            return min(game.legal_moves(state))

    # Each move is well inside 120 ms, but three of them are not.
    result = play_match(
        Dawdler(), LeftBot(), EMPTY, Budgets(game_ms=120, build_ms=2000),
        use_subprocess=False,
    )
    assert result.result == "forfeit_timeout"
    assert result.winner == "LeftBot"
    assert "game budget" in result.detail


@requires_fork
def test_spent_time_survives_a_kill():
    """The orchestrator must recover per-player time even when the child is killed."""
    result = play_match(SlowBot(), LeftBot(), EMPTY, Budgets(game_ms=200, build_ms=200))
    assert result.result == "forfeit_timeout"
    assert set(result.spent_ms) == {"SlowBot", "LeftBot"}
    assert set(result.build_ms) == {"SlowBot", "LeftBot"}


def test_deadline_is_twice_the_budgets_plus_grace():
    b = Budgets(game_ms=1000, build_ms=500, grace_ms=250)
    assert b.deadline_ms == 2 * (1000 + 500) + 250
    assert UNLIMITED.deadline_ms is None


def test_player_state_survives_across_moves_in_one_game():
    """Fork-per-game, not per move: a counter must advance through the game."""

    class Counter(_Stub):
        def __init__(self):
            self.seen = 0

        def choose_move(self, state):
            self.seen += 1
            if self.seen > 1 and not self._ok:
                raise AssertionError("state was discarded between moves")
            self._ok = True
            return min(game.legal_moves(state))

        _ok = False

    result = play_match(Counter(), Counter(), EMPTY, Budgets())
    assert result.result == "normal"


def _signature(g):
    return tuple(m.move for m in g.moves if m.move is not None)


def test_repeated_games_differ_when_the_player_is_stochastic():
    """Repetitions must not be byte-identical."""
    from players.builtin.random import Random

    from conecta_cuatro.tournament import play_matchup

    mu = play_matchup(
        PlayerSpec(Random, 0, "random_0"),
        PlayerSpec(Random, 1, "random_1"),
        [EMPTY], repetitions=6, budgets=Budgets(),
    )
    signatures = {_signature(g) for g in mu.games}
    assert len(signatures) > 2, f"only {len(signatures)} distinct games out of {len(mu.games)}"


# --------------------------------------------------------------------------- #
# Input validation                                                             #
# --------------------------------------------------------------------------- #

def _floating() -> list[list[int]]:
    board = game.new_board()
    board[0][0] = 1  # a piece hanging in the air, nothing beneath it
    return board


def _too_many_for_player_two() -> list[list[int]]:
    board = game.new_board()
    board[-1][0] = 2
    return board


def _won() -> list[list[int]]:
    board = game.new_board()
    for c in range(4):
        board[-1][c] = 1
    for c in range(3):
        board[-2][c] = 2
    return board


@pytest.mark.parametrize(
    "boards",
    [[], [[]], [[[0, 0, 0]]], [[[0, "x", 0, 0]] * 4], [_floating()],
     [_too_many_for_player_two()], [_won()]],
)
def test_unplayable_boards_are_rejected(boards):
    with pytest.raises(ValueError):
        validate_starting_states(boards)


def test_valid_boards_are_returned_as_clean_lists():
    as_tuples = tuple(tuple(row) for row in ONE_MOVE_FROM_DRAW)
    cleaned = validate_starting_states([EMPTY, as_tuples])
    assert cleaned == [EMPTY, ONE_MOVE_FROM_DRAW]
    assert all(isinstance(row, list) for board in cleaned for row in board)


def test_an_opening_that_plays_a_full_column_is_rejected():
    with pytest.raises(ValueError, match="not playable"):
        board_from_opening([0] * 7)


def test_empty_roster_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        run_tournament([], use_subprocess=False)


def test_duplicate_roster_names_are_rejected():
    """Two same-named entries would collapse into one standings row."""
    with pytest.raises(ValueError, match="unique"):
        run_tournament(
            [LeftBot(), LeftBot()], starting_states=[EMPTY],
            repetitions=1, budgets=UNLIMITED, use_subprocess=False,
        )


def test_zero_repetitions_is_rejected():
    with pytest.raises(ValueError):
        run_tournament([LeftBot(), RightBot()], repetitions=0, use_subprocess=False)


@pytest.mark.parametrize(("group_size", "advance"), [(0, 2), (4, 0)])
def test_championship_rejects_degenerate_group_settings(group_size, advance):
    """group_size=0 used to raise ZeroDivisionError."""
    with pytest.raises(ValueError):
        run_tournament(
            build_roster([LeftBot(), RightBot()], repetition=1), mode="championship",
            starting_states=[EMPTY], repetitions=1, budgets=UNLIMITED,
            use_subprocess=False, group_size=group_size, advance_per_group=advance,
        )


def test_a_whole_run_is_reproducible_despite_varying_games():
    """Games within a match differ, yet the run repeats byte-for-byte."""
    from players.builtin.random import Random

    from conecta_cuatro.tournament import play_matchup

    def signatures():
        mu = play_matchup(
            PlayerSpec(Random, 0, "random_0"),
            PlayerSpec(Random, 1, "random_1"),
            [EMPTY], repetitions=4, budgets=UNLIMITED, use_subprocess=False,
        )
        return [_signature(g) for g in mu.games]

    first, second = signatures(), signatures()
    assert first == second, "the same match must replay identically"
    assert len(set(first)) > 2, "but its games must not be identical to each other"


# --------------------------------------------------------------------------- #
# Command line                                                                 #
# --------------------------------------------------------------------------- #

def test_cli_writes_a_leaderboard_with_openings_and_size(tmp_path, capsys):
    import json

    out = tmp_path / "lb.json"
    code = main([
        "--no-subprocess", "--repetitions", "1", "--rows", "5", "--columns", "6",
        "--opening", "", "--opening", "2,3", "--out", str(out),
    ])
    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["config"]["openings"] == [[], [2, 3]]
    assert all(len(b) == 5 and len(b[0]) == 6 for b in data["config"]["starting_states"])
    assert "Classification" in capsys.readouterr().out


def test_cli_rejects_a_bad_opening(tmp_path, capsys):
    code = main(["--no-subprocess", "--opening", "9", "--out", str(tmp_path / "x.json")])
    assert code == 1
    assert "not playable" in capsys.readouterr().err
