# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit

import os
import secrets
import logging
import urllib.parse
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends, Form, UploadFile, File
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import (
    inicializar_db,
    guardar_mensaje,
    obtener_historial,
    esta_pausado,
    set_pausado,
    set_etiqueta,
    eliminar_conversacion,
    listar_conversaciones,
)
from agent.providers import obtener_proveedor
from agent.panel import PANEL_HTML

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")

security = HTTPBasic()


def verificar_acceso(credentials: HTTPBasicCredentials = Depends(security)):
    """Protege el panel con usuario y contraseña definidos en .env."""
    usuario_correcto = secrets.compare_digest(credentials.username, os.getenv("PANEL_USER", "admin"))
    clave_correcta = secrets.compare_digest(credentials.password, os.getenv("PANEL_PASSWORD", "changeme"))
    if not (usuario_correcto and clave_correcta):
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor AgentKit corriendo en puerto {PORT}")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="Doppler — WhatsApp AI Agent",
    version="1.0.0",
    lifespan=lifespan
)

# Sirve las fichas técnicas en PDF para que WhatsApp pueda descargarlas
app.mount("/fichas", StaticFiles(directory="knowledge/Fichas"), name="fichas")

# Carpeta para archivos enviados manualmente desde el panel
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def health_check():
    """Endpoint de salud para Railway/monitoreo."""
    return {"status": "ok", "service": "doppler-agentkit"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """Verificación GET del webhook (requerido por Meta Cloud API, no-op para Twilio)."""
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe mensajes de WhatsApp via Twilio.
    Procesa el mensaje, genera respuesta con Claude y la envía de vuelta.
    """
    try:
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            if msg.es_propio or not msg.texto:
                continue

            logger.info(f"Mensaje de {msg.telefono}: {msg.texto}")

            # Obtener historial y estado de pausa ANTES de guardar el mensaje actual
            historial = await obtener_historial(msg.telefono)
            pausado = await esta_pausado(msg.telefono)

            await guardar_mensaje(msg.telefono, "user", msg.texto)

            if pausado:
                logger.info(f"Conversación pausada (modo humano) para {msg.telefono}, no se responde")
                continue

            # Generar respuesta con Claude
            respuesta, archivo_ficha = await generar_respuesta(msg.texto, historial)

            # Guardar respuesta del agente
            await guardar_mensaje(msg.telefono, "assistant", respuesta)

            # Enviar respuesta por WhatsApp via Twilio
            await proveedor.enviar_mensaje(msg.telefono, respuesta)

            # Si Lea pidió enviar una ficha técnica, mandarla como documento PDF
            if archivo_ficha and PUBLIC_URL:
                url_ficha = f"{PUBLIC_URL}/fichas/{urllib.parse.quote(archivo_ficha)}"
                await proveedor.enviar_documento(msg.telefono, url_ficha)
            elif archivo_ficha and not PUBLIC_URL:
                logger.warning("PUBLIC_URL no configurado, no se pudo enviar la ficha técnica")

            logger.info(f"Respuesta a {msg.telefono}: {respuesta}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════
# Panel web — para que el equipo vea conversaciones e intervenga
# ════════════════════════════════════════════════════════════

@app.get("/panel", response_class=HTMLResponse)
async def panel(autorizado: bool = Depends(verificar_acceso)):
    """Sirve el panel web de conversaciones."""
    return PANEL_HTML


@app.get("/api/conversaciones")
async def api_conversaciones(autorizado: bool = Depends(verificar_acceso)):
    """Lista todas las conversaciones con su último mensaje y estado de pausa."""
    return await listar_conversaciones()


@app.get("/api/conversaciones/{telefono}/mensajes")
async def api_mensajes(telefono: str, autorizado: bool = Depends(verificar_acceso)):
    """Devuelve el historial completo de una conversación."""
    return await obtener_historial(telefono, limite=200)


@app.post("/api/conversaciones/{telefono}/pausar")
async def api_pausar(telefono: str, pausado: bool, autorizado: bool = Depends(verificar_acceso)):
    """Pausa o reanuda las respuestas automáticas del bot para un número."""
    await set_pausado(telefono, pausado)
    return {"status": "ok", "pausado": pausado}


@app.post("/api/conversaciones/{telefono}/enviar")
async def api_enviar(telefono: str, mensaje: str = Form(...), autorizado: bool = Depends(verificar_acceso)):
    """Envía un mensaje manual desde el panel (intervención humana)."""
    await guardar_mensaje(telefono, "assistant", mensaje)
    await proveedor.enviar_mensaje(telefono, mensaje)
    return {"status": "ok"}


@app.post("/api/conversaciones/{telefono}/archivo")
async def api_enviar_archivo(
    telefono: str,
    archivo: UploadFile = File(...),
    mensaje: str = Form(""),
    autorizado: bool = Depends(verificar_acceso),
):
    """Sube un archivo y lo envía por WhatsApp como documento (intervención humana)."""
    if not PUBLIC_URL:
        raise HTTPException(status_code=400, detail="PUBLIC_URL no configurado en el servidor")

    extension = Path(archivo.filename).suffix
    nombre_unico = f"{uuid.uuid4().hex}{extension}"
    ruta_destino = UPLOADS_DIR / nombre_unico

    contenido = await archivo.read()
    ruta_destino.write_bytes(contenido)

    url_archivo = f"{PUBLIC_URL}/uploads/{nombre_unico}"

    descripcion = mensaje or archivo.filename
    await guardar_mensaje(telefono, "assistant", f"[Archivo enviado: {archivo.filename}]" + (f" — {mensaje}" if mensaje else ""))
    await proveedor.enviar_documento(telefono, url_archivo, mensaje)

    return {"status": "ok", "url": url_archivo}


@app.post("/api/conversaciones/{telefono}/etiqueta")
async def api_etiqueta(telefono: str, etiqueta: str = "", autorizado: bool = Depends(verificar_acceso)):
    """Asigna o quita una etiqueta de clasificación a una conversación."""
    await set_etiqueta(telefono, etiqueta or None)
    return {"status": "ok", "etiqueta": etiqueta or None}


@app.delete("/api/conversaciones/{telefono}")
async def api_eliminar_conversacion(telefono: str, autorizado: bool = Depends(verificar_acceso)):
    """Elimina por completo una conversación (mensajes y estado)."""
    await eliminar_conversacion(telefono)
    return {"status": "ok"}
