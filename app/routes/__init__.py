from app.routes.admin import register_admin_routes
from app.routes.auth import register_auth_routes
from app.routes.public import register_public_routes


def register_routes(app):
    register_auth_routes(app)
    register_public_routes(app)
    register_admin_routes(app)
