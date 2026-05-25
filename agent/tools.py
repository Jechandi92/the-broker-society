# agent/tools.py — Herramientas del agente Doppler
# Generado por AgentKit

import os
import yaml
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")


def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    """Retorna el horario de atención del negocio."""
    return {
        "horario": "24 horas, 7 días a la semana",
        "esta_abierto": True,
        "nota": "El agente responde 24/7. Para temas que requieren a Jaime: Lunes a Viernes 9am-6pm."
    }


def buscar_en_knowledge(consulta: str) -> str:
    """
    Busca información relevante en los archivos de /knowledge.
    Retorna el contenido más relevante encontrado.
    """
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica sobre eso en mis archivos."


def registrar_lead(telefono: str, nombre: str, tipo_negocio: str, interes: str) -> dict:
    """
    Registra un nuevo lead calificado.
    En producción esto se conectaría al CRM de Google Sheets via Make.com.
    """
    lead = {
        "telefono": telefono,
        "nombre": nombre,
        "tipo_negocio": tipo_negocio,
        "interes": interes,
        "timestamp": datetime.utcnow().isoformat(),
        "estado": "caliente",
        "fuente": "whatsapp_agente"
    }
    logger.info(f"Nuevo lead registrado: {lead}")
    # TODO: integrar con Google Sheets via Make.com webhook
    return lead


def calificar_lead(tiene_instagram: bool, publica_actualmente: bool, tiene_equipo_redes: bool) -> str:
    """
    Califica un prospecto según sus respuestas.
    Retorna: 'caliente', 'tibio' o 'frio'
    """
    if tiene_instagram and not publica_actualmente:
        return "caliente"
    if tiene_instagram and publica_actualmente and not tiene_equipo_redes:
        return "caliente"
    if tiene_instagram and publica_actualmente:
        return "tibio"
    return "frio"


def obtener_info_niveles() -> list[dict]:
    """Retorna la tabla de niveles y precios de Doppler."""
    return [
        {
            "nivel": 1,
            "nombre": "Doppler Content",
            "precio_mes": 1500,
            "instalacion_normal": 2500,
            "instalacion_fundador": 0,
            "descripcion": "Publicación automática en Instagram con captions generados por IA"
        },
        {
            "nivel": 2,
            "nombre": "+ Doppler Leads",
            "precio_mes": 2500,
            "instalacion_upgrade": 500,
            "descripcion": "Captura y clasificación inteligente de prospectos en CRM"
        },
        {
            "nivel": 3,
            "nombre": "+ Doppler Agenda",
            "precio_mes": 3500,
            "instalacion_upgrade": 800,
            "descripcion": "Agendamiento automático con recordatorios y reducción de no-shows"
        },
        {
            "nivel": 4,
            "nombre": "+ Doppler WhatsApp",
            "precio_mes": 4800,
            "instalacion_upgrade": 1500,
            "descripcion": "Asistente virtual 24/7 entrenado en el negocio del cliente"
        },
        {
            "nivel": 5,
            "nombre": "+ Doppler 360",
            "precio_mes": 6500,
            "instalacion_upgrade": 2000,
            "descripcion": "Reportes, reactivación de leads fríos y gestión de reseñas"
        },
    ]
