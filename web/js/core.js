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
  if (name === "scoreboard") loadScoreboard();
}

function setupNav() {
  for (const btn of document.querySelectorAll("[data-nav]")) {
    btn.addEventListener("click", () => showScreen(btn.dataset.nav));
  }
  $("theme-toggle").addEventListener("click", () => {
    const root = document.documentElement;
    const next = root.dataset.theme === "light" ? "dark" : "light";
    root.dataset.theme = next;
    try { localStorage.setItem("c4-theme", next); } catch {}
  });
  try {
    const saved = localStorage.getItem("c4-theme");
    if (saved) document.documentElement.dataset.theme = saved;
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

/* Return the reason a rows x columns board is unplayable, or null if it is fine. */
function boardProblem(rows, columns) {
  if (!Number.isInteger(rows) || !Number.isInteger(columns)) {
    return "Rows and columns must be whole numbers.";
  }
  if (rows < MIN_SIDE || columns < MIN_SIDE) {
    return `A board needs at least ${MIN_SIDE} rows and ${MIN_SIDE} columns.`;
  }
  if (rows > MAX_ROWS) return `Too many rows: ${rows}. The maximum is ${MAX_ROWS}.`;
  if (columns > MAX_COLUMNS) {
    return `Too many columns: ${columns}. The maximum is ${MAX_COLUMNS}.`;
  }
  return null;
}

/* Draw a board into any container.
   Extracted from the Play screen so the Tournament page renders the identical
   board — same markup, same hover preview, same click semantics — without a
   second copy of it. `onPick` receives a column index; pass null for read-only.
   `line` is a list of [row, column] cells to highlight (the four in a row),
   `targetColumn` a column to outline (a hint), and `scores` one label per
   column (or null) shown above the board for the X-ray panel. */
function paintBoard(container, state, { onPick = null, line = null, targetColumn = -1, scores = null } = {}) {
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
      byColumn[c].push(cell);
      grid.appendChild(cell);
    }
  }

  // Every cell of a column is a click target for that column: you drop a piece
  // into a column, not into a cell. Full columns are not clickable.
  if (interactive) {
    for (let c = 0; c < columns; c++) {
      if (state[0][c] !== 0) continue;
      for (const cell of byColumn[c]) {
        cell.classList.add("selectable");
        cell.addEventListener("mouseenter", () => byColumn[c].forEach((x) => x.classList.add("preview")));
        cell.addEventListener("mouseleave", () => byColumn[c].forEach((x) => x.classList.remove("preview")));
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
