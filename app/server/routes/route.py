from flask import Blueprint
from controllers.route_controller import compute_route

route_bp = Blueprint("route", __name__)

@route_bp.post("/")
def post_route():
    return compute_route()