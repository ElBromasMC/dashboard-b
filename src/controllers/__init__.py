from controllers.auth import auth_bp
from controllers.dashboard import dashboard_bp
from controllers.admin import admin_bp
from controllers.inventory import inventory_bp
from controllers.conformity import conformity_bp
from controllers.repotentiation import repotentiation_bp
from controllers.destruction import destruction_bp
from controllers.reports import reports_bp
from controllers.bulk_upload import bulk_upload_bp

__all__ = [
    'auth_bp', 'dashboard_bp', 'admin_bp', 'inventory_bp',
    'conformity_bp', 'repotentiation_bp', 'destruction_bp',
    'reports_bp', 'bulk_upload_bp'
]
