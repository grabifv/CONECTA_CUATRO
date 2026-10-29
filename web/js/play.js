// Conecta Cuatro Arena — the Play screen
//
// One free-form game: human or AI in either seat, X-ray, hints, move log,
// timeline scrubbing and shareable replay links.
//
// Loaded as a plain script (not an ES module): the whole app shares one global
// namespace by design, and plain scripts keep working without a bundler.
"use strict";

const HUMAN = "Human";

const G = {
  config: { rows: DEFAULT_SIZE[0], columns: DEFAULT_SIZE[1] },
  seats: [HUMAN, HUMAN], // seat 0 (first, X) and seat 1 (second, O)
  history: [], // states; history[0] is the start
  moves: [], // {seat, move: column, elapsed, info} for each transition
  cursor: 0, // which history index is shown
  gameOver: false,
  winnerSeat: null, // 0 or 1; null with gameOver === true is a draw
  line: null, // the four-in-a-row to highlight
  thinking: false,
  aiTimer: null,
  showXray: false,
  showWhy: true,
  delay: 600,
};

/* ---------------- setup / seats ---------------- */
/* Preferred default opponent, best first — the first one present is used. */
const DEFAULT_OPPONENTS = ["medium", "hard", "easy", "random"];

function populateSeatSelects() {
  const players = window.C4.players();
  for (const p of players) META.set(p.name, p);
  const names = players.map((p) => p.name);
  const preferred = DEFAULT_OPPONENTS.find((n) => names.includes(n));
  for (const i of [0, 1]) {
    const sel = $(`seat-${i}`);
    sel.innerHTML = "";
    for (const opt of [HUMAN, ...names]) {
      // <option> renders text only — no markup, no SVG — so the icon has to be a
      // glyph and the copy index a Unicode subscript.
      const o = el("option", null, opt === HUMAN ? `${HUMAN_ICON} ${HUMAN}` : playerText(opt));
      o.value = opt;
      const meta = META.get(opt);
      if (meta) o.title = `${meta.description}\nBy: ${meta.authors.join(", ")}`;
      sel.appendChild(o);
    }
    // Default: seat 0 Human, seat 1 a mid-strength bot so a first game is winnable.
    sel.value = i === 1 && preferred ? preferred : HUMAN;
    G.seats[i] = sel.value;
    sel.onchange = () => {
      G.seats[i] = sel.value;
      // Swapping a seat mid-game takes effect on the next turn.
      if (!G.gameOver && isLive()) maybeScheduleAI();
      render();
    };
  }
}

/* Parse the setup inputs. Returns null (after warning) if unplayable. */
function readConfig() {
  const rows = parseInt($("cfg-rows").value);
  const columns = parseInt($("cfg-cols").value);
  const problem = boardProblem(rows, columns);
  if (problem) {
    toast(problem);
    return null;
  }
  return { rows, columns };
}

/* ---------------- game lifecycle ---------------- */
function newGame(size, replayMoves) {
  const requested = size || readConfig();
  // readConfig() already explained why; a caller-supplied size still has to pass.
  if (!requested) return;
  if (size) {
    const problem = boardProblem(size.rows, size.columns);
    if (problem) {
      toast(problem);
      return;
    }
  }
  clearTimeout(G.aiTimer);
  G.config = { rows: requested.rows, columns: requested.columns };
  $("cfg-rows").value = G.config.rows;
  $("cfg-cols").value = G.config.columns;
  G.history = [window.C4.newBoard(G.config.rows, G.config.columns)];
  G.moves = [];
  G.cursor = 0;
  G.gameOver = false;
  G.winnerSeat = null;
  G.line = null;
  G.thinking = false;
  $("why").innerHTML = "";

  if (replayMoves && replayMoves.length) {
    for (const mv of replayMoves) {
      if (G.gameOver) break;
      if (!commitMove(mv, null)) break;
    }
    G.cursor = G.history.length - 1;
  }
  render();
  maybeScheduleAI();
}

const current = () => G.history[G.history.length - 1];
const shown = () => G.history[G.cursor];
const isLive = () => G.cursor === G.history.length - 1;
const seatToMove = () => (G.history.length - 1) % 2; // seat 0 moves first

function commitMove(move, meta) {
  const before = current();
  if (!window.C4.legalMoves(before).includes(move)) {
    toast(`Illegal move ${JSON.stringify(move)} — ignored.`);
    return false;
  }
  const seat = seatToMove();
  const after = window.C4.applyMove(before, move);
  G.history.push(after);
  G.moves.push({ seat, move, elapsed: meta?.elapsed ?? null, info: meta?.info ?? null });
  G.cursor = G.history.length - 1;
  logMove(G.moves[G.moves.length - 1]);

  const out = window.C4.outcome(after);
  if (out.terminal) {
    G.gameOver = true;
    // Only the player who just moved can have completed a line.
    G.winnerSeat = out.winner == null ? null : seat;
    G.line = out.line;
  }
  return true;
}

function humanMove(move) {
  if (G.gameOver || !isLive() || G.thinking) return;
  if (G.seats[seatToMove()] !== HUMAN) return;
  if (commitMove(move, null)) {
    render();
    maybeScheduleAI();
  }
}

function maybeScheduleAI() {
  clearTimeout(G.aiTimer);
  if (G.gameOver || !isLive() || G.thinking) return;
  const name = G.seats[seatToMove()];
  if (name === HUMAN) return;
  G.aiTimer = setTimeout(() => runAITurn(name), Math.max(0, G.delay));
}

function runAITurn(name) {
  if (G.gameOver || !isLive()) return;
  if (G.seats[seatToMove()] !== name) return; // seat was swapped
  G.thinking = true;
  render();
  try {
    const res = window.C4.askMove(name, current());
    G.thinking = false;
    if (!commitMove(res.move, res)) {
      toast(`${name} returned an illegal move — stopping.`);
      G.gameOver = true;
    }
  } catch (err) {
    G.thinking = false;
    G.gameOver = true;
    toast(`${name} crashed: ${err}`);
  }
  render();
  maybeScheduleAI();
}

/* ---------------- rendering ---------------- */
function render() {
  renderStatus();
  renderBoard();
  renderXray();
  renderTimeline();
  updateButtons();
}

const PIECE = ["🔴", "🟡"];

function seatLabel(i) {
  return `${PIECE[i]} Seat ${i + 1} (${G.seats[i]})`;
}

function resultText() {
  return G.winnerSeat == null
    ? "🤝 Draw — the board is full and nobody connected four."
    : `🎉 <strong>${seatLabel(G.winnerSeat)}</strong> wins — four in a row!`;
}

function renderStatus() {
  const st = $("status");
  if (!isLive()) {
    st.innerHTML = `⏳ Viewing move ${G.cursor} / ${G.moves.length}. ` +
      `<em>Return to the latest move to keep playing.</em>`;
    return;
  }
  if (G.gameOver) {
    st.innerHTML = resultText();
    return;
  }
  const seat = seatToMove();
  const who = G.seats[seat];
  const chip = seat === 0 ? "chip-a" : "chip-b";
  if (who === HUMAN) {
    st.innerHTML = `<span class="chip ${chip}">${seatLabel(seat)}</span> your turn — click a column to drop your piece.`;
  } else {
    st.innerHTML = `<span class="chip ${chip}">${seatLabel(seat)}</span> ${who} is ${G.thinking ? "thinking…" : "up next…"}`;
  }
}

/* The X-ray analysis of the live position, or null when it is not shown. */
function liveAnalysis() {
  if (!G.showXray || !isLive() || G.gameOver) return null;
  return window.C4.analysis(current());
}

function formatScore(score) {
  if (score == null) return null;
  if (score >= 9000) return "WIN";
  if (score <= -9000) return "LOSS";
  return String(Math.round(score));
}

function renderBoard() {
  const board = $("board");
  const state = shown();
  const interactive =
    isLive() && !G.gameOver && !G.thinking && G.seats[seatToMove()] === HUMAN;
  const an = liveAnalysis();

  paintBoard(board, state, {
    onPick: interactive ? humanMove : null,
    line: isLive() ? G.line : null,
    targetColumn: an && an.best != null ? an.best : -1,
    scores: an ? an.scores.map(formatScore) : null,
  });

  const old = board.parentElement.querySelector(".win-banner");
  if (old) old.remove();
  if (G.gameOver && isLive()) {
    const text = G.winnerSeat == null ? "🤝 Draw!" : `🏆 ${seatLabel(G.winnerSeat)} wins!`;
    board.after(el("div", "win-banner", text));
  }
}

function renderXray() {
  const box = $("xray");
  if (!G.showXray) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  if (!isLive()) {
    box.innerHTML = `<strong>X-ray:</strong> return to the latest move to analyse it.`;
    return;
  }
  if (G.gameOver) {
    box.innerHTML = `<strong>X-ray:</strong> the game is over.`;
    return;
  }
  const an = window.C4.analysis(current());
  const verdicts = {
    win: "the player to move can <strong>force a win</strong>",
    loss: "the player to move <strong>loses against best play</strong> (stall and hope!)",
    unclear: "no forced result in sight",
  };
  box.innerHTML =
    `<strong>X-ray:</strong> each column scored by a 5-ply search for the player to move ` +
    `(higher is better). Verdict: ${verdicts[an.verdict] || an.verdict}. ` +
    (an.best != null ? `Best column: <strong>${an.best + 1}</strong> (outlined).` : "");
}

function logMove(m) {
  if (!G.showWhy) return;
  const cls = m.seat === 0 ? "a" : "b";
  const entry = el("div", `why-entry ${cls}`);
  const head = el("div", "head");
  head.appendChild(el("span", null, `${seatLabel(m.seat)} · column ${m.move + 1}`));
  head.appendChild(el("span", "time", m.elapsed != null ? `${m.elapsed.toFixed(1)} ms` : "human"));
  entry.appendChild(head);
  if (m.info && m.info.note) {
    entry.appendChild(el("div", "note", m.info.note));
    const bits = [];
    if (m.info.depth != null) bits.push(`depth ${m.info.depth}`);
    if (m.info.score != null) bits.push(`score ${Number(m.info.score).toFixed(2)}`);
    if (m.info.nodes != null) bits.push(`${m.info.nodes} nodes`);
    if (bits.length) entry.appendChild(el("div", "note", bits.join(" · ")));
  }
  const body = $("why");
  body.insertBefore(entry, body.firstChild);
}

/* ---------------- timeline ---------------- */
function renderTimeline() {
  const slider = $("tl-slider");
  slider.max = G.history.length - 1;
  slider.value = G.cursor;
  $("tl-label").textContent = `move ${G.cursor} / ${G.history.length - 1}`;
}

function gotoCursor(idx) {
  G.cursor = Math.max(0, Math.min(G.history.length - 1, idx));
  clearTimeout(G.aiTimer);
  render();
  if (isLive()) maybeScheduleAI(); // returning to live resumes AI play
}

function setupTimeline() {
  $("tl-first").onclick = () => gotoCursor(0);
  $("tl-prev").onclick = () => gotoCursor(G.cursor - 1);
  $("tl-next").onclick = () => gotoCursor(G.cursor + 1);
  $("tl-last").onclick = () => gotoCursor(G.history.length - 1);
  $("tl-slider").oninput = (e) => gotoCursor(parseInt(e.target.value));
}

/* ---------------- buttons ---------------- */
function updateButtons() {
  const humanTurn = isLive() && !G.gameOver && G.seats[seatToMove()] === HUMAN;
  $("btn-hint").disabled = !humanTurn;
  const aiTurn = isLive() && !G.gameOver && G.seats[seatToMove()] !== HUMAN;
  $("btn-play-ai").disabled = !aiTurn;
}

function hint() {
  const an = window.C4.analysis(current());
  if (an.best == null) return;
  const why = {
    win: " — it forces a win!",
    loss: " — every column loses against best play, this one lasts longest.",
    unclear: ".",
  };
  toast(`Suggested: column ${an.best + 1}${why[an.verdict] || "."}`);
  paintBoard($("board"), current(), { onPick: humanMove, targetColumn: an.best });
  setTimeout(() => renderBoard(), 1500);
}

/* ---------------- share / replay ---------------- */
function shareLink() {
  const payload = {
    s: [G.config.rows, G.config.columns],
    seats: G.seats,
    m: G.moves.map((x) => x.move),
  };
  const hash = "#g=" + btoa(unescape(encodeURIComponent(JSON.stringify(payload))));
  const url = location.origin + location.pathname + hash;
  navigator.clipboard?.writeText(url).then(
    () => toast("Replay link copied to clipboard!"),
    () => toast("Copy failed — link is in the address bar."),
  );
  history.replaceState(null, "", hash);
}

function loadFromHash() {
  if (!location.hash.startsWith("#g=")) return false;
  try {
    const payload = JSON.parse(decodeURIComponent(escape(atob(location.hash.slice(3)))));
    for (const i of [0, 1]) {
      if (payload.seats?.[i]) {
        $(`seat-${i}`).value = payload.seats[i];
        G.seats[i] = payload.seats[i];
      }
    }
    const [rows, columns] = payload.s || DEFAULT_SIZE;
    newGame({ rows, columns }, payload.m || []);
    showScreen("game");
    toast("Loaded a shared replay.");
    return true;
  } catch (err) {
    toast("Could not read the shared link.");
    return false;
  }
}


/* ---------------- wiring ---------------- */
function setupPlay() {
  setupTimeline();
  $("btn-new").onclick = guard("New game", () => newGame());
  $("btn-hint").onclick = guard("Hint", hint);
  $("btn-share").onclick = guard("Share", shareLink);
  $("btn-play-ai").onclick = guard("Step", () => {
    clearTimeout(G.aiTimer);
    const name = G.seats[seatToMove()];
    if (name !== HUMAN) runAITurn(name);
  });
  $("cfg-delay").onchange = (e) => { G.delay = parseInt(e.target.value) || 0; };
  $("toggle-xray").onchange = guard("X-ray", (e) => { G.showXray = e.target.checked; render(); });
  $("toggle-why").onchange = (e) => { G.showWhy = e.target.checked; };
}
