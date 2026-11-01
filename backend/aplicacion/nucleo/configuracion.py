"""Configuracion de la aplicacion, leida de variables de entorno y del archivo .env.

El archivo .env vive en la raiz del repositorio (nunca se sube a Git).
Las variables de entorno reales tienen prioridad sobre el archivo .env.

Uso:
    from aplicacion.nucleo.configuracion import obtener_configuracion
    configuracion = obtener_configuracion()
    configuracion.base_datos_url
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/aplicacion/nucleo/configuracion.py -> la raiz del repositorio esta 3 niveles arriba
RAIZ_PROYECTO = Path(__file__).resolve().parents[3]


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ_PROYECTO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_datos_url: str = "postgresql://clinica:clinica@localhost:5432/clinica_san_rafael"
    clave_secreta_jwt: str = "cambiar-por-un-valor-largo-y-aleatorio"
    expiracion_token_minutos: int = 60
    autenticacion_simulada: bool = False
    rol_simulado: str = "MEDICO"
    # Origenes del frontend permitidos por CORS, separados por comas
    origenes_permitidos: str = "http://localhost:5173"

    @property
    def lista_origenes_permitidos(self) -> list[str]:
        return [origen.strip() for origen in self.origenes_permitidos.split(",") if origen.strip()]


@lru_cache
def obtener_configuracion() -> Configuracion:
    """Devuelve la configuracion (se lee una sola vez).

    En pruebas, llamar a obtener_configuracion.cache_clear() despues de cambiar variables de entorno.
    """
    return Configuracion()
