# agent/brain.py — Cerebro del agente: conexión con Claude API
# Generado por AgentKit

import os
import yaml
import logging
from datetime import datetime
import pytz
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from agent.fichas import FICHAS

load_dotenv(override=True)
logger = logging.getLogger("agentkit")

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TOOLS = [
    {
        "name": "enviar_ficha_tecnica",
        "description": (
            "Envía la ficha técnica en PDF de una propiedad al cliente por WhatsApp, "
            "con fotos y todos los detalles. Úsala cuando el cliente muestre interés real "
            "en una propiedad específica (pregunta por más info, fotos, ubicación o detalles)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "propiedad": {
                    "type": "string",
                    "enum": list(FICHAS.keys()),
                    "description": "Identificador de la propiedad de la cual enviar la ficha técnica",
                }
            },
            "required": ["propiedad"],
        },
    }
]


def cargar_config_prompts() -> dict:
    """Lee toda la configuración desde config/prompts.yaml."""
    try:
        with open("config/prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/prompts.yaml no encontrado")
        return {}


def cargar_system_prompt() -> str:
    """Lee el system prompt desde config/prompts.yaml."""
    config = cargar_config_prompts()
    return config.get("system_prompt", "Eres un asistente útil de Doppler. Responde en español.")


def obtener_mensaje_error() -> str:
    config = cargar_config_prompts()
    return config.get("error_message", "Lo siento, estoy teniendo problemas técnicos. Por favor intenta de nuevo en unos minutos.")


def obtener_mensaje_fallback() -> str:
    config = cargar_config_prompts()
    return config.get("fallback_message", "Disculpa, no entendí tu mensaje. ¿Podrías reformularlo?")


async def generar_respuesta(mensaje: str, historial: list[dict]) -> tuple[str, str | None]:
    """
    Genera una respuesta usando Claude API.

    Args:
        mensaje: El mensaje nuevo del usuario
        historial: Lista de mensajes anteriores [{"role": "user/assistant", "content": "..."}]

    Returns:
        Tupla (texto_respuesta, archivo_ficha_o_None)
    """
    if not mensaje or len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback(), None

    # Obtener hora actual de Mérida para que Lea salude correctamente
    zona_merida = pytz.timezone("America/Merida")
    hora_merida = datetime.now(zona_merida).strftime("%H:%M")
    system_prompt = cargar_system_prompt().replace("[HORA_MERIDA]", hora_merida)
    system_prompt = f"[HORA_MERIDA: {hora_merida}]\n\n" + system_prompt

    mensajes = []
    for msg in historial:
        mensajes.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    mensajes.append({
        "role": "user",
        "content": mensaje
    })

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            tools=TOOLS,
            messages=mensajes
        )

        texto_partes = []
        ficha_solicitada = None

        for bloque in response.content:
            if bloque.type == "text":
                texto_partes.append(bloque.text)
            elif bloque.type == "tool_use" and bloque.name == "enviar_ficha_tecnica":
                propiedad = bloque.input.get("propiedad")
                ficha_solicitada = FICHAS.get(propiedad)

        respuesta = "\n".join(texto_partes).strip()

        if not respuesta and ficha_solicitada:
            respuesta = "Claro, te comparto la ficha técnica con todos los detalles 📄"

        logger.info(f"Respuesta generada ({response.usage.input_tokens} in / {response.usage.output_tokens} out)")
        return respuesta, ficha_solicitada

    except Exception as e:
        logger.error(f"Error Claude API: {e}")
        return obtener_mensaje_error(), None
