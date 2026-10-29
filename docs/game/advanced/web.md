# La página web

La [página en vivo](https://grabifv.github.io/CONECTA_CUATRO) es un **sitio
estático** servido por GitHub Pages. Carga [Pyodide](https://pyodide.org)
(Python compilado a WebAssembly) y ejecuta **el mismo** motor de juego y los
mismos jugadores de IA en tu navegador.

!!! quote "Una única fuente de verdad"
    Las reglas y las IA vienen del Python compartido, ejecutado con Pyodide. Las
    reglas **nunca** se reimplementan en JavaScript. El trabajo de JavaScript es
    deliberadamente fino: dibujar el tablero, gestionar los clics, animar y
    llevar la línea temporal.

---

## Cómo carga

```mermaid
flowchart LR
    Z["🔨 build_web.py<br/>→ py.zip"] --> P["🐍 Pyodide<br/>arranca"]
    P --> U["📦 descomprime<br/>e importa"]
    U --> G["🔌 webglue.init()<br/>carga el registro"]
    G --> J["🖱️ window.C4.*<br/>lo llama el JS"]
```

1. `scripts/build_web.py` empaqueta la librería, todo el árbol `players/` y el
   puente `webglue.py` en `web/py.zip`.
2. En el navegador, `pyodide-bootstrap.js` arranca Pyodide, carga PyYAML,
   descarga `py.zip`, lo descomprime en el sistema de archivos virtual de
   Pyodide e importa `webglue`.
3. `webglue.init()` carga el manifiesto y rellena el registro.
4. Los scripts de la página llaman al puente (`window.C4.*`) para cada
   comprobación de reglas y cada jugada de la IA.

Todo cruza la frontera Python↔JS como **cadenas JSON**: el estado es una lista
de filas de enteros y una jugada es el número de columna. Nada de objetos
propios.

---

## Qué puedes hacer en ella

| | Funcionalidad | Qué hace |
|---|---|---|
| 🎛️ | **Tablero configurable** | número de filas y de columnas (de 4 a 10) |
| 👥 | **Elige cada asiento** | humano o cualquier IA registrada |
| 🔄 | **Cambiar de bot a mitad de partida** | surte efecto en la jugada siguiente, sin reiniciar |
| ⏯️ | **IA contra IA con ritmo** | un retardo configurable entre jugadas para poder seguirlas |
| ⏪ | **Repetición y viaje en el tiempo** | arrastra la línea temporal, avanza jugada a jugada, vuelve al estado en vivo |
| 🔍 | **Modo rayos X** | puntúa cada columna con una búsqueda a 5 jugadas y marca la mejor |
| 🧠 | **Panel «¿por qué ha hecho eso?»** | el razonamiento que publica la IA: profundidad, puntuación, nodos y tiempo |
| 💡 | **Modo pista** | sugiere una columna al asiento humano |
| 🏆 | **Página de torneo** | construye tu propio cuadro de 4, 8 o 16, con bots y personas mezclados |
| 🔗 | **Partida compartible** | el historial se codifica en la URL: compartes un enlace y se repite |

!!! info "El modo pista no es un bot"
    `webglue.analysis` busca 5 jugadas desde cada columna con la heurística de
    `hard`. No es juego perfecto: es una segunda opinión tan fuerte como el
    mejor jugador de referencia, que además te enseña la puntuación de cada
    columna.

!!! note "Empates en el cuadro del torneo"
    En la página de torneo cada eliminatoria es **una sola partida**. Si acaba
    en empate, pasa quien jugó **segundo**, porque salir primero es una
    ventaja.

---

## Lo que la página *no* hace

| No hay… | Por qué |
|---|---|
| **tiempos límite** | el juego en vivo es de mejor esfuerzo; los tiempos y las descalificaciones pertenecen al [torneo](tournament.md), que se ejecuta en CI |
| **backend, secretos ni servicios de pago** | todo es estático, más Pyodide, más un archivo JSON descargado |
| **botón de «ejecutar el torneo»** | dispararlo desde una página estática exigiría exponer un token en el navegador. Usa la interfaz «Run workflow» de GitHub |

---

## La pantalla del marcador

Descarga `leaderboard.json` (copiado junto a la página por la construcción) y
renderiza resultados producidos enteramente por el workflow del torneo. No se
juega ninguna partida para dibujarla: es renderizado puro de datos.

---

**Siguiente:** [El marcador](scoreboard.md) — la estructura del archivo que lee.
