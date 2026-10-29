# CONECTA_CUATRO

Conecta Cuatro por terminal, en Python 3.8+ y sin dependencias externas.

## Cómo jugar

```
python jugar.py
```

Modos disponibles:

1. **Jugador vs Jugador**: dos personas en el mismo ordenador.
2. **Jugador vs Bot**: contra cualquiera de los bots de `src/conecta_cuatro/bots/`.
3. **Bot vs Bot**: dos bots se enfrentan N partidas (alternando quién empieza).
4. **Torneo de bots**: todos los bots contra todos.
5. **Leaderboard**: victorias, derrotas y empates de cada persona y bot.

El leaderboard se guarda en `leaderboard.json`. Las partidas abandonadas no cuentan.

## Crear un bot

Crea un archivo en `src/conecta_cuatro/bots/`, por ejemplo `mi_bot.py`:

```python
from ..jugadores import Bot


class MiBot(Bot):
    nombre = "MiBot"  # nombre que aparece en el menú y en el leaderboard

    def elegir_columna(self, tablero, ficha):
        # tablero: copia del Tablero (puedes usar soltar/deshacer para probar jugadas)
        # ficha: 1 o 2, la ficha con la que juegas
        return tablero.columnas_validas()[0]  # columna 0..6
```

Se carga automáticamente al arrancar el juego. Si un bot devuelve una columna
inválida o lanza una excepción, pierde la partida. Tienes dos ejemplos:
`aleatorio.py` y `basico.py`.

Métodos útiles de `Tablero`: `columnas_validas()`, `soltar(col, ficha)`,
`deshacer()`, `ganador()`, `lleno()`, `celdas` (matriz filas x columnas, fila 0 arriba).
