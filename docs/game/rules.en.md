# Game rules

Connect Four (*Conecta Cuatro*) is played on a **vertical grid**, 6 rows by 7
columns on the standard board. One player has the `X` pieces (red on the web
page) and the other the `O` pieces (yellow). A position is written as the list
of rows, **top to bottom**:

```text
| . . . . . . . |    row 0 (top)
| . . . . . . . |
| . . . . . . . |
| . . . O . . . |
| . . X X . . . |
| . O X X O . . |    row 5 (bottom)
+---------------+
  1 2 3 4 5 6 7      columns (0 to 6 in code)
```

---

## How to play

On each turn, a player:

- picks **one column** that is not full, and
- drops **one piece** into it, which **falls** to the lowest free cell.

Players alternate and **`X` always starts**. **The first to line up four of
their pieces** in a row — horizontally, vertically or diagonally — **wins**. If
the board fills up before anyone does, the game is a **draw**.

!!! example "One turn"
    It is `X`'s turn and they drop a piece into column 5 (index `4`):

    ```text
    before                    after

    | . . . . . . . |         | . . . . . . . |
    | . . . . . . . |         | . . . . . . . |
    | . . . . . . . |         | . . . . . . . |
    | . . . O . . . |         | . . . O . . . |
    | . . X X . . . |         | . . X X X . . |
    | . O X X O . . |         | . O X X O . . |
    ```

    The piece lands on the `O` in column 5. The move is written `4`: the
    column index, starting at zero.

---

## The four concepts

| Concept | How it is represented | Example |
|---|---|---|
| **Position** | list of rows (top to bottom); each cell `0`, `1` or `2` | `[[0, 0, 0, 0, 0, 0, 0], …]` |
| **Move** | an integer: the column | `3` |
| **Turn** | derived from the board: `1` moves when there are as many `1`s as `2`s | `game.current_player(state)` |
| **End** | four in a row, or a full board (draw) | `game.is_terminal(state)` |

The game ends as soon as someone makes four in a row: only the player who just
moved can have done it. If the board fills up with no line, it is a draw.

!!! note "Configurable boards"
    The web page, the terminal game and the tournament all let you choose a
    different number of rows and columns (at least 4). By default the
    tournament plays on the 6×7 board from three **openings**: the empty board,
    the first two pieces stacked in the centre (`3, 3`), and the first two in
    the corners (`0, 6`).

---

## Strategy ideas

Connect Four on 6×7 is **solved**: with perfect play, the first player wins by
opening in the centre column. But perfect play needs a very deep search; in
practice the game is played with a few ideas:

| Idea | Why |
|---|---|
| **The centre is worth more** | the centre column is part of more lines of four than any other |
| **A threat** is three in a row with the fourth cell free | it forces the rival to block it |
| **Two threats at once** win | the rival can only block one |
| **Do not give away the cell below** | if your rival threatens a cell, do not play right under it: you would bring it within reach |

!!! tip "See it live"
    The **X-ray mode** of the [web page](advanced/web.md) scores every column
    with a 5-ply search while you play, and outlines the one it would pick.

---

## Why the bundled AIs are still beatable

None of the four AIs that ship with the project plays perfectly. `hard`
searches 5 plies ahead and scores the open lines of both players, but it does
not understand long-term threats (which threats sit on odd or even rows as the
board fills up), which is what decides games between experts.

That is why it can be beaten, and why there is room at the top of the ladder
for a better player.

---

**Next:** [Getting started](advanced/getting-started.md) — install the package
and play a game. Or go straight to the [Player API](upload-a-bot/player-api.md)
to turn these ideas into code.
