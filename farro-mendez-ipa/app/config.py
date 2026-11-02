"""Módulo de configuración centralizada con Pydantic Settings.

Carga y valida las variables de entorno para la base de datos PostgreSQL,
WhatsApp Cloud API y Google Gemini.
"""

import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Configuraciones del sistema cargadas desde el entorno o archivo .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Base de Datos PostgreSQL
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/farro_mendez",
        description="URL de conexión asíncrona a PostgreSQL con asyncpg"
    )

    # WhatsApp Cloud API (Meta Developers)
    WHATSAPP_API_TOKEN: str = Field(
        default="TU_TOKEN_AQUI",
        description="Token de acceso permanente o temporal de WhatsApp Cloud API"
    )
    WHATSAPP_PHONE_NUMBER_ID: str = Field(
        default="TU_PHONE_NUMBER_ID_AQUI",
        description="ID del número de teléfono registrado en WhatsApp Cloud API"
    )
    WHATSAPP_VERIFY_TOKEN: str = Field(
        default="TU_VERIFY_TOKEN_AQUI",
        description="Token secreto configurado en el Webhook de Meta para verificación GET"
    )
    WHATSAPP_API_URL: str = Field(
        default="https://graph.facebook.com/v21.0",
        description="URL base de la API de Graph de Meta"
    )

    # Google Gemini
    GEMINI_API_KEY: str = Field(
        default="TU_GEMINI_API_KEY_AQUI",
        description="Clave de API para invocar modelos Google Gemini"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Nombre del modelo Gemini a utilizar (ej. gemini-2.5-flash, gemini-1.5-flash)"
    )

    # Configuración de Flujo y Servidor
    FLOW_MODE: Literal["rpa", "agentic"] = Field(
        default="rpa",
        description="Modo de ejecución: 'rpa' (flujo determinista orquestado) o 'agentic' (AI Agent)"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    APP_HOST: str = Field(
        default="0.0.0.0",
        description="Host para bind de FastAPI"
    )
    APP_PORT: int = Field(
        default=8000,
        description="Puerto para bind de FastAPI"
    )

    @property
    def sync_database_url(self) -> str:
        """Devuelve una URL sincrónica compatible con Alembic/psycopg2."""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


# Instancia singleton de configuraciones
settings = Settings()
