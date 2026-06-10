# agent/memory.py — Memoria de conversaciones con SQLite
# Generado por AgentKit

import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, Boolean, select, Integer, func
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentkit.db")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Mensaje(Base):
    """Modelo de mensaje en la base de datos."""
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Conversacion(Base):
    """Estado de cada conversación (pausa y etiqueta de clasificación)."""
    __tablename__ = "conversaciones"

    telefono: Mapped[str] = mapped_column(String(50), primary_key=True)
    pausado: Mapped[bool] = mapped_column(Boolean, default=False)
    etiqueta: Mapped[str | None] = mapped_column(String(30), nullable=True, default=None)


async def inicializar_db():
    """Crea las tablas si no existen y aplica migraciones simples."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Migración aparte: agregar columna 'etiqueta' si la tabla ya existía sin ella
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE conversaciones ADD COLUMN etiqueta VARCHAR(30)"))
    except Exception:
        pass


async def guardar_mensaje(telefono: str, role: str, content: str):
    """Guarda un mensaje en el historial de conversación."""
    async with async_session() as session:
        mensaje = Mensaje(
            telefono=telefono,
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        )
        session.add(mensaje)
        await session.commit()


async def obtener_historial(telefono: str, limite: int = 20) -> list[dict]:
    """
    Recupera los últimos N mensajes de una conversación.

    Args:
        telefono: Número de teléfono del cliente
        limite: Máximo de mensajes a recuperar (default: 20)

    Returns:
        Lista de diccionarios con role y content, en orden cronológico
    """
    async with async_session() as session:
        query = (
            select(Mensaje)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.timestamp.desc())
            .limit(limite)
        )
        result = await session.execute(query)
        mensajes = result.scalars().all()

        mensajes.reverse()

        return [
            {"role": msg.role, "content": msg.content}
            for msg in mensajes
        ]


async def limpiar_historial(telefono: str):
    """Borra todo el historial de una conversación."""
    async with async_session() as session:
        query = select(Mensaje).where(Mensaje.telefono == telefono)
        result = await session.execute(query)
        mensajes = result.scalars().all()
        for msg in mensajes:
            await session.delete(msg)
        await session.commit()


async def esta_pausado(telefono: str) -> bool:
    """Indica si el bot está pausado (modo humano) para este número."""
    async with async_session() as session:
        conv = await session.get(Conversacion, telefono)
        return conv.pausado if conv else False


async def set_pausado(telefono: str, pausado: bool):
    """Pausa o reanuda las respuestas automáticas del bot para este número."""
    async with async_session() as session:
        conv = await session.get(Conversacion, telefono)
        if conv is None:
            conv = Conversacion(telefono=telefono, pausado=pausado)
            session.add(conv)
        else:
            conv.pausado = pausado
        await session.commit()


async def set_etiqueta(telefono: str, etiqueta: str | None):
    """Asigna una etiqueta de clasificación a una conversación (o None para quitarla)."""
    async with async_session() as session:
        conv = await session.get(Conversacion, telefono)
        if conv is None:
            conv = Conversacion(telefono=telefono, pausado=False, etiqueta=etiqueta)
            session.add(conv)
        else:
            conv.etiqueta = etiqueta
        await session.commit()


async def eliminar_conversacion(telefono: str):
    """Borra por completo una conversación: mensajes y su estado."""
    async with async_session() as session:
        query = select(Mensaje).where(Mensaje.telefono == telefono)
        mensajes = (await session.execute(query)).scalars().all()
        for msg in mensajes:
            await session.delete(msg)

        conv = await session.get(Conversacion, telefono)
        if conv is not None:
            await session.delete(conv)

        await session.commit()


async def listar_conversaciones() -> list[dict]:
    """Lista todas las conversaciones con su último mensaje y estado de pausa."""
    async with async_session() as session:
        subq = (
            select(Mensaje.telefono, func.max(Mensaje.timestamp).label("ultimo"))
            .group_by(Mensaje.telefono)
            .order_by(func.max(Mensaje.timestamp).desc())
        )
        result = await session.execute(subq)
        filas = result.all()

        conversaciones = []
        for telefono, ultimo in filas:
            conv = await session.get(Conversacion, telefono)

            ultimo_mensaje_query = (
                select(Mensaje)
                .where(Mensaje.telefono == telefono)
                .order_by(Mensaje.timestamp.desc())
                .limit(1)
            )
            ultimo_msg = (await session.execute(ultimo_mensaje_query)).scalar_one()

            conversaciones.append({
                "telefono": telefono,
                "ultimo_mensaje": ultimo_msg.content,
                "ultimo_role": ultimo_msg.role,
                "fecha": ultimo.isoformat(),
                "pausado": conv.pausado if conv else False,
                "etiqueta": conv.etiqueta if conv else None,
            })

        return conversaciones
