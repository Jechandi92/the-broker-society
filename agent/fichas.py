# agent/fichas.py — Mapeo de propiedades a sus fichas técnicas en PDF
# Generado por AgentKit

"""
Relaciona el identificador de cada propiedad con el archivo PDF de su ficha técnica
ubicado en knowledge/Fichas/. Estos archivos se sirven públicamente en /fichas/.
"""

FICHAS = {
    "casa_sac_franco": "Ficha Casa SAC Franco.pdf",
    "casa_montes_de_ame": "Casa Montes de Ame FT.pdf",
    "casa_44": "Ficha Casa 44 YCC.pdf",
    "casa_banqueta": "Casa Banqueta.pdf",
    "departamento_la_vista": "Ficha Tecnica La Vista.pdf",
    "departamento_atlantida": "FT DP Atlantida.pdf",
    "townhouse_almoara": "Ficha Tecnica TH Almoara (1).pdf",
    "terreno_kikteil": "Tno Kikteil.pdf",
    "terreno_turena": "FT Turena.pdf",
    "san_ignacio_25ha": "San Ignacio 25ha FT SD.pdf",
    "tixcacal": "Tixcacal FT (1).pdf",
}


def obtener_archivo_ficha(propiedad: str) -> str | None:
    """Retorna el nombre del archivo PDF de la ficha técnica de una propiedad, o None si no existe."""
    return FICHAS.get(propiedad)
