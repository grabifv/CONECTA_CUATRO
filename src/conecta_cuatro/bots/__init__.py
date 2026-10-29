"""Carpeta de bots: cualquier subclase de ``Bot`` definida aquí se carga sola."""

import importlib
import inspect
import pkgutil

from ..jugadores import Bot


def cargar_bots():
    """Devuelve {nombre: clase} con todos los bots de esta carpeta."""
    encontrados = {}
    for modulo_info in pkgutil.iter_modules(__path__):
        if modulo_info.name.startswith("_"):
            continue
        try:
            modulo = importlib.import_module(f"{__name__}.{modulo_info.name}")
        except Exception as error:
            print(f"Aviso: no se pudo cargar el bot '{modulo_info.name}': {error!r}")
            continue
        for _, clase in inspect.getmembers(modulo, inspect.isclass):
            if (
                issubclass(clase, Bot)
                and clase is not Bot
                and clase.__module__ == modulo.__name__
                and not inspect.isabstract(clase)
            ):
                encontrados[clase.nombre] = clase
    return dict(sorted(encontrados.items()))
