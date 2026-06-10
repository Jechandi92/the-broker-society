# tests/test_local.py — Simulador de chat en terminal
# Generado por AgentKit

import asyncio
import sys
import os

# Forzar UTF-8 en Windows para soportar emojis
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, limpiar_historial

TELEFONO_TEST = "test-local-001"


async def main():
    """Loop principal del chat de prueba."""
    await inicializar_db()

    print()
    print("=" * 55)
    print("   Doppler — Test Local (AgentKit)")
    print("=" * 55)
    print()
    print("  Escribe mensajes como si fueras un prospecto.")
    print("  Comandos especiales:")
    print("    'limpiar'  — borra el historial")
    print("    'salir'    — termina el test")
    print()
    print("-" * 55)
    print()

    while True:
        try:
            mensaje = input("Tu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nTest finalizado.")
            break

        if not mensaje:
            continue

        if mensaje.lower() == "salir":
            print("\nTest finalizado.")
            break

        if mensaje.lower() == "limpiar":
            await limpiar_historial(TELEFONO_TEST)
            print("[Historial borrado]\n")
            continue

        historial = await obtener_historial(TELEFONO_TEST)

        print("\nLea: ", end="", flush=True)
        respuesta, archivo_ficha, motivo_escalacion = await generar_respuesta(mensaje, historial)
        print(respuesta)
        if archivo_ficha:
            print(f"[Adjuntaría ficha técnica: {archivo_ficha}]")
        if motivo_escalacion:
            print(f"[Escalaría a humano: {motivo_escalacion}]")
        print()

        await guardar_mensaje(TELEFONO_TEST, "user", mensaje)
        await guardar_mensaje(TELEFONO_TEST, "assistant", respuesta)


if __name__ == "__main__":
    asyncio.run(main())
