// Headless smoke test for the web app: boot it exactly as the browser does,
// then drive the Tournament screen the way a user does.
//
// This exists because two bugs shipped that no Python test could see, and that
// looked identical from the outside — "the button does nothing":
//
//   * a duplicate element id, so the board was painted into a text input;
//   * `main()` throwing before the wiring ran, leaving buttons with no handler.
//
// Both are caught below. Run with `node tests/js/boot_test.js`.
"use strict";

const path = require("path");
const fs = require("fs");
const { buildDocument } = require("./domstub.js");

const ROOT = path.resolve(__dirname, "..", "..");
const WEB = path.join(ROOT, "web");

let failures = 0;
function check(label, ok, detail = "") {
  if (ok) console.log(`  ok   ${label}`);
  else { failures++; console.log(`  FAIL ${label}${detail ? " — " + detail : ""}`); }
}

/* ---------- environment ---------- */
const document = buildDocument(WEB);
global.document = document;
global.localStorage = { getItem: () => null, setItem: () => {} };
global.Event = class { constructor(t) { this.type = t; } };
// Node ≥21 defines navigator as a getter-only global; only define it if absent.
if (!globalThis.navigator) global.navigator = {};
global.history = { replaceState: () => {} };
global.location = { hash: "", origin: "http://localhost", pathname: "/" };

let pending = [];
global.setTimeout = (fn) => { pending.push(fn); return 0; };
global.clearTimeout = () => {};
const drain = () => {
  let guard = 0;
  while (pending.length && guard++ < 500) { const fns = pending; pending = []; fns.forEach((f) => f()); }
};

// Screens are fetched at boot; serve them from disk.
global.fetch = async (url) => {
  const file = path.join(WEB, url.split("?")[0]);
  if (!fs.existsSync(file)) return { ok: false, status: 404 };
  return { ok: true, status: 200, text: async () => fs.readFileSync(file, "utf8") };
};

// The engine, standing in for Pyodide. Same payload shapes webglue produces,
// with a small but real Connect Four rule set so games end the way they would.
const PLAYERS = [
  { name: "random", icon: "🎲", authors: ["builtin"], description: "Random column." },
  { name: "easy", icon: "🌱", authors: ["builtin"], description: "Wins, blocks, centre." },
  { name: "medium", icon: "🧠", authors: ["builtin"], description: "Depth-4 minimax." },
  { name: "hard", icon: "⚔️", authors: ["builtin"], description: "Depth-5 minimax." },
];
const newBoard = (rows, cols) => Array.from({ length: rows }, () => Array(cols).fill(0));
const toMove = (st) => {
  const n = st.flat().filter((x) => x !== 0).length;
  return n % 2 === 0 ? 1 : 2;
};
const lineAt = (st, r, c) => {
  const p = st[r][c];
  if (!p) return null;
  for (const [dr, dc] of [[0, 1], [1, 0], [1, 1], [1, -1]]) {
    const cells = [[r, c]];
    for (const s of [1, -1]) {
      let rr = r + dr * s, cc = c + dc * s;
      while (rr >= 0 && rr < st.length && cc >= 0 && cc < st[0].length && st[rr][cc] === p) {
        cells.push([rr, cc]); rr += dr * s; cc += dc * s;
      }
    }
    if (cells.length >= 4) return cells;
  }
  return null;
};
const outcome = (st) => {
  for (let r = 0; r < st.length; r++) {
    for (let c = 0; c < st[0].length; c++) {
      const line = lineAt(st, r, c);
      if (line) return { terminal: true, winner: st[r][c], line, to_move: toMove(st) };
    }
  }
  const full = st[0].every((x) => x !== 0);
  return { terminal: full, winner: null, line: null, to_move: toMove(st) };
};
const legalMoves = (st) => (outcome(st).terminal ? [] : st[0].flatMap((x, c) => (x === 0 ? [c] : [])));
const applyMove = (st, col) => {
  const s = st.map((row) => row.slice());
  for (let r = s.length - 1; r >= 0; r--) {
    if (s[r][col] === 0) { s[r][col] = toMove(st); return s; }
  }
  throw new Error(`column ${col} is full`);
};
let entrantCalls = 0;
global.window = {
  _handlers: {},
  addEventListener(ev, fn) { (this._handlers[ev] ||= []).push(fn); },
  bootEngine: async (onStatus) => { onStatus("Ready."); },
  C4: {
    players: () => PLAYERS,
    playerNames: () => PLAYERS.map((p) => p.name),
    newBoard,
    legalMoves,
    applyMove,
    isTerminal: (st) => outcome(st).terminal,
    outcome,
    askMove: (name, st) => ({ move: legalMoves(st)[0], elapsed_ms: 0.5, info: null }),
    analysis: (st) => ({
      scores: st[0].map((x) => (x === 0 ? 0 : null)),
      best: legalMoves(st)[0] ?? null,
      verdict: "unclear",
    }),
    resetEntrants: () => "ok",
    createEntrant: () => "ok",
    entrantMove: (id, st) => {
      entrantCalls++;
      return { move: legalMoves(st)[0], elapsed_ms: 0.5, info: null };
    },
    // A deterministic finish: both sides play the leftmost column with room.
    playAuto: (a, b, st) => {
      const moves = [];
      let s = st;
      while (!outcome(s).terminal) {
        const col = legalMoves(s)[0];
        moves.push(col);
        s = applyMove(s, col);
      }
      const won = outcome(s).winner != null;
      return { moves, winner_seat: won ? (moves.length - 1) % 2 : null,
               result: "normal", detail: "", elapsed_ms: [1, 1] };
    },
  },
};

/* ---------- load every screen script, in the order index.html does ----------
   Concatenated and evaluated once: separate <script> tags share one global
   scope, and evaluating each file separately here would not. */
const shell = fs.readFileSync(path.join(WEB, "index.html"), "utf8");
const scripts = [...shell.matchAll(/<script src="(js\/[^"]+)"><\/script>/g)].map((m) => m[1]);
if (scripts.length < 5) {
  console.log(`  FAIL index.html loads only ${scripts.length} screen scripts`);
  process.exit(1);
}
const app = {};
eval(
  scripts.map((rel) => fs.readFileSync(path.join(WEB, rel), "utf8")).join("\n;\n") +
  // `const` at the top of an eval is scoped to that eval, so hand out what the
  // assertions below need to poke at.
  "\n;Object.assign(app, { T, G, tHumanMove, newGame, humanMove });"
);

const $ = (id) => document.getElementById(id);
const cellsIn = (node) => node.querySelectorAll("cell").length;
const piecesIn = (node) =>
  node.querySelectorAll("p1").length + node.querySelectorAll("p2").length;

(async () => {
  console.log("boot");
  const dcl = window._handlers.DOMContentLoaded || [];
  check("index.html registers a DOMContentLoaded handler", dcl.length === 1);
  for (const fn of dcl) await fn();
  drain();

  check("no fatal banner", $("fatal").classList.contains("hidden"),
        $("fatal").innerHTML.replace(/<[^>]+>/g, " ").trim());
  check("boot overlay hidden", $("boot").classList.contains("hidden"));
  check("screens injected", $("screens").innerHTML.length > 500);
  check("no lookups for missing ids", document._missing.size === 0,
        [...document._missing].join(", "));

  console.log("\nwiring — every control a user can click must have a handler");
  for (const id of ["btn-new", "btn-hint", "btn-share", "btn-play-ai",
                    "t-start", "t-reset", "t-shuffle", "t-close-view",
                    "t-tl-first", "t-tl-prev", "t-tl-next", "t-tl-last"]) {
    check(`${id} is wired`, typeof $(id).onclick === "function");
  }

  console.log("\ntournament — all bots");
  check("slot list built", $("t-slots").children.length === 8);
  $("t-start").onclick();
  drain();
  check("bracket drawn", $("t-bracket").children.length === 3,
        `columns=${$("t-bracket").children.length}`);
  check("bracket visible", !$("t-bracket-wrap").classList.contains("hidden"));
  check("all matches played", /7 \/ 7/.test($("t-progress").textContent),
        $("t-progress").textContent);
  check("champion shown", !$("t-champion").classList.contains("hidden"));
  check("podium rendered", /podium-step/.test($("t-champion").innerHTML));

  console.log("\ntournament — replay a finished match");
  const firstTie = $("t-bracket").children[0].children[1]; // [0] is the round name
  check("finished match is clickable", typeof firstTie.onclick === "function");
  firstTie.onclick();
  check("match panel opens", !$("t-match").classList.contains("hidden"));
  check("timeline shown", !$("t-timeline").classList.contains("hidden"));
  $("t-tl-first").onclick();
  check("scrubbing to the start shows an empty board", cellsIn($("t-board")) === 42 &&
        piecesIn($("t-board")) === 0, `cells=${cellsIn($("t-board"))} pieces=${piecesIn($("t-board"))}`);
  $("t-tl-last").onclick();
  check("scrubbing to the end shows every piece", piecesIn($("t-board")) === 19,
        `pieces=${piecesIn($("t-board"))}`);
  check("the winning line is highlighted", $("t-board").querySelectorAll("win").length === 4);
  $("t-close-view").onclick();
  check("replay closes", $("t-match").classList.contains("hidden"));

  console.log("\ntournament — a human entrant gets somewhere to play");
  $("t-reset").onclick();
  $("t-size").value = "4";
  $("t-size").onchange();
  app.T.slots[0].kind = "__human__";
  app.T.slots[0].label = "Ada";
  [1, 2, 3].forEach((i) => { app.T.slots[i].kind = "hard"; });
  $("t-start").onclick();
  drain();
  check("bracket paused for the human", app.T.live !== null);
  check("match panel visible", !$("t-match").classList.contains("hidden"));
  check("board has clickable cells", $("t-board").querySelectorAll("selectable").length === 42,
        `selectable=${$("t-board").querySelectorAll("selectable").length}`);
  check("status names the human", /Ada/.test($("t-status").innerHTML));

  let n = 0;
  while (app.T.live && !app.T.game.over && n++ < 60) {
    const st = app.T.game.history[app.T.game.history.length - 1];
    app.tHumanMove(legalMoves(st)[0]);
    drain();
  }
  check("the bot replied", entrantCalls > 0, `entrantMove calls=${entrantCalls}`);
  check("human match recorded", app.T.rounds[0][0].done);
  drain();
  check("bracket ran to a champion", app.T.rounds.every((r) => r.every((m) => m.done)));
  check("champion panel shown", !$("t-champion").classList.contains("hidden"));

  console.log("\nplay screen still works after the split");
  app.newGame({ rows: 6, columns: 7 });
  check("board rendered", cellsIn($("board")) === 42, `cells=${cellsIn($("board"))}`);
  app.G.seats = ["Human", "Human"];
  app.newGame({ rows: 5, columns: 6 });
  check("board size follows the setup", cellsIn($("board")) === 30);
  for (const col of [0, 1, 0, 1, 0, 1, 0]) app.humanMove(col);
  check("game reaches a winner", app.G.gameOver === true && app.G.winnerSeat === 0);
  check("the winning line is highlighted", $("board").querySelectorAll("win").length === 4);
  check("the status announces it", /wins/.test($("status").innerHTML));

  console.log("\nplay screen — X-ray and a full board");
  app.newGame({ rows: 4, columns: 4 });
  $("toggle-xray").checked = true;
  $("toggle-xray").onchange({ target: $("toggle-xray") });
  check("X-ray scores are drawn", $("board").querySelectorAll("c4-score").length === 4);
  // A real 4x4 game that fills the board with no four in a row.
  for (const col of [3, 3, 0, 2, 3, 3, 1, 1, 1, 2, 0, 2, 0, 1, 2, 0]) app.humanMove(col);
  check("a full board is a draw", app.G.gameOver === true && app.G.winnerSeat === null,
        `over=${app.G.gameOver} winner=${app.G.winnerSeat}`);
  check("the status says draw", /Draw/.test($("status").innerHTML));

  console.log(`\n${failures ? "FAILED: " + failures + " check(s)" : "all checks passed"}`);
  process.exit(failures ? 1 : 0);
})();
