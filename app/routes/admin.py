from app.routes.admin_meetings import register_admin_meeting_routes
from app.routes.admin_motions import register_admin_motion_routes
from app.routes.admin_results import register_admin_result_routes
from app.routes.admin_voters import register_admin_voter_routes


def register_admin_routes(app):
    register_admin_meeting_routes(app)
    register_admin_motion_routes(app)
    register_admin_voter_routes(app)
    register_admin_result_routes(app)
