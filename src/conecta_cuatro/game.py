"""Parametrized Connect Four (Conecta Cuatro) game engine.

Two players take turns dropping a piece into a column of a vertical grid. The
piece falls to the lowest empty cell of that column. **The first player to line
up four of their pieces** — horizontally, vertically or diagonally — **wins**.
If the grid fills up with no four-in-a-row, the game is a **draw**.

Design rules honored by this module:

* The game **state** is a plain, JSON-serializable ``list[list[int]]``: a grid of
  ``rows`` lists, each of ``columns`` cells. ``state[0]`` is the **top** row and
  ``state[-1]`` the bottom one. A cell holds :data:`EMPTY` (``0``),
  :data:`PLAYER_1` (``1``) or :data:`PLAYER_2` (``2``). No custom objects ever
  cross the API boundary.
* A **move** is a plain ``int``: the index of the column to drop a piece into,
  ``0 <= column < columns``.
* **Whose turn it is** is derived from the board, never stored: player 1 always
  moves first, so it is player 1's turn whenever both have the same number of
  pieces on the board (see :func:`current_player`).
* Every function is **pure**: it never mutates its arguments. In particular
  :func:`apply_move` returns a brand-new state. This matters because minimax
  explores many hypothetical futures, and shared mutable state is a classic
  source of subtle bugs.

There is intentionally **no player identity in here** — the engine only knows
about boards, pieces and moves. Who plays which piece, timing and forfeits live
in the tournament (see :mod:`conecta_cuatro.tournament`).
"""

from __future__ import annotations

State = list[list[int]]
Move = int

#: An empty cell.
EMPTY = 0
#: The piece of the player who moves first.
PLAYER_1 = 1
#: The piece of the player who moves second.
PLAYER_2 = 2
#: Standard board height.
DEFAULT_ROWS = 6
#: Standard board width.
DEFAULT_COLUMNS = 7
#: Pieces in a row needed to win.
CONNECT = 4

#: The four line directions as ``(row step, column step)``: horizontal,
#: vertical, and the two diagonals. The opposite directions are covered by
#: walking each line both ways.
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


def new_board(rows: int = DEFAULT_ROWS, columns: int = DEFAULT_COLUMNS) -> State:
    """Return an empty board of ``rows`` x ``columns``.

    Raises:
        ValueError: if the board is too small to ever hold four in a row.
    """
    if rows < 1 or columns < 1 or max(rows, columns) < CONNECT:
        raise ValueError(f"a {rows}x{columns} board cannot hold {CONNECT} in a row")
    return [[EMPTY] * columns for _ in range(rows)]


def rows(state: State) -> int:
    """Return the number of rows of ``state``."""
    return len(state)


def columns(state: State) -> int:
    """Return the number of columns of ``state``."""
    return len(state[0]) if state else 0


def other(player: int) -> int:
    """Return the opponent's piece: ``1 -> 2`` and ``2 -> 1``."""
    return PLAYER_2 if player == PLAYER_1 else PLAYER_1


def count_pieces(state: State) -> int:
    """Return how many pieces are on the board."""
    return sum(1 for row in state for cell in row if cell != EMPTY)


def current_player(state: State) -> int:
    """Return the piece of the player whose turn it is (``1`` or ``2``).

    Player 1 always moves first, so it is player 1's turn whenever both
    players have placed the same number of pieces.
    """
    ones = sum(row.count(PLAYER_1) for row in state)
    twos = sum(row.count(PLAYER_2) for row in state)
    return PLAYER_1 if ones == twos else PLAYER_2


def legal_moves(state: State) -> list[Move]:
    """Return every column that can still take a piece, left to right.

    A column is playable while its **top** cell is empty. Empty if the board is
    already terminal (won or full).
    """
    if winner(state) is not None:
        return []
    return [c for c in range(columns(state)) if state[0][c] == EMPTY]


def is_legal(state: State, move: object) -> bool:
    """Return ``True`` if ``move`` is legal from ``state``.

    This is the single source of truth for "what is a legal move", used by the
    tournament to forfeit players that return illegal moves.

    ``move`` is deliberately typed ``object`` rather than :data:`Move`: its whole
    job is to judge what an *untrusted* player handed back, which may be any
    object at all. ``bool`` is rejected even though it is a subclass of ``int``:
    ``True`` is not a column.
    """
    if isinstance(move, bool) or not isinstance(move, int):
        return False
    if not 0 <= move < columns(state):
        return False
    if state[0][move] != EMPTY:
        return False
    return winner(state) is None


def landing_row(state: State, column: int) -> int | None:
    """Return the row a piece dropped into ``column`` would land on, or ``None``."""
    for row in range(rows(state) - 1, -1, -1):
        if state[row][column] == EMPTY:
            return row
    return None


def apply_move(state: State, move: Move) -> State:
    """Return a **new** state with the current player's piece dropped in ``move``.

    Does **not** mutate ``state``.

    Raises:
        ValueError: if ``move`` is not legal from ``state``.
    """
    if not is_legal(state, move):
        raise ValueError(f"Illegal move {move!r} for state {state!r}")
    row = landing_row(state, move)
    assert row is not None  # is_legal guarantees the column has room
    new_state = [list(r) for r in state]
    new_state[row][move] = current_player(state)
    return new_state


def line_through(state: State, row: int, column: int) -> list[tuple[int, int]] | None:
    """Return the cells of a four-in-a-row through ``(row, column)``, if any.

    Only the piece in that cell is considered. Used both to detect a win and to
    highlight the winning line in the web app.
    """
    piece = state[row][column]
    if piece == EMPTY:
        return None
    height, width = rows(state), columns(state)
    for dr, dc in DIRECTIONS:
        cells = [(row, column)]
        for sign in (1, -1):
            r, c = row + dr * sign, column + dc * sign
            while 0 <= r < height and 0 <= c < width and state[r][c] == piece:
                cells.append((r, c))
                r += dr * sign
                c += dc * sign
        if len(cells) >= CONNECT:
            return sorted(cells)
    return None


def winning_line(state: State) -> list[tuple[int, int]] | None:
    """Return the cells of the first four-in-a-row found on the board, or ``None``."""
    for r in range(rows(state)):
        for c in range(columns(state)):
            line = line_through(state, r, c)
            if line is not None:
                return line
    return None


def winner(state: State) -> int | None:
    """Return the piece (``1`` or ``2``) that has four in a row, or ``None``."""
    line = winning_line(state)
    if line is None:
        return None
    r, c = line[0]
    return state[r][c]


def is_full(state: State) -> bool:
    """Return ``True`` if no column can take another piece."""
    return all(cell != EMPTY for cell in state[0])


def is_terminal(state: State) -> bool:
    """Return ``True`` if the game is over: somebody won, or the board is full."""
    return winner(state) is not None or is_full(state)


def is_draw(state: State) -> bool:
    """Return ``True`` if the board is full and nobody has four in a row."""
    return is_full(state) and winner(state) is None


def validate_state(state: object) -> State:
    """Return ``state`` as a clean board, or explain why it is not a reachable one.

    Checks the shape, the cell values, gravity (no piece floats above an empty
    cell), and the piece counts (player 1 moves first, so it has as many pieces
    as player 2 or exactly one more).

    Raises:
        ValueError: describing the first problem found.
    """
    if not isinstance(state, (list, tuple)) or not state:
        raise ValueError("a board must be a non-empty list of rows")
    grid = [list(row) if isinstance(row, (list, tuple)) else row for row in state]
    if not all(isinstance(row, list) and row for row in grid):
        raise ValueError("every row must be a non-empty list of cells")
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        raise ValueError("every row must have the same number of columns")
    if max(len(grid), width) < CONNECT:
        raise ValueError(f"a {len(grid)}x{width} board cannot hold {CONNECT} in a row")
    for row in grid:
        for cell in row:
            if isinstance(cell, bool) or cell not in (EMPTY, PLAYER_1, PLAYER_2):
                raise ValueError(f"cells must be 0, 1 or 2, got {cell!r}")
    for c in range(width):
        seen_piece = False
        for r in range(len(grid)):
            if grid[r][c] != EMPTY:
                seen_piece = True
            elif seen_piece:
                raise ValueError(f"column {c} has a piece floating above an empty cell")
    ones = sum(row.count(PLAYER_1) for row in grid)
    twos = sum(row.count(PLAYER_2) for row in grid)
    if ones - twos not in (0, 1):
        raise ValueError(
            f"player 1 moves first, so it must have as many pieces as player 2 or "
            f"one more; got {ones} and {twos}"
        )
    return grid


def render(state: State) -> str:
    """Return a plain-text drawing of ``state`` (``X`` = player 1, ``O`` = player 2)."""
    symbols = {EMPTY: ".", PLAYER_1: "X", PLAYER_2: "O"}
    lines = ["| " + " ".join(symbols[cell] for cell in row) + " |" for row in state]
    lines.append("+" + "-" * (columns(state) * 2 + 1) + "+")
    lines.append("  " + " ".join(str(c + 1) for c in range(columns(state))))
    return "\n".join(lines)
