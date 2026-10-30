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
  justMoved: false, // animate the next render's newest piece
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
      const o = el("option", null, opt === HUMAN ? `${HUMAN_ICON} Persona` : playerText(opt));
      o.value = opt;
      const meta = META.get(opt);
      if (meta) o.title = `${meta.description}\nAutoría: ${meta.authors.join(", ")}`;
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
  G.justMoved = false;
  $("why").innerHTML = "";

  if (replayMoves && replayMoves.length) {
    for (const mv of replayMoves) {
      if (G.gameOver) break;
      if (!commitMove(mv, null)) break;
    }
    G.cursor = G.history.length - 1;
    G.justMoved = false; // a loaded replay appears at once
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
    toast(`Jugada no válida (${JSON.stringify(move)}): se ignora.`);
    return false;
  }
  const seat = seatToMove();
  const after = window.C4.applyMove(before, move);
  G.history.push(after);
  G.moves.push({ seat, move, elapsed: meta?.elapsed ?? null, info: meta?.info ?? null });
  G.cursor = G.history.length - 1;
  G.justMoved = true;
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
      toast(`${name} ha devuelto una jugada no válida: partida detenida.`);
      G.gameOver = true;
    }
  } catch (err) {
    G.thinking = false;
    G.gameOver = true;
    toast(`${name} ha fallado: ${err}`);
  }
  render();
  maybeScheduleAI();
}

/* ---------------- rendering ---------------- */
function render() {
  renderStatus();
  renderTurns();
  renderBoard();
  renderXray();
  renderTimeline();
  updateButtons();
}

const PIECE = ["🔴", "🟡"];

function seatName(i) {
  return G.seats[i] === HUMAN ? `Jugador ${i + 1}` : G.seats[i];
}

function seatLabel(i) {
  return `${PIECE[i]} ${seatName(i)}`;
}

function resultText() {
  return G.winnerSeat == null
    ? "🤝 ¡Empate! El tablero se ha llenado sin cuatro en línea."
    : `🎉 ¡Gana <strong>${esc(seatLabel(G.winnerSeat))}</strong> con cuatro en línea!`;
}

/* Light up the card of the side to move, and crown the winner. */
function renderTurns() {
  for (const i of [0, 1]) {
    const card = $(`turn-${i}`);
    card.classList.toggle("active", isLive() && !G.gameOver && seatToMove() === i);
    card.classList.toggle("winner", isLive() && G.gameOver && G.winnerSeat === i);
  }
}

function renderStatus() {
  const st = $("status");
  if (!isLive()) {
    st.innerHTML = `⏳ Viendo la jugada ${G.cursor} de ${G.moves.length}. ` +
      `<em>Vuelve a la última para seguir jugando.</em>`;
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
    st.innerHTML = `<span class="chip ${chip}">${esc(seatName(seat))}</span> te toca: pulsa una columna para soltar tu ficha.`;
  } else {
    st.innerHTML = `<span class="chip ${chip}">${esc(who)}</span> ${G.thinking ? "está pensando…" : "juega a continuación…"}`;
  }
}

/* The X-ray analysis of the live position, or null when it is not shown. */
function liveAnalysis() {
  if (!G.showXray || !isLive() || G.gameOver) return null;
  return window.C4.analysis(current());
}

function formatScore(score) {
  if (score == null) return null;
  if (score >= 9000) return "GANA";
  if (score <= -9000) return "PIERDE";
  return String(Math.round(score));
}

function renderBoard() {
  const board = $("board");
  const state = shown();
  const interactive =
    isLive() && !G.gameOver && !G.thinking && G.seats[seatToMove()] === HUMAN;
  const an = liveAnalysis();

  // Only a move that was just made falls into place; scrubbing and redraws
  // (a seat change, the X-ray toggle) show the board as it stands.
  const drop = G.justMoved && isLive() && G.cursor > 0
    ? newPiece(G.history[G.cursor - 1], G.history[G.cursor])
    : null;
  G.justMoved = false;

  paintBoard(board, state, {
    onPick: interactive ? humanMove : null,
    line: isLive() ? G.line : null,
    targetColumn: an && an.best != null ? an.best : -1,
    scores: an ? an.scores.map(formatScore) : null,
    drop,
    ghost: interactive ? seatToMove() + 1 : null,
  });

  const old = board.parentElement.querySelector(".win-banner");
  if (old) old.remove();
  if (G.gameOver && isLive()) {
    const text = G.winnerSeat == null ? "🤝 ¡Empate!" : `🏆 ¡Gana ${seatLabel(G.winnerSeat)}!`;
    board.after(el("div", "win-banner", text));
  }
}

function renderXray() {
  const box = $("xray");
  if (!G.showXray) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  if (!isLive()) {
    box.innerHTML = `<strong>Rayos X:</strong> vuelve a la última jugada para analizarla.`;
    return;
  }
  if (G.gameOver) {
    box.innerHTML = `<strong>Rayos X:</strong> la partida ha terminado.`;
    return;
  }
  const an = window.C4.analysis(current());
  const verdicts = {
    win: "quien mueve <strong>puede forzar la victoria</strong>",
    loss: "quien mueve <strong>pierde si el rival juega bien</strong> (¡aguanta y reza!)",
    unclear: "no hay un resultado forzado a la vista",
  };
  box.innerHTML =
    `<strong>Rayos X:</strong> cada columna puntuada con una búsqueda de 5 jugadas para quien mueve ` +
    `(más es mejor). Veredicto: ${verdicts[an.verdict] || an.verdict}. ` +
    (an.best != null ? `Mejor columna: <strong>${an.best + 1}</strong> (marcada).` : "");
}

function logMove(m) {
  if (!G.showWhy) return;
  const cls = m.seat === 0 ? "a" : "b";
  const entry = el("div", `why-entry ${cls}`);
  const head = el("div", "head");
  head.appendChild(el("span", null, `${seatLabel(m.seat)} · columna ${m.move + 1}`));
  head.appendChild(el("span", "time", m.elapsed != null ? `${m.elapsed.toFixed(1)} ms` : "persona"));
  entry.appendChild(head);
  if (m.info && m.info.note) {
    entry.appendChild(el("div", "note", m.info.note));
    const bits = [];
    if (m.info.depth != null) bits.push(`profundidad ${m.info.depth}`);
    if (m.info.score != null) bits.push(`puntuación ${Number(m.info.score).toFixed(2)}`);
    if (m.info.nodes != null) bits.push(`${m.info.nodes} nodos`);
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
  $("tl-label").textContent = `jugada ${G.cursor} / ${G.history.length - 1}`;
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
    win: ": ¡fuerza la victoria!",
    loss: ": todas pierden si el rival juega bien, esta es la que más aguanta.",
    unclear: ".",
  };
  toast(`Prueba la columna ${an.best + 1}${why[an.verdict] || "."}`);
  paintBoard($("board"), current(), {
    onPick: humanMove, targetColumn: an.best, ghost: seatToMove() + 1,
  });
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
    () => toast("¡Enlace de la partida copiado!"),
    () => toast("No se pudo copiar: el enlace está en la barra de direcciones."),
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
    toast("Partida compartida cargada.");
    return true;
  } catch (err) {
    toast("No se pudo leer el enlace compartido.");
    return false;
  }
}


/* ---------------- wiring ---------------- */
function setupPlay() {
  setupTimeline();
  $("btn-new").onclick = guard("Nueva partida", () => newGame());
  $("btn-hint").onclick = guard("Pista", hint);
  $("btn-share").onclick = guard("Compartir", shareLink);
  $("btn-play-ai").onclick = guard("Turno del bot", () => {
    clearTimeout(G.aiTimer);
    const name = G.seats[seatToMove()];
    if (name !== HUMAN) runAITurn(name);
  });
  $("cfg-delay").onchange = (e) => { G.delay = parseInt(e.target.value) || 0; };
  $("toggle-xray").onchange = guard("Rayos X", (e) => { G.showXray = e.target.checked; render(); });
  $("toggle-why").onchange = (e) => { G.showWhy = e.target.checked; };
}
