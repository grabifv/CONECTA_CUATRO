# Conecta Cuatro Arena 🔴🟡

[![Tests](https://github.com/grabifv/CONECTA_CUATRO/actions/workflows/tests.yml/badge.svg)](https://github.com/grabifv/CONECTA_CUATRO/actions/workflows/tests.yml)
[![Tournament](https://github.com/grabifv/CONECTA_CUATRO/actions/workflows/tournament.yml/badge.svg)](https://github.com/grabifv/CONECTA_CUATRO/actions/workflows/tournament.yml)
[![Docs](https://readthedocs.org/projects/conecta-cuatro/badge/?version=latest)](https://conecta-cuatro.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

### ▶️ &nbsp;[**Jugar online**](https://grabifv.github.io/CONECTA_CUATRO) &nbsp;·&nbsp; 📚 &nbsp;[**Documentación**](https://conecta-cuatro.readthedocs.io) &nbsp;·&nbsp; 🚀 &nbsp;[**Envía tu propia IA**](https://conecta-cuatro.readthedocs.io/es/latest/game/upload-a-bot/submit-a-player/)

<sub>La documentación está en español e inglés: usa el selector de idioma de su cabecera.</sub>

---

Un proyecto completo construido sobre GitHub alrededor del **Conecta Cuatro**:

- 🐍 una **librería de Python**: un motor de juego parametrizado (cualquier
  tamaño de tablero), una API de jugador sencilla, una escalera de cuatro IA
  de referencia y un ejecutor de torneos robusto;
- ⌨️ un **juego por terminal**: Jugador vs Jugador, Jugador vs Bot y Bot vs
  Bot, con un **leaderboard** de victorias, derrotas y empates de cada persona
  y cada bot;
- 🌐 una **página web estática** —
  [**grabifv.github.io/CONECTA_CUATRO**](https://grabifv.github.io/CONECTA_CUATRO) —
  donde juegas contra una persona o contra cualquier IA, ejecutando *el mismo
  código Python* en el navegador gracias a **Pyodide**;
- 🏆 un **torneo automático** (GitHub Actions) que enfrenta a todas las IA y
  publica una [clasificación](results/leaderboard.json);
- 📚 **documentación** en español e inglés: el manual del juego (incluido cómo
  [enviar una IA nueva por Pull Request](https://conecta-cuatro.readthedocs.io/es/latest/game/upload-a-bot/submit-a-player/))
  y una **Guía** de Git, GitHub, empaquetado en Python, apps web y documentación.

Las reglas y las IA se escriben **una sola vez, en Python**, y ese mismo código
se ejecuta en el torneo (CI), en la terminal y en el navegador. Las reglas
**nunca** se reimplementan en JavaScript.

## El juego

Dos jugadores sueltan fichas por turnos en las columnas de una rejilla vertical
(6×7 por defecto); cada ficha cae a la casilla libre más baja. **Gana quien
primero alinee cuatro** en horizontal, vertical o diagonal. Si el tablero se
llena antes, es **empate**.

Reglas completas e ideas de estrategia en la
[documentación](https://conecta-cuatro.readthedocs.io/es/latest/game/rules/).

## Instalar y jugar en local

Requiere Python 3.10 o superior.

```bash
git clone https://github.com/grabifv/CONECTA_CUATRO
cd CONECTA_CUATRO
python -m venv .venv
.venv\Scripts\activate             # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"

# Jugar en la terminal (menú con los tres modos y el leaderboard)
conecta-cuatro

# Ejecutar las pruebas
pytest

# Ejecutar el torneo y escribir results/leaderboard.json
conecta-cuatro-torneo --out results/leaderboard.json
```

El leaderboard del juego por terminal se guarda en `leaderboard_local.json`
(git lo ignora). Los formatos de torneo, presupuestos de tiempo y
descalificaciones están en la
[documentación del torneo](https://conecta-cuatro.readthedocs.io/es/latest/game/advanced/tournament/).

Una partida rápida desde Python:

```python
from conecta_cuatro import game
from conecta_cuatro.manifest import load_players

reg = load_players()
hard, rnd = reg.get("hard"), reg.get("random")

state, players, turn = game.new_board(), [hard, rnd], 0
while not game.is_terminal(state):
    state = game.apply_move(state, players[turn].choose_move(state))
    turn = 1 - turn
print(game.render(state))
```

## La página web en local

La página carga el Python compartido con Pyodide. Ensambla los recursos y sirve
la carpeta:

```bash
python scripts/build_web.py          # copia el paquete y los jugadores a web/py.zip
python -m http.server -d web 8000    # abre http://localhost:8000
```

## Los jugadores de referencia

Una escalera de cuatro niveles, registrada en
[`players/builtin/players.yaml`](players/builtin/players.yaml). Cada uno es una
envoltura fina sobre una estrategia de
[`conecta_cuatro.bots`](src/conecta_cuatro/bots/).

| Nombre | Estrategia | Fuerza |
|--------|------------|--------|
| 🎲 `random` | columna legal al azar | la referencia base |
| 🌱 `easy` | mira una jugada: gana si puede, tapa si debe, si no juega al centro | gana siempre a `random` |
| 🧠 `medium` | minimax a 4 niveles, alfa-beta, heurística de control del centro | no se pierde lo que ve |
| ⚔️ `hard` | minimax a 5 niveles, alfa-beta, cuenta las líneas de cuatro abiertas | fuerte, pero no perfecto |

Medido: `hard` > `medium` > `easy` > `random`. **No hay jugador perfecto**: el
hueco de arriba de la escalera sigue abierto.

## Añade tu propia IA (por Pull Request)

1. Copia [`players/builtin/random.py`](players/builtin/random.py) a
   `players/custom/<tu_bot>.py`.
2. Hereda de [`Player`](src/conecta_cuatro/player.py), rellena `get_name` /
   `get_authors` / `get_description` / `get_icon` e implementa
   `choose_move(state) -> int` (la columna donde soltar la ficha).
3. Añade una entrada a
   [`players/custom/players.yaml`](players/custom/players.yaml): solo `file` y
   `class`.
4. Abre un PR: el CI ejecuta las pruebas. Un jugador que falla, se cuelga o
   repite un nombre existente no se fusiona.

Guía completa: [CONTRIBUTING.md](CONTRIBUTING.md) ·
[documentación](https://conecta-cuatro.readthedocs.io/es/latest/game/upload-a-bot/submit-a-player/).

## Estructura del repositorio

```
src/conecta_cuatro/        motor de juego, API de jugador, registro, manifiestos, torneo, juego por terminal
src/conecta_cuatro/bots/   estrategias reutilizables de los jugadores de referencia
players/builtin/           la escalera de referencia y su manifiesto
players/custom/            los jugadores enviados y su manifiesto
results/                   leaderboard.json, escrito por el workflow del torneo
web/                       sitio de GitHub Pages (Pyodide + JS fino)
docs/                      documentación de Read the Docs (MkDocs + Material), en español e inglés
tests/                     batería de pytest (y una prueba de arranque de la web con Node)
```

## Licencia

[MIT](LICENSE).
