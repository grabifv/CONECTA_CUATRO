<div align="center">

# 🔴🟡 Conecta Cuatro

**Cuatro en línea en Python: juega contra personas o bots, enfrenta bots entre sí
y compite en una clasificación.**

[🌐 Jugar en el navegador](https://grabifv.github.io/CONECTA_CUATRO) ·
[📖 Documentación](docs/index.md) ·
[🤖 Crear un bot](#-crea-tu-propio-bot) ·
[🏆 Clasificación](results/leaderboard.json)

[![Tests](https://github.com/grabifv/CONECTA_CUATRO/actions/workflows/tests.yml/badge.svg)](https://github.com/grabifv/CONECTA_CUATRO/actions/workflows/tests.yml)
[![Torneo](https://github.com/grabifv/CONECTA_CUATRO/actions/workflows/tournament.yml/badge.svg)](https://github.com/grabifv/CONECTA_CUATRO/actions/workflows/tournament.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![Licencia MIT](https://img.shields.io/badge/licencia-MIT-green)](LICENSE)

</div>

```text
| . . . . . . . |
| . . . . . . . |
| . . . O . . . |      X = 🔴 empieza
| . . X X O . . |      O = 🟡
| . O X X X O . |
| O X O X X O . |      ¿dónde jugarías?
+---------------+
  1 2 3 4 5 6 7
```

## Índice

- [Qué puedes hacer](#-qué-puedes-hacer)
- [Empezar en 1 minuto](#-empezar-en-1-minuto)
- [El juego en la terminal](#-el-juego-en-la-terminal)
- [Los bots](#-los-bots)
- [Crea tu propio bot](#-crea-tu-propio-bot)
- [Torneos](#-torneos)
- [La web](#-la-web)
- [Cómo está organizado](#-cómo-está-organizado)
- [Desarrollo](#-desarrollo)

---

## ✨ Qué puedes hacer

| | Dónde | Qué |
|---|---|---|
| 👥 | terminal y web | **Persona contra persona** en el mismo ordenador |
| 🧑‍💻 | terminal y web | **Persona contra bot**, eligiendo el nivel |
| 🤖 | terminal y web | **Bot contra bot**, una o muchas partidas seguidas |
| 📊 | terminal | **Leaderboard** con victorias, derrotas y empates de cada persona y cada bot |
| 🏆 | GitHub Actions | **Torneo automático** entre todos los bots, con clasificación Elo |
| 🔍 | web | **Rayos X**: puntuación de cada columna y pistas mientras juegas |

Reglas: las fichas caen por la columna que eliges; gana quien alinee **cuatro**
en horizontal, vertical o diagonal; si el tablero se llena antes, es **empate**.
Más detalle e ideas de estrategia en [las reglas](docs/game/rules.md).

---

## 🚀 Empezar en 1 minuto

Solo necesitas **Python 3.10 o superior**.

```bash
git clone https://github.com/grabifv/CONECTA_CUATRO.git
cd CONECTA_CUATRO
python -m venv .venv
```

Activa el entorno:

| Windows | Linux / macOS |
|---|---|
| `.venv\Scripts\activate` | `source .venv/bin/activate` |

Instala y juega:

```bash
pip install -e .
conecta-cuatro
```

> ¿Sin instalar nada? Juega directamente en
> **[grabifv.github.io/CONECTA_CUATRO](https://grabifv.github.io/CONECTA_CUATRO)**.

---

## ⌨️ El juego en la terminal

`conecta-cuatro` (o `python -m conecta_cuatro`) abre este menú:

```text
===== CONECTA CUATRO =====
  1. Jugador vs Jugador
  2. Jugador vs Bot
  3. Bot vs Bot
  4. Ver leaderboard
  5. Salir
```

- Para jugar, escribe el **número de la columna** (1-7). Con `q` abandonas la
  partida, y las partidas abandonadas no cuentan.
- Al acabar una partida puedes pedir **revancha**; quien empieza se alterna.
- En **Bot vs Bot** eliges cuántas partidas se juegan y si quieres verlas
  jugada a jugada o solo el resultado final.

El **leaderboard** se guarda en `leaderboard_local.json` (no se sube a git: son
tus partidas) y se ordena por victorias:

```text
  #  Nombre                Tipo        V    D    E     % V
--------------------------------------------------------
  1  hard                  bot        12    1    2   80.0%
  2  Ana                   humano      5    3    1   55.6%
  3  medium                bot         4    6    3   30.8%
```

Personas y bots se cuentan por separado, así que una persona puede llamarse
igual que un bot sin mezclar sus resultados.

---

## 🤖 Los bots

Vienen cuatro, de menos a más fuerte:

| Bot | Cómo piensa | Tiempo por partida* |
|---|---|---|
| 🎲 **random** | elige una columna libre al azar | ~0 ms |
| 🌱 **easy** | mira una jugada: gana si puede, tapa si debe, si no juega al centro | ~4 ms |
| 🧠 **medium** | minimax a 4 jugadas con poda alfa-beta; valora tener fichas en el centro | ~20 ms |
| ⚔️ **hard** | minimax a 5 jugadas; cuenta las líneas de cuatro que siguen abiertas para cada jugador | ~300 ms |

<sub>* Medido en los servidores de GitHub durante el torneo.</sub>

Resultado del último torneo oficial (504 partidas, 0 descalificaciones):

```text
⚔️ hard   ≈ 1840 Elo   ████████████████████
🧠 medium ≈ 1735 Elo   ████████████████
🌱 easy   ≈ 1360 Elo   ███████
🎲 random ≈ 1065 Elo   █
```

Ninguno juega perfecto: **el primer puesto está libre** para el bot que lo
supere.

---

## 🛠️ Crea tu propio bot

Un bot es **una clase con un método**: recibe el tablero y devuelve la columna
donde jugar (empezando en 0).

```python
# players/custom/mi_bot.py
from conecta_cuatro import game
from conecta_cuatro.player import Player


class MiBot(Player):
    @classmethod
    def get_name(cls) -> str:
        return "mi-bot"                     # único entre todos los bots

    @classmethod
    def get_authors(cls) -> list[str]:
        return ["Tu nombre"]

    @classmethod
    def get_description(cls) -> str:
        return "Gana si puede; si no, juega lo más al centro posible."

    @classmethod
    def get_icon(cls) -> str:
        return "🦊"                         # un solo emoji

    def choose_move(self, state: game.State) -> int:
        columnas = game.legal_moves(state)
        for c in columnas:                  # ¿alguna jugada gana ya?
            if game.winner(game.apply_move(state, c)) is not None:
                return c
        centro = len(state[0]) // 2
        return min(columnas, key=lambda c: abs(c - centro))
```

Y dale de alta con una línea en
[`players/custom/players.yaml`](players/custom/players.yaml):

```yaml
players:
  - file: mi_bot.py
    class: MiBot
```

Listo: aparece en el menú de la terminal, en la web y en el torneo.

**Cómo es el tablero que recibes**

- `state` es una lista de filas, de **arriba abajo**; cada casilla vale `0`
  (vacía), `1` (`X`) o `2` (`O`).
- Tu ficha es `game.current_player(state)`.
- No modifiques `state` ni des por hecho que el tablero mide 6×7.

**Reglas del torneo para tu bot**

- Tienes **2 segundos para toda la partida**, no por jugada.
- Una columna llena o inexistente, una excepción o pasarte de tiempo te hacen
  **perder esa partida**, pero el torneo sigue.

¿Quieres ir más lejos? Puedes heredar de `MinimaxBot` y escribir solo tu función
de evaluación. Lo tienes explicado en la
[API del jugador](docs/game/upload-a-bot/player-api.md), y en
[enviar un jugador](docs/game/upload-a-bot/submit-a-player.md) está el proceso
de Pull Request.

---

## 🏆 Torneos

```bash
conecta-cuatro-torneo                            # todos contra todos, por puntos
conecta-cuatro-torneo --tournament league        # liga con Elo
conecta-cuatro-torneo --tournament championship  # grupos + eliminatorias
conecta-cuatro-torneo --opening 3,3 --opening '' # aperturas propias
conecta-cuatro-torneo --rows 7 --columns 8       # otro tamaño de tablero
```

- **Puntos:** victoria 3, empate 1, derrota 0. En el Elo, un empate cuenta como
  medio resultado para cada uno.
- **Partidas:** cada pareja juega desde tres aperturas (vacía, `3-3` y `0-6`),
  alternando quién empieza.
- **Seguridad:** cada partida corre en su propio proceso, así que un bot que se
  cuelga se corta y pierde, sin parar el torneo.
- **Automático:** en GitHub el torneo se repite en cada cambio de `main` y cada
  lunes, y propone la clasificación nueva en una Pull Request. Al fusionarla,
  la web se actualiza sola.

Todas las opciones: `conecta-cuatro-torneo --help` o la
[documentación del torneo](docs/game/advanced/tournament.md).

---

## 🌐 La web

La [web](https://grabifv.github.io/CONECTA_CUATRO) ejecuta **el mismo código
Python** que la terminal y el torneo, dentro del navegador gracias a
[Pyodide](https://pyodide.org). No hay servidor ni copia de las reglas en
JavaScript.

Tiene tablero de tamaño configurable, asientos para personas o cualquier bot,
rayos X, pistas, una línea de tiempo para repasar la partida, enlaces para
compartirla, cuadros de torneo propios y la clasificación oficial.

Para abrirla en local:

```bash
python scripts/build_web.py          # empaqueta el código Python en web/py.zip
python -m http.server -d web 8000    # http://localhost:8000
```

---

## 🗂️ Cómo está organizado

```text
CONECTA_CUATRO/
├── src/conecta_cuatro/
│   ├── game.py          reglas: tablero, jugadas, ganador, empate
│   ├── player.py        la clase Player que implementa cada bot
│   ├── cli.py           el juego en la terminal y su leaderboard
│   ├── tournament.py    torneos, tiempos y descalificaciones
│   ├── manifest.py      carga los bots desde players/*/players.yaml
│   ├── elo.py           cálculo del Elo
│   └── bots/            estrategias reutilizables (minimax, greedy, random)
├── players/
│   ├── builtin/         random, easy, medium, hard
│   └── custom/          ← aquí van los bots nuevos
├── web/                 la página (HTML + JS + puente a Python)
├── results/             clasificación oficial del torneo
├── docs/                documentación en español e inglés (MkDocs)
└── tests/               pruebas automáticas
```

---

## 🧪 Desarrollo

```bash
pip install -e ".[dev]"     # herramientas de desarrollo
pytest                      # pruebas
ruff check .                # estilo
mypy                        # tipos
```

Cada push y cada Pull Request pasan por GitHub Actions: pruebas en Python 3.10,
3.12 y 3.14, comprobación de los bots enviados, compilación de la documentación
y publicación de la web.

Para ver la documentación en local:

```bash
pip install -e ".[docs]"
mkdocs serve                # http://127.0.0.1:8000
```

---

<div align="center">

Hecho por [grabifv](https://github.com/grabifv) · [Licencia MIT](LICENSE)

</div>
