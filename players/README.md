# `players/` — the admitted players

Every Conecta Cuatro Arena player is a single `.py` file that subclasses
[`conecta_cuatro.player.Player`](../src/conecta_cuatro/player.py) and is admitted through a
manifest. There are two directories, each with its own manifest:

| Directory | Manifest | Holds |
|-----------|----------|-------|
| [`builtin/`](builtin/) | [`builtin/players.yaml`](builtin/players.yaml) | the reference ladder that ships with the project |
| [`custom/`](custom/) | [`custom/players.yaml`](custom/players.yaml) | every player submitted by pull request |

A submission goes in `custom/` and touches nothing else, so two submissions never
collide in the same manifest and none of them can change the reference ladder.

A player file declares **identity and configuration**. The strategies themselves
are reusable and live in [`src/conecta_cuatro/bots/`](../src/conecta_cuatro/bots/), so
`hard.py` is a few lines of metadata plus a search depth rather than a search
implementation. You may do either: import a strategy and configure it, or write
your own `choose_move` from scratch.

## The reference ladder (ships with the project)

| File | Class | Name | Strategy |
|------|-------|------|----------|
| [`builtin/random.py`](builtin/random.py) | `Random` | 🎲 `random` | uniform random legal move — the baseline |
| [`builtin/easy.py`](builtin/easy.py) | `Easy` | 🌱 `easy` | one move ahead: wins, blocks, else plays the centre |
| [`builtin/medium.py`](builtin/medium.py) | `Medium` | 🧠 `medium` | depth-4 minimax, alpha-beta, centre-control heuristic |
| [`builtin/hard.py`](builtin/hard.py) | `Hard` | ⚔️ `hard` | depth-5 minimax, alpha-beta, open-lines (threat) heuristic |

Measured strength is `hard` > `medium` > `easy` > `random`, with clear margins
between every rung.

There is deliberately **no perfect player yet** — that is the open slot at the
top of the ladder.

## Add your own

Copy [`builtin/random.py`](builtin/random.py) into `custom/`, rename the class,
implement `choose_move`, add one entry to
[`custom/players.yaml`](custom/players.yaml), and open a Pull Request.

The step-by-step walkthrough, with the code to copy and the acceptance criteria,
is in the docs: **[Submit a player](https://conecta-cuatro.readthedocs.io/en/latest/en/game/upload-a-bot/submit-a-player/)**
(short version: [CONTRIBUTING.md](../CONTRIBUTING.md)).
