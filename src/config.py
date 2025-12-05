import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "dashboard.db"

class Config:
    SECRET_KEY = os.environ.get("BANBIF_DASHBOARD_SECRET", secrets.token_hex(16))
    DATABASE = str(DB_PATH)
    # Limite global de subida (500MB para videos de evidencia)
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024
    INITIAL_ADMIN_PASSWORD = os.environ.get("BANBIF_ADMIN_CODE")

# Limites especificos por tipo de archivo
MAX_ACTA_SIZE = 50 * 1024 * 1024      # 50MB para PDFs y MSGs
MAX_VIDEO_SIZE = 500 * 1024 * 1024    # 500MB para videos de evidencia

PROJECT_COLUMNS = [
    "record_id",
    "ubicacion",
    "nom_sede",
    "categoria_trab",
    "nombre_completo",
    "perfil_imagen",
    "marca",
    "modelo",
    "serial_num",
    "hostname",
    "ip_equipo",
    "email_trabajo",
    "fecha_estado",
    "estado",
    "estado_coordinacion",
    "estado_upgrade",
    "fecha_programada",
    "fecha_ejecucion",
    "notas",
]

STATUS_CHOICES = [
    "PROGRAMADO",
    "REPROGRAMADO",
    "EN PROCESO",
    "REALIZADO",
    "USER NO ASISTIO",
    "USER SIN RESPUESTA",
    "NO APLICA UPGRADE",
    "INCIDENCIA UPGRADE",
    "PENDIENTE",
]

DONE_STATUS = {"REALIZADO"}
IN_PROGRESS_STATUS = {"EN PROCESO", "PROGRAMADO", "REPROGRAMADO", "INCIDENCIA UPGRADE"}
PENDING_STATUS = {
    "PENDIENTE",
    "USER SIN RESPUESTA",
    "USER NO ASISTIO",
    "NO APLICA UPGRADE",
}

# Fases del proyecto
PROJECT_PHASES = {
    "FASE_1": {
        "nombre": "Fase 1 - Upgrade SO",
        "descripcion": "Solo Upgrade de Sistema Operativo (Windows 10 a Windows 11)",
        "categorias": ["UPGRADE + WIN11", "UPGRADE"],
        "color": "#0d6efd",
    },
    "FASE_2": {
        "nombre": "Fase 2 - Repotenciación",
        "descripcion": "Cambio de Disco Mecánico a Sólido, y cambio/aumento de RAM",
        "categorias": ["REPOTENCIACIÓN + WIN11", "REPOTENCIACION + WIN11", "REPOTENCIACION"],
        "color": "#198754",
    },
    "FASE_3": {
        "nombre": "Fase 3 - Equipo nuevo",
        "descripcion": "Reemplazo de equipo antiguo a equipo nuevo",
        "categorias": ["EQUIPO NUEVO", "REEMPLAZO"],
        "color": "#6f42c1",
    },
}

def get_phase_from_category(categoria: str) -> str:
    """Determina la fase a partir de la categoría de trabajo"""
    if not categoria:
        return None
    categoria_upper = categoria.strip().upper()
    for phase_key, phase_data in PROJECT_PHASES.items():
        for cat in phase_data["categorias"]:
            if cat.upper() in categoria_upper or categoria_upper in cat.upper():
                return phase_key
    return None

CSV_FIELD_MAP = {
    "id": "record_id",
    "record_id": "record_id",
    "ubicacion": "ubicacion",
    "nom_sede": "nom_sede",
    "categoria_trab": "categoria_trab",
    "categoria": "categoria_trab",
    "nombre_completo": "nombre_completo",
    "nombre": "nombre_completo",
    "perfil_imagen": "perfil_imagen",
    "perfil": "perfil_imagen",
    "marca": "marca",
    "modelo": "modelo",
    "serial_num": "serial_num",
    "serialnumber": "serial_num",
    "hostname": "hostname",
    "ip_equipo": "ip_equipo",
    "email_trabajo": "email_trabajo",
    "correo": "email_trabajo",
    "fecha_estado": "fecha_estado",
    "estado": "estado",
    "estado_coordinacion": "estado_coordinacion",
    "estado_coordinacin": "estado_coordinacion",
    "estado_upgrade": "estado_upgrade",
    "fecha_programada": "fecha_programada",
    "fecha_programacion": "fecha_programada",
    "fecha_ejecucion": "fecha_ejecucion",
    "fecha_upgrade": "fecha_ejecucion",
    "notas": "notas",
}
