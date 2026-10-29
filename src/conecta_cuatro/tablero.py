"""Lógica del tablero de Conecta Cuatro (sin entrada/salida)."""

FILAS = 6
COLUMNAS = 7
VACIO = 0
FICHA_1 = 1
FICHA_2 = 2

SIMBOLOS = {VACIO: ".", FICHA_1: "X", FICHA_2: "O"}
COLORES = {FICHA_1: "\033[91m", FICHA_2: "\033[93m"}  # rojo, amarillo
RESET = "\033[0m"


def ficha_rival(ficha):
    return FICHA_2 if ficha == FICHA_1 else FICHA_1


class Tablero:
    """Tablero de filas x columnas. La fila 0 es la de arriba."""

    def __init__(self, filas=FILAS, columnas=COLUMNAS):
        self.filas = filas
        self.columnas = columnas
        self.celdas = [[VACIO] * columnas for _ in range(filas)]
        self.historial = []  # lista de (fila, columna) en orden de juego

    def copia(self):
        nuevo = Tablero(self.filas, self.columnas)
        nuevo.celdas = [fila[:] for fila in self.celdas]
        nuevo.historial = self.historial[:]
        return nuevo

    def es_valida(self, columna):
        return (
            isinstance(columna, int)
            and 0 <= columna < self.columnas
            and self.celdas[0][columna] == VACIO
        )

    def columnas_validas(self):
        return [c for c in range(self.columnas) if self.es_valida(c)]

    def soltar(self, columna, ficha):
        """Deja caer una ficha en la columna. Devuelve la fila donde queda."""
        if not self.es_valida(columna):
            raise ValueError(f"Columna no válida: {columna!r}")
        for fila in range(self.filas - 1, -1, -1):
            if self.celdas[fila][columna] == VACIO:
                self.celdas[fila][columna] = ficha
                self.historial.append((fila, columna))
                return fila

    def deshacer(self):
        """Quita la última ficha jugada (útil para bots que exploran jugadas)."""
        fila, columna = self.historial.pop()
        self.celdas[fila][columna] = VACIO

    def lleno(self):
        return all(self.celdas[0][c] != VACIO for c in range(self.columnas))

    def hay_cuatro_desde(self, fila, columna):
        """Comprueba si la ficha en (fila, columna) forma 4 en línea."""
        ficha = self.celdas[fila][columna]
        if ficha == VACIO:
            return False
        for df, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
            seguidas = 1
            for signo in (1, -1):
                f, c = fila + df * signo, columna + dc * signo
                while (
                    0 <= f < self.filas
                    and 0 <= c < self.columnas
                    and self.celdas[f][c] == ficha
                ):
                    seguidas += 1
                    f += df * signo
                    c += dc * signo
            if seguidas >= 4:
                return True
        return False

    def ganador(self):
        """Devuelve la ficha ganadora tras la última jugada, o None."""
        if not self.historial:
            return None
        fila, columna = self.historial[-1]
        if self.hay_cuatro_desde(fila, columna):
            return self.celdas[fila][columna]
        return None

    def dibujar(self, color=True):
        lineas = []
        for fila in self.celdas:
            celdas = []
            for ficha in fila:
                simbolo = SIMBOLOS[ficha]
                if color and ficha in COLORES:
                    simbolo = f"{COLORES[ficha]}{simbolo}{RESET}"
                celdas.append(simbolo)
            lineas.append("| " + " ".join(celdas) + " |")
        lineas.append("+" + "-" * (self.columnas * 2 + 1) + "+")
        lineas.append("  " + " ".join(str(c + 1) for c in range(self.columnas)))
        return "\n".join(lineas)

    def __str__(self):
        return self.dibujar(color=False)
