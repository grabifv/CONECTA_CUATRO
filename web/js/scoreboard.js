// Conecta Cuatro — the Scoreboard screen
//
// Renders results/leaderboard.json as a podium, one card per bot and a
// head-to-head grid. The tournament enters each bot more than once
// ("hard_0", "hard_1"); everything here is grouped by bot *kind*, which is what
// a reader cares about.
//
// Loaded as a plain script (not an ES module): the whole app shares one global
// namespace by design, and plain scripts keep working without a bundler.
"use strict";

const MODE_LABEL = { simple: "todos contra todos", league: "liga con Elo", championship: "campeonato" };
const LEVEL_LABEL = { random: "Al azar", easy: "Fácil", medium: "Medio", hard: "Difícil" };
/* The reference bots describe themselves in English (the docs and the
   tournament share those strings); the page shows them in Spanish. */
const DESC_ES = {
  random: "Suelta la ficha en una columna libre al azar. Sin estrategia: es la referencia que todos deben superar.",
  easy: "Mira una jugada por delante: gana si puede, tapa si debe y, si no, juega lo más al centro posible. Cae en cualquier doble amenaza.",
  medium: "Minimax con poda alfa-beta a 4 jugadas que valora tener fichas en el centro. No se le escapa lo que ve, pero no construye amenazas.",
  hard: "Minimax con poda alfa-beta a 5 jugadas que cuenta las líneas de cuatro abiertas de cada jugador. Fuerte, pero no perfecto.",
};

async function loadScoreboard() {
  const content = $("sb-content");
  const empty = $("sb-empty");
  try {
    const resp = await fetch("leaderboard.json", { cache: "no-cache" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    empty.classList.add("hidden");
    content.classList.remove("hidden");
    renderScoreboard(data);
  } catch (err) {
    content.classList.add("hidden");
    empty.classList.remove("hidden");
    empty.textContent =
      "Todavía no hay clasificación. Se genera con el torneo automático " +
      "(o en local con `conecta-cuatro-torneo`).";
    $("sb-meta").textContent = "";
  }
}

/* Fold the per-copy standings and matches into one record per bot kind. */
function groupByKind(data) {
  const kinds = new Map();
  const kindOf = (name) => splitPlayer(name)[0];
  const get = (k) => {
    if (!kinds.has(k)) {
      kinds.set(k, { name: k, wins: 0, draws: 0, losses: 0, forfeits: 0,
                     games: 0, points: 0, elo: [], vs: new Map() });
    }
    return kinds.get(k);
  };
  for (const row of data.standings || []) {
    const k = get(kindOf(row.player));
    k.wins += row.wins; k.draws += row.draws ?? 0; k.losses += row.losses;
    k.forfeits += row.forfeits ?? 0; k.games += row.games; k.points += row.points;
    if (row.elo != null) k.elo.push(row.elo);
  }
  // Head to head, kind against kind: [wins, draws, losses] from the row's side.
  const bump = (a, b, w, d, l) => {
    const rec = get(a).vs.get(b) || [0, 0, 0];
    rec[0] += w; rec[1] += d; rec[2] += l;
    get(a).vs.set(b, rec);
  };
  for (const m of data.matches || []) {
    const a = kindOf(m.player_a), b = kindOf(m.player_b);
    const d = m.draws ?? 0;
    bump(a, b, m.a_wins, d, m.b_wins);
    bump(b, a, m.b_wins, d, m.a_wins);
  }
  const list = [...kinds.values()];
  for (const k of list) {
    k.rating = k.elo.length ? k.elo.reduce((x, y) => x + y, 0) / k.elo.length : null;
    k.winRate = k.games ? k.wins / k.games : 0;
  }
  const useElo = list.every((k) => k.rating != null);
  list.sort((x, y) => (useElo ? y.rating - x.rating : y.points / (y.games || 1) - x.points / (x.games || 1)));
  return { list, useElo };
}

function renderScoreboard(data) {
  for (const p of data.players || []) META.set(p.name, p);
  const cfg = data.config || {};
  const { list, useElo } = groupByKind(data);

  $("sb-title").textContent = "Clasificación";
  const when = (data.generated_at || "").replace("T", " a las ").replace(/:\d\dZ$/, " UTC");
  $("sb-meta").textContent =
    `Último torneo: ${when} · ${MODE_LABEL[cfg.tournament] || cfg.tournament || "torneo"} · ` +
    `${(data.totals && data.totals.games) ?? "?"} partidas entre ${list.length} bots.`;

  renderPodium(list, useElo);
  renderBots(list, useElo);
  renderHeadToHead(list);
  renderFacts(data.totals || {});
}

function scoreText(k, useElo) {
  return useElo ? `${Math.round(k.rating)} Elo` : `${k.points} pts`;
}

function renderPodium(list, useElo) {
  const box = $("sb-podium");
  box.innerHTML = "";
  // Second, first, third: the winner stands in the middle, highest.
  const places = [[1, "silver", "🥈"], [0, "gold", "🥇"], [2, "bronze", "🥉"]];
  for (const [i, cls, medal] of places) {
    const k = list[i];
    if (!k) continue;
    const step = el("div", `pod ${cls}`);
    step.innerHTML =
      `<div class="pod-icon">${esc(playerIcon(k.name))}</div>` +
      `<div class="pod-name">${esc(k.name)}</div>` +
      `<div class="pod-score">${esc(scoreText(k, useElo))}</div>` +
      `<div class="pod-block"><span>${medal}</span>${i + 1}º</div>`;
    box.appendChild(step);
  }
}

function renderBots(list, useElo) {
  const box = $("sb-bots");
  box.innerHTML = "";
  list.forEach((k, idx) => {
    const meta = META.get(k.name) || {};
    const pct = (n) => (k.games ? (100 * n) / k.games : 0);
    const card = el("article", "bot-card");
    card.innerHTML =
      `<header>` +
      `<span class="bot-rank">${idx + 1}</span>` +
      `<span class="bot-icon">${esc(playerIcon(k.name))}</span>` +
      `<div class="bot-id"><strong>${esc(k.name)}</strong>` +
      `<span class="bot-level">${esc(LEVEL_LABEL[k.name] || (meta.authors || []).join(", ") || "Bot")}</span></div>` +
      `<span class="bot-score">${esc(scoreText(k, useElo))}</span>` +
      `</header>` +
      `<p class="bot-desc">${esc(DESC_ES[k.name] || meta.description || "")}</p>` +
      `<div class="wdl" title="Victorias / empates / derrotas">` +
      `<span class="w" style="width:${pct(k.wins)}%"></span>` +
      `<span class="d" style="width:${pct(k.draws)}%"></span>` +
      `<span class="l" style="width:${pct(k.losses)}%"></span></div>` +
      `<div class="wdl-legend">` +
      `<span><i class="w"></i>${k.wins} victorias</span>` +
      `<span><i class="d"></i>${k.draws} empates</span>` +
      `<span><i class="l"></i>${k.losses} derrotas</span>` +
      `</div>` +
      `<footer>${Math.round(100 * k.winRate)}% de victorias en ${k.games} partidas` +
      `${k.forfeits ? ` · ${k.forfeits} descalificaciones` : ""}</footer>`;
    box.appendChild(card);
  });
}

function renderHeadToHead(list) {
  const box = $("sb-h2h");
  box.innerHTML = "";
  const table = el("table", "h2h");
  let html = "<thead><tr><th></th>";
  for (const col of list) html += `<th title="${esc(col.name)}">${esc(playerIcon(col.name))}<br>${esc(col.name)}</th>`;
  html += "</tr></thead><tbody>";
  for (const row of list) {
    html += `<tr><th>${esc(playerIcon(row.name))} ${esc(row.name)}</th>`;
    for (const col of list) {
      const rec = row.vs.get(col.name);
      if (!rec || row.name === col.name) {
        html += `<td class="self">—</td>`;
        continue;
      }
      const games = rec[0] + rec[1] + rec[2];
      const rate = games ? rec[0] / games : 0;
      // Hue from red (loses) through yellow to green (wins).
      const hue = Math.round(rate * 130);
      html += `<td style="--h:${hue}" title="${rec[0]} victorias, ${rec[1]} empates, ${rec[2]} derrotas">` +
        `${Math.round(100 * rate)}%</td>`;
    }
    html += "</tr>";
  }
  table.innerHTML = html + "</tbody>";
  box.appendChild(table);
}

function renderFacts(t) {
  const box = $("sb-facts");
  box.innerHTML = "";
  const facts = [
    ["🎮", t.games ?? "—", "partidas jugadas"],
    ["🤝", t.draws ?? "—", "empates"],
    ["📏", t.avg_game_moves != null ? Math.round(t.avg_game_moves) : "—", "jugadas por partida, de media"],
    ["🐢", t.longest_game_moves ?? "—", "jugadas en la partida más larga"],
    ["🚫", t.forfeits ?? "—", "descalificaciones"],
    ["⏱️", t.total_move_time_ms != null ? `${(t.total_move_time_ms / 1000).toFixed(1)} s` : "—", "pensando, entre todos"],
  ];
  for (const [icon, value, label] of facts) {
    const tile = el("div", "fact");
    tile.innerHTML = `<span class="fact-icon">${icon}</span><strong>${esc(String(value))}</strong><span>${esc(label)}</span>`;
    box.appendChild(tile);
  }
}

function setupScoreboard() {
  // Everything is drawn on demand when the screen opens (see showScreen);
  // there is nothing to wire up front.
}
