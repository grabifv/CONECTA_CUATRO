// Conecta Cuatro Arena — shared helpers used by every screen
//
// DOM helpers, navigation, player identity, and the board renderer. Nothing
// here knows about a specific screen.
//
// Loaded as a plain script (not an ES module): the whole app shares one global
// namespace by design, and plain scripts keep working without a bundler.
"use strict";

/* ---------------- element helpers ---------------- */
const $ = (id) => document.getElementById(id);
const el = (tag, cls, txt) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (txt != null) e.textContent = txt;
  return e;
};

/* Defined up here because playerHtml() below needs it, and a `const` arrow is
   unusable until its own line has been evaluated. */
const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), 2200);
}

/* ---------------- navigation & theme ---------------- */
function showScreen(name) {
  for (const s of document.querySelectorAll(".screen")) s.classList.add("hidden");
  $(`screen-${name}`).classList.remove("hidden");
  // Mark the tab of the screen on show; the menu's own tiles share data-nav.
  for (const link of document.querySelectorAll(".nav [data-nav]")) {
    link.classList.toggle("active", link.dataset.nav === name);
  }
  if (name === "scoreboard") loadScoreboard();
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  $("theme-toggle").textContent = theme === "dark" ? "☀️" : "🌙";
}

function setupNav() {
  for (const btn of document.querySelectorAll("[data-nav]")) {
    btn.addEventListener("click", () => showScreen(btn.dataset.nav));
  }
  $("theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(next);
    try { localStorage.setItem("c4-theme", next); } catch {}
  });
  try {
    const saved = localStorage.getItem("c4-theme");
    if (saved) applyTheme(saved);
  } catch {}
}

/* ---------------- player identity ---------------- */
/* name -> {icon, authors, description}, keyed by KIND ("hard"), not roster entry
   ("hard_0"). Populated from the live registry on the Play screen and from the
   leaderboard's `players` block on the Scoreboard, which may not be the same set:
   a player can be removed from the repo after a tournament ran. */
const META = new Map();

const SUB_DIGITS = "₀₁₂₃₄₅₆₇₈₉";
/* Silhouette for a human seat; every bot supplies its own icon. */
const HUMAN_ICON = "👤";
/* Fallback when the leaderboard predates icons, or a kind is unknown. */
const BOT_ICON = "🤖";

/* Split a roster name into its kind and copy index: "hard_0" -> ["hard", "0"]. */
function splitPlayer(name) {
  const m = /^(.*)_(\d+)$/.exec(String(name));
  return m ? [m[1], m[2]] : [String(name), null];
}

function playerIcon(name) {
  const [kind] = splitPlayer(name);
  return META.get(kind)?.icon || BOT_ICON;
}

/* Plain-text label — for <option>, tooltips and anywhere markup is not allowed.
   Uses Unicode subscript digits, since <sub> cannot render inside <option>. */
function playerText(name) {
  const [kind, idx] = splitPlayer(name);
  const sub = idx == null ? "" : [...idx].map((d) => SUB_DIGITS[+d]).join("");
  return `${playerIcon(name)} ${kind}${sub}`;
}

/* HTML label — real <sub> markup, for everywhere else. */
function playerHtml(name) {
  const [kind, idx] = splitPlayer(name);
  return (
    `<span class="p-icon">${esc(playerIcon(name))}</span>` +
    `<span class="p-name">${esc(kind)}` +
    (idx == null ? "" : `<sub>${esc(idx)}</sub>`) +
    `</span>`
  );
}

/* Hard ceilings for a *playable* board. The renderer builds one element with
   listeners per cell, and the search behind the X-ray panel grows with the width,
   so an unbounded board freezes the tab. Rejected rather than silently clamped:
   quietly changing what someone typed is worse than telling them. */
const MIN_SIDE = 4;
const MAX_ROWS = 10;
const MAX_COLUMNS = 10;
const DEFAULT_SIZE = [6, 7];

/* The [row, column] where `after` differs from `before`: the piece just played. */
function newPiece(before, after) {
  if (!before || !after) return null;
  for (let r = 0; r < after.length; r++) {
    for (let c = 0; c < after[r].length; c++) {
      if (before[r][c] !== after[r][c]) return [r, c];
    }
  }
  return null;
}

/* Return the reason a rows x columns board is unplayable, or null if it is fine. */
function boardProblem(rows, columns) {
  if (!Number.isInteger(rows) || !Number.isInteger(columns)) {
    return "Las filas y las columnas tienen que ser números enteros.";
  }
  if (rows < MIN_SIDE || columns < MIN_SIDE) {
    return `El tablero necesita al menos ${MIN_SIDE} filas y ${MIN_SIDE} columnas.`;
  }
  if (rows > MAX_ROWS) return `Demasiadas filas: ${rows}. El máximo es ${MAX_ROWS}.`;
  if (columns > MAX_COLUMNS) {
    return `Demasiadas columnas: ${columns}. El máximo es ${MAX_COLUMNS}.`;
  }
  return null;
}

/* Draw a board into any container.
   Extracted from the Play screen so the Tournament page renders the identical
   board — same markup, same hover preview, same click semantics — without a
   second copy of it. `onPick` receives a column index; pass null for read-only.
   `line` is a list of [row, column] cells to highlight (the four in a row),
   `targetColumn` a column to outline (a hint), and `scores` one label per
   column (or null) shown above the board for the X-ray panel.
   `drop` is the [row, column] of the piece just played, which falls into place,
   and `ghost` (1 or 2) is the piece to preview where a hovered column would
   land it. */
function paintBoard(container, state, {
  onPick = null, line = null, targetColumn = -1, scores = null, drop = null, ghost = null,
} = {}) {
  container.innerHTML = "";
  const interactive = typeof onPick === "function";
  container.classList.toggle("locked", !interactive);
  const rows = state.length;
  const columns = rows ? state[0].length : 0;
  const winning = new Set((line || []).map(([r, c]) => `${r},${c}`));

  const grid = el("div", "c4-grid");
  grid.style.gridTemplateColumns = `repeat(${columns}, var(--cell))`;

  if (scores) {
    for (let c = 0; c < columns; c++) {
      grid.appendChild(el("div", "c4-score", scores[c] == null ? "" : String(scores[c])));
    }
  }

  const byColumn = Array.from({ length: columns }, () => []);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < columns; c++) {
      const cell = el("div", "cell");
      const piece = state[r][c];
      if (piece === 1) cell.classList.add("p1");
      if (piece === 2) cell.classList.add("p2");
      if (winning.has(`${r},${c}`)) cell.classList.add("win");
      if (c === targetColumn) cell.classList.add("target");
      if (drop && drop[0] === r && drop[1] === c) {
        cell.classList.add("drop");
        cell.style.setProperty("--fall", String(r));
      }
      byColumn[c].push(cell);
      grid.appendChild(cell);
    }
  }

  // Every cell of a column is a click target for that column: you drop a piece
  // into a column, not into a cell. Full columns are not clickable.
  if (interactive) {
    for (let c = 0; c < columns; c++) {
      if (state[0][c] !== 0) continue;
      // The lowest empty cell is where a piece would land: it shows the ghost.
      let landing = null;
      for (let r = rows - 1; r >= 0; r--) {
        if (state[r][c] === 0) { landing = byColumn[c][r]; break; }
      }
      const ghostClass = ghost ? `ghost-${ghost}` : null;
      for (const cell of byColumn[c]) {
        cell.classList.add("selectable");
        cell.addEventListener("mouseenter", () => {
          byColumn[c].forEach((x) => x.classList.add("preview"));
          if (ghostClass && landing) landing.classList.add(ghostClass);
        });
        cell.addEventListener("mouseleave", () => {
          byColumn[c].forEach((x) => x.classList.remove("preview"));
          if (ghostClass && landing) landing.classList.remove(ghostClass);
        });
        cell.addEventListener("click", () => onPick(c));
      }
    }
  }

  const labels = el("div", "c4-grid c4-labels");
  labels.style.gridTemplateColumns = `repeat(${columns}, var(--cell))`;
  for (let c = 0; c < columns; c++) labels.appendChild(el("div", "c4-label", String(c + 1)));

  container.appendChild(grid);
  container.appendChild(labels);
}
