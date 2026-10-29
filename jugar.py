"""Lanzador: ejecuta `python jugar.py` desde la raíz del proyecto."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from conecta_cuatro.conecta_cuatro import main  # noqa: E402

main()
