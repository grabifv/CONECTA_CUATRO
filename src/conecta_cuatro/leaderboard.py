"""Leaderboard persistente en JSON con victorias, derrotas y empates."""

import json
import os


class Leaderboard:
    def __init__(self, ruta):
        self.ruta = ruta
        self.datos = self._cargar()

    def _cargar(self):
        if not os.path.exists(self.ruta):
            return {}
        try:
            with open(self.ruta, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            print(f"Aviso: no se pudo leer {self.ruta}, se empieza un leaderboard nuevo.")
            return {}

    def _guardar(self):
        temporal = self.ruta + ".tmp"
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(self.datos, f, indent=2, ensure_ascii=False)
        os.replace(temporal, self.ruta)

    def _entrada(self, jugador):
        return self.datos.setdefault(
            jugador.clave,
            {
                "nombre": jugador.nombre,
                "tipo": "bot" if jugador.es_bot else "humano",
                "victorias": 0,
                "derrotas": 0,
                "empates": 0,
            },
        )

    def registrar(self, resultado, jugador1, jugador2):
        """Apunta el resultado de una partida. Las abandonadas no cuentan."""
        if resultado.abandonada:
            return
        if resultado.empate:
            self._entrada(jugador1)["empates"] += 1
            self._entrada(jugador2)["empates"] += 1
        else:
            self._entrada(resultado.ganador)["victorias"] += 1
            self._entrada(resultado.perdedor)["derrotas"] += 1
        self._guardar()

    def ranking(self, tipo=None):
        """Lista de entradas ordenadas por victorias (y % de victoria)."""
        entradas = [e for e in self.datos.values() if tipo is None or e["tipo"] == tipo]

        def porcentaje(e):
            jugadas = e["victorias"] + e["derrotas"] + e["empates"]
            return e["victorias"] / jugadas if jugadas else 0.0

        return sorted(entradas, key=lambda e: (e["victorias"], porcentaje(e)), reverse=True)

    def mostrar(self, tipo=None):
        filas = self.ranking(tipo)
        if not filas:
            print("El leaderboard está vacío. ¡Juega alguna partida!")
            return
        print(f"\n{'#':>3}  {'Nombre':<22}{'Tipo':<8}{'V':>5}{'D':>5}{'E':>5}{'% V':>7}")
        print("-" * 55)
        for i, e in enumerate(filas, 1):
            jugadas = e["victorias"] + e["derrotas"] + e["empates"]
            pct = 100 * e["victorias"] / jugadas if jugadas else 0
            print(
                f"{i:>3}  {e['nombre'][:21]:<22}{e['tipo']:<8}"
                f"{e['victorias']:>5}{e['derrotas']:>5}{e['empates']:>5}{pct:>6.1f}%"
            )
