# BanBif Upgrade Dashboard

Dashboard para gestionar el proyecto de upgrade a Windows 11 de BanBif. Permite visualizar el estado del proyecto, gestionar inventario de componentes, actas de conformidad, repotenciaciones y destruccion de discos.

## Fases del Proyecto

- **Fase 1**: Solo Upgrade de Sistema Operativo (Windows 10 a Windows 11)
- **Fase 2**: Repotenciacion (cambio de Disco Mecanico a Solido, y cambio y/o aumento de RAM)
- **Fase 3**: Equipo antiguo a equipo nuevo

## Requisitos

- Python 3.10+
- SQLite 3
- pip (gestor de paquetes de Python)

## Instalacion

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd src

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Configuracion

### Variables de Entorno

Crear un archivo `.env` o configurar las siguientes variables:

| Variable | Descripcion | Valor por defecto |
|----------|-------------|-------------------|
| `SECRET_KEY` | Clave secreta para sesiones Flask | (generada automaticamente) |
| `DATABASE` | Ruta a la base de datos SQLite | `dashboard.db` |

### Base de Datos

La base de datos se inicializa automaticamente al iniciar la aplicacion. Para reinicializar manualmente:

```bash
flask init-db
```

## Ejecucion

```bash
# Desarrollo
python app.py

# O usando Flask CLI
flask run --port 5000
```

La aplicacion estara disponible en `http://localhost:5000`

## Estructura del Proyecto

```
src/
  app.py                 # Punto de entrada de la aplicacion
  config.py              # Configuracion y constantes
  dashboard.db           # Base de datos SQLite

  controllers/           # Controladores (rutas)
    __init__.py
    admin.py             # Carga de datos y gestion de usuarios
    auth.py              # Autenticacion (login/logout)
    conformity.py        # Gestion de actas de conformidad
    dashboard.py         # Dashboard principal
    destruction.py       # Panel de destruccion de discos
    inventory.py         # Inventario de componentes
    repotentiation.py    # Historial de repotenciaciones

  models/                # Modelos de datos
    __init__.py
    component.py         # RAM y SSD
    conformity.py        # Actas de conformidad
    database.py          # Conexion a BD
    destruction.py       # Destruccion de discos
    project.py           # Registros del proyecto
    repotentiation.py    # Repotenciaciones
    user.py              # Usuarios

  templates/             # Plantillas HTML (Jinja2)
    base.html
    login.html
    conformity/
    dashboard/
    destruction/
    inventory/
    repotentiation/

  static/                # Archivos estaticos
    css/
    js/

  uploads/               # Archivos subidos
    actas/               # PDFs y MSGs de conformidad
    destruccion/         # Videos de evidencia

  utils/                 # Utilidades
    decorators.py        # Decoradores (@login_required, @admin_required)
    helpers.py           # Funciones auxiliares
```

## Modulos

### Dashboard

Panel principal con visualizacion del progreso del proyecto:
- Grafico de progreso por categoria
- Tabla de registros con filtros por estado, fase, y busqueda
- Contadores por fase del proyecto

### Inventario de Componentes

Gestion de unidades de RAM y SSD con estados:
- **Por entregar**: Unidades reservadas pero no entregadas (gris)
- **Instalado**: Unidades instaladas en equipos (verde)
- **Por asignar**: Unidades entregadas sin instalar (amarillo)
- **Defectuoso**: Unidades con fallas (rojo)

Rutas: `/inventario/`

### Actas de Conformidad

Subida y visualizacion de actas de conformidad:
- Soporta archivos PDF y MSG (maximo 50MB)
- Vinculacion con registros del proyecto
- Previsualizacion de documentos

Rutas: `/actas/`

### Repotenciacion

Historial de cambios de componentes en equipos:
- Registro de RAM antes/despues
- Registro de disco antes/despues
- Busqueda por serial de equipo o componente
- Seguimiento de componentes extraidos

Rutas: `/repotenciacion/`

### Destruccion de Discos

Panel de gestion de destruccion de discos:
- Estados: Pendiente, Programado, En proceso, Destruido, Certificado
- Subida de videos de evidencia (MP4, AVI, MOV, MKV, WEBM) - maximo 500MB
- Generacion de certificados de destruccion

Rutas: `/destruccion/`

## Limites de Subida de Archivos

| Tipo | Formatos | Limite |
|------|----------|--------|
| Actas de conformidad | PDF, MSG | 50 MB |
| Videos de evidencia | MP4, AVI, MOV, MKV, WEBM | 500 MB |

## Roles de Usuario

- **admin**: Acceso completo (crear, editar, eliminar)
- **standard**: Solo lectura

### Usuario por defecto

- Usuario: `admin`
- Contrasena: `admin`

## API Endpoints

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/api/summary` | GET | Resumen del dashboard |
| `/api/records` | GET | Registros filtrados |
| `/inventario/api/summary` | GET | Resumen de inventario |
| `/destruccion/api/summary` | GET | Resumen de destruccion |

## Tecnologias

- **Backend**: Flask (Python)
- **Base de datos**: SQLite
- **Frontend**: Bootstrap 5, Chart.js
- **Plantillas**: Jinja2

## Desarrollo

### Agregar nuevos modulos

1. Crear modelo en `models/`
2. Agregar `ensure_table()` al modelo
3. Registrar tabla en `models/database.py` -> `init_db()`
4. Crear controlador en `controllers/`
5. Registrar blueprint en `controllers/__init__.py` y `app.py`
6. Crear templates en `templates/<modulo>/`
7. Agregar enlace en `templates/base.html`

### Migraciones de BD

Para agregar columnas a tablas existentes:

```python
@staticmethod
def ensure_new_column(db):
    try:
        db.execute("ALTER TABLE tablename ADD COLUMN columnname TYPE DEFAULT value")
        db.commit()
    except sqlite3.OperationalError:
        pass  # La columna ya existe
```

## Licencia

Proyecto interno de BanBif - Team Support
