// Conecta Cuatro Arena — boot and wiring.
//
// Loads the screen partials, wires each screen independently, then starts the
// Python engine.
//
// Two rules here, both learned the hard way:
//
//   1. **Never let one failure kill the wiring.** This file used to set every
//      handler in a single straight line, so an exception anywhere left later
//      buttons with no `onclick` at all — and a button with no handler does
//      nothing, silently, with no clue as to why. Each step is now isolated.
//   2. **Never fail silently.** An exception inside an event handler is
//      swallowed by the browser and only appears in the console. Everything the
//      user can trigger goes through `guard()`, and anything that escapes lands
//      in a visible banner.
"use strict";

const SCREENS = ["menu", "game", "scoreboard", "tournament", "about"];

/* Show a persistent, visible error. The console is not good enough: "nothing
   happened" is the least debuggable bug report there is. */
function showFatal(what, err) {
  const box = $("fatal");
  if (!box) return;
  box.classList.remove("hidden");
  box.innerHTML =
    `<strong>${esc(what)}</strong><br>` +
    `<code>${esc(err && err.message ? err.message : String(err))}</code><br>` +
    `<span class="muted small">Mira la consola del navegador para ver el detalle.</span>`;
  console.error(what, err);
}

/* Wrap a user-triggered handler so a throw becomes a toast, not silence. */
function guard(label, fn) {
  return (...args) => {
    try {
      return fn(...args);
    } catch (err) {
      console.error(`${label} failed`, err);
      toast(`${label}: algo ha fallado (${err.message || err})`);
    }
  };
}

/* Run one setup step in isolation, so a failure cannot disarm the others. */
function step(label, fn) {
  try {
    fn();
    return true;
  } catch (err) {
    showFatal(`No se pudo preparar ${label}`, err);
    return false;
  }
}

/* Fetch each screen's markup and place it in the shell. Screens live in their
   own files so a page is editable without scrolling past the other four. */
async function loadScreens() {
  const host = $("screens");
  const parts = await Promise.all(
    SCREENS.map(async (name) => {
      const resp = await fetch(`screens/${name}.html`, { cache: "no-cache" });
      if (!resp.ok) throw new Error(`screens/${name}.html → HTTP ${resp.status}`);
      return resp.text();
    }),
  );
  host.innerHTML = parts.join("\n");
  // Only the menu starts visible.
  for (const name of SCREENS) {
    const el = $(`screen-${name}`);
    if (el) el.classList.toggle("hidden", name !== "menu");
  }
}

async function main() {
  window.addEventListener("error", (e) => showFatal("Error inesperado", e.error || e.message));
  window.addEventListener("unhandledrejection", (e) => showFatal("Error inesperado", e.reason));

  try {
    await loadScreens();
  } catch (err) {
    showFatal("No se pudo cargar la página", err);
    $("boot-status").textContent = "⚠️ " + (err.message || err);
    return;
  }

  // DOM-only wiring: safe before the engine exists.
  step("la navegación", setupNav);
  step("la pantalla de juego", setupPlay);
  step("la clasificación", setupScoreboard);
  step("el torneo", setupTournament);

  try {
    await window.bootEngine((msg) => { $("boot-status").textContent = msg; });
  } catch (err) {
    $("boot-status").textContent = "⚠️ " + (err.message || err);
    showFatal("El motor de Python no ha arrancado", err);
    return;
  }

  // Anything that needs the engine: the player lists.
  step("la lista de jugadores", populateSeatSelects);
  step("los participantes del torneo", tBuildSetup);

  $("boot").classList.add("hidden");

  if (!loadFromHash()) {
    newGame({ rows: DEFAULT_SIZE[0], columns: DEFAULT_SIZE[1] });
    showScreen("menu");
  }
}

window.addEventListener("DOMContentLoaded", main);
