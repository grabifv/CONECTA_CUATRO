# Reglas del juego

El Conecta Cuatro se juega en una **rejilla vertical**, de 6 filas por 7
columnas en el tablero estándar. Un jugador tiene las fichas `X` (rojas en la
web) y el otro las `O` (amarillas). Una posición se escribe como la lista de
filas, **de arriba abajo**:

```text
| . . . . . . . |    fila 0 (arriba)
| . . . . . . . |
| . . . . . . . |
| . . . O . . . |
| . . X X . . . |
| . O X X O . . |    fila 5 (abajo)
+---------------+
  1 2 3 4 5 6 7      columnas (en código, de 0 a 6)
```

---

## Cómo se juega

En cada turno, un jugador:

- elige **una columna** que no esté llena, y
- suelta en ella **una ficha**, que **cae** hasta la casilla libre más baja.

Los jugadores se alternan y **siempre empieza `X`**. **Gana quien primero
alinee cuatro fichas suyas** seguidas: en horizontal, en vertical o en
diagonal. Si el tablero se llena sin que nadie lo consiga, la partida es un
**empate**.

!!! example "Un turno"
    Le toca a `X` y suelta su ficha en la columna 5 (índice `4`):

    ```text
    antes                     después

    | . . . . . . . |         | . . . . . . . |
    | . . . . . . . |         | . . . . . . . |
    | . . . . . . . |         | . . . . . . . |
    | . . . O . . . |         | . . . O . . . |
    | . . X X . . . |         | . . X X X . . |
    | . O X X O . . |         | . O X X O . . |
    ```

    La ficha cae sobre la `O` de la columna 5. La jugada se escribe `4`: el
    índice de la columna, empezando en cero.

---

## Los cuatro conceptos

| Concepto | Cómo se representa | Ejemplo |
|---|---|---|
| **Posición** | lista de filas (de arriba abajo); cada casilla `0`, `1` o `2` | `[[0, 0, 0, 0, 0, 0, 0], …]` |
| **Jugada** | un entero: la columna | `3` |
| **Turno** | se deduce del tablero: juega `1` si hay tantas `1` como `2` | `game.current_player(state)` |
| **Final** | cuatro en línea, o tablero lleno (empate) | `game.is_terminal(state)` |

La partida termina en cuanto alguien hace cuatro en línea: solo puede haberlo
conseguido quien acaba de jugar. Si se llena el tablero sin línea, es empate.

!!! note "Tableros configurables"
    Tanto la página web como el juego en terminal y el torneo permiten elegir
    otro número de filas y columnas (como mínimo 4). El torneo juega por
    defecto en el tablero 6×7 desde tres **aperturas**: el tablero vacío, las
    dos primeras fichas apiladas en el centro (`3, 3`) y las dos primeras en
    las esquinas (`0, 6`).

---

## Ideas de estrategia

El Conecta Cuatro en 6×7 está **resuelto**: con juego perfecto, gana quien
empieza si abre en la columna central. Pero el juego perfecto necesita
buscar muy hondo; en la práctica se juega con unas pocas ideas:

| Idea | Por qué |
|---|---|
| **El centro vale más** | la columna central forma parte de más líneas de cuatro que ninguna otra |
| **Una amenaza** es tres en línea con la cuarta casilla libre | obliga al rival a taparla |
| **Dos amenazas a la vez** ganan | el rival solo puede tapar una |
| **No regales la casilla de debajo** | si tu rival amenaza en una casilla, no juegues justo debajo: le pondrías la ficha a su alcance |

!!! tip "Míralo en vivo"
    El **modo rayos X** de la [página web](advanced/web.md) puntúa cada columna
    con una búsqueda a 5 jugadas mientras juegas, y marca la que elegiría.

---

## Por qué las IA incluidas siguen siendo batibles

Ninguna de las cuatro IA que trae el proyecto juega perfecto. `hard` busca 5
jugadas por delante y valora las líneas abiertas de ambos jugadores, pero no
entiende las amenazas a largo plazo (qué amenazas quedan en filas pares o
impares cuando el tablero se va llenando), que es lo que decide las partidas
entre expertos.

Por eso se le puede ganar, y por eso hay hueco arriba de la escalera para un
jugador mejor.

---

**Siguiente:** [Primeros pasos](advanced/getting-started.md) — instala el paquete y juega
una partida. O ve directo a la [API de jugador](upload-a-bot/player-api.md) para
convertir estas ideas en código.
