# El torneo

El torneo enfrenta a **todos los jugadores registrados** entre sí y escribe un
archivo de resultados que la [página web](web.md) renderiza como marcador.

```mermaid
flowchart LR
    R["👥 Jugadores<br/>registrados"] --> T["⚔️ Enfrentamientos<br/>todos contra todos"]
    T --> G["🎮 Partidas<br/>con tiempo limitado"]
    G --> J["📊 leaderboard.json"]
```

Lo ejecutas tú con `conecta-cuatro-torneo`, y lo ejecuta una GitHub Action de forma
programada.

---

## Un «enfrentamiento» son muchas partidas

Dos jugadores no juegan una partida: juegan una **serie**. Para cada tablero
inicial, y con cada uno saliendo primero una vez, se juegan `--repetitions`
partidas.

```text
partidas de un enfrentamiento = nº de tableros × 2 × repeticiones
```

Con los valores por defecto (3 tableros, 3 repeticiones) son **18 partidas** por
pareja.

!!! info "Por qué se alterna quién sale primero"
    En el Conecta Cuatro el primer jugador tiene ventaja real (con juego
    perfecto, gana). Si no se alternara, el torneo mediría el sorteo en vez de
    la habilidad.

Los **tableros iniciales** por defecto son tres **aperturas** sobre el tablero
6×7: vacío, `3, 3` (las dos primeras fichas apiladas en el centro) y `0, 6`
(en las esquinas). Sin aperturas distintas, dos bots deterministas repetirían
siempre la misma partida.

!!! note "Los empates existen"
    Si el tablero se llena sin cuatro en línea, la partida es un **empate**:
    un punto para cada uno en la clasificación (la victoria vale tres) y medio
    resultado (0,5) para cada uno en el Elo. El `winner` de esa partida es la
    cadena vacía.

---

## Los tres formatos

| Formato | Emparejamientos | Clasificación |
|---------|-----------------|---------------|
| `simple` *(por defecto)* | todos contra todos, cada par una vez | puntos (3 por victoria, 1 por empate) |
| `league` | todos contra todos, cada par una vez | puntuación Elo |
| `championship` | fase de grupos + cuadro eliminatorio | puntos y un campeón |

Se elige con `--tournament`.

??? info "Detalle de `league` y `championship`"
    **`league`** usa el mismo todos contra todos que `simple`, pero ordena por
    una [puntuación Elo][conecta_cuatro.elo] actualizada partida a partida (K=32,
    inicio 1500). `--no-elo` vuelve a puntos.

    **`championship`** reparte a los jugadores en **grupos de cuatro**
    equilibrados; cada grupo juega un todos contra todos y sus **dos primeros
    pasan** a un cuadro de eliminación directa con cabezas de serie (con
    exenciones para los mejores cuando el número no es potencia de dos). Cada
    eliminatoria es un enfrentamiento completo; si acaba igualada, pasa el
    mejor cabeza de serie.

??? info "Por qué un jugador puede aparecer como `hard_0` y `hard_1`"
    Un tipo de jugador puede inscribirse **más de una vez**, cada copia con su
    propia semilla, que es lo que permite que un tipo compita contra *sí mismo*
    — un todos contra todos nunca empareja una instancia consigo misma. Las
    copias se llaman `<tipo>_<semilla>`, y el marcador renderiza ese sufijo como
    subíndice.

    Los jugadores de referencia entran **dos** veces y los enviados por PR
    **una**, porque el lado de las propuestas crece con cada PR fusionado y el
    trabajo crece con el cuadrado de la plantilla. `--player-repetition` lo
    sobrescribe.

---

## Robustez: un mal bot nunca rompe la ejecución

Incluso los bots bienintencionados pueden colgarse, romperse o devolver una
jugada ilegal en algún caso límite. El torneo sobrevive a todo ello:

| Fallo | Resultado |
|-------|-----------|
| supera su presupuesto de partida, o se cuelga | derrota (`forfeit_timeout`) |
| lanza una excepción jugando | derrota (`forfeit_error`) |
| devuelve una jugada ilegal o malformada | derrota (`forfeit_illegal`) |
| `create()` supera el presupuesto | derrota (`forfeit_build_timeout`) |
| `create()` lanza una excepción | derrota (`forfeit_build_error`) |

En todos los casos se registra el motivo y la ejecución **continúa**.

---

## Los tiempos

Cada jugador recibe **dos presupuestos por partida**, no por jugada:

| Presupuesto | Por defecto | Cubre |
|---|---|---|
| de partida (`--game-time-limit`) | 2 s | todo tu tiempo de pensar en esa partida, acumulado |
| de construcción (`--build-time-limit`) | 2 s | `create()` |

Son acumulativos: un bot puede quemar casi todo su presupuesto en una posición
difícil y jugar el resto al instante. Están separados para que no se pueda colar
precálculo gratis en el constructor.

!!! warning "El tiempo se mide en CI"
    El torneo oficial se ejecuta en los **runners de GitHub**, más lentos y
    variables que un portátil. Un bot que pasa en tu máquina todavía puede
    agotar el tiempo allí. Es una regla declarada, no una sorpresa.

??? info "Cómo se cumple el límite de verdad"
    Cada **partida** se ejecuta en un proceso aparte. Si un bot se cuelga en un
    bucle infinito, el proceso se **termina** y el bot pierde; el torneo sigue.
    Los hilos de Python no se pueden matar a la fuerza, así que un tiempo basado
    en hilos no podría garantizar esto.

    Se bifurca por partida y no por jugada a propósito: las cachés y la posición
    del generador aleatorio de un jugador tienen que sobrevivir de una jugada a
    la siguiente *dentro de su propia partida*.

    `--no-subprocess` da un modo de «tiempo blando» en un solo proceso para
    ejecuciones locales rápidas; sigue descalificando a quien se pase, pero no
    puede interrumpir un bucle infinito real.

---

## Ejecutarlo

```bash
# Lo habitual: torneo simple, escribe la clasificación
conecta-cuatro-torneo --out results/leaderboard.json

# Una liga ordenada por Elo
conecta-cuatro-torneo --tournament league

# Rápido, para probar tu bot mientras lo escribes
conecta-cuatro-torneo --no-subprocess
```

Las opciones que usarás casi siempre:

| Opción | Por defecto | Significado |
|--------|-------------|-------------|
| `--out` | — | dónde escribir el archivo de resultados |
| `--tournament` | `simple` | `simple`, `league` o `championship` |
| `--opening` | tres aperturas | un tablero inicial, como columnas ya jugadas (desde 0), p. ej. `--opening 3,3`; `--opening ''` es el vacío; repetible |
| `--rows` / `--columns` | `6` / `7` | tamaño del tablero |
| `--no-subprocess` | off | tiempo blando en un solo proceso (rápido, local) |

??? info "Todas las opciones"
    | Opción | Por defecto | Significado |
    |--------|-------------|-------------|
    | `--time-limit` | `2.0` | presupuesto por jugador en segundos, para una partida entera *y* para construir |
    | `--game-time-limit` | — | sobreescribe solo el presupuesto de pensar |
    | `--build-time-limit` | — | sobreescribe solo el de construcción |
    | `--no-time-limit` | off | no impone nada (nunca con jugadores no confiables) |
    | `--repetitions` | `3` | partidas por (tablero, quién sale primero) |
    | `--player-repetition` | *la de cada tipo* | sobrescribe las copias inscritas |
    | `--group-size` | `4` | solo campeonato: jugadores por grupo |
    | `--advance-per-group` | `2` | solo campeonato: cuántos pasan |
    | `--elo` / `--no-elo` | on | usar Elo para la clasificación de liga |

---

## Cómo se clasifica

`simple` y `championship` clasifican por **puntos** (3 por victoria, 1 por
empate); `league` clasifica por **Elo**. Las igualdades se rompen por **menos derrotas por
descalificación** y luego por **nombre**, de modo que el orden es completamente
determinista.

!!! note "El tiempo por jugada *no* desempata, a propósito"
    Premiaría lo que no toca: un jugador que pierde todas las partidas por
    descalificación no registra ningún tiempo de jugada, así que ganaría
    cualquier desempate por velocidad. Por eso las descalificaciones van
    primero.

### El orden esperado

Con suficientes partidas, los jugadores de referencia quedan así:

```text
⚔️ hard   >   🧠 medium   >   🌱 easy   >   🎲 random
```

- **`hard`** explora 5 niveles con poda alfa-beta y valora todas las líneas de
  cuatro abiertas de ambos jugadores. Fuerte, pero no entiende las amenazas a
  largo plazo, así que sigue siendo batible.
- **`medium`** explora 4 niveles con una heurística deliberadamente débil
  (fichas cerca del centro): nunca se pierde lo que ve, pero no construye
  amenazas propias.
- **`easy`** mira una sola jugada: gana si puede, tapa si debe y si no juega al
  centro. Le gana siempre a `random`, pero cae en cualquier doble amenaza.

!!! note "En `league`, los puntos y el puesto pueden discrepar"
    El puesto viene del Elo mientras la tabla también muestra puntos, así que un
    jugador con más puntos puede quedar *por debajo* de otro con menos. Eso es
    el Elo funcionando como debe: pondera *a quién* ganas, no solo cuántas
    veces.

---

**Siguiente:** [El marcador](scoreboard.md) — qué escribe el torneo y cómo se
convierte en la tabla que ves.
