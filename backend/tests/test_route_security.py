import pathlib
import sys

from fastapi.routing import APIRoute

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from app.api import auth, availability, roster, users, workplace


def _find_route(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


def _has_route_dependency(route: APIRoute, dependency) -> bool:
    return any(dep.call == dependency for dep in route.dependant.dependencies)


def test_users_router_requires_authenticated_user():
    assert any(dep.dependency == auth.get_current_user for dep in users.router.dependencies)


def test_availability_router_requires_authenticated_user():
    assert any(dep.dependency == auth.get_current_user for dep in availability.router.dependencies)


def test_roster_router_requires_authenticated_user():
    assert any(dep.dependency == auth.get_current_user for dep in roster.router.dependencies)


def test_workplace_router_does_not_define_router_level_auth():
    assert workplace.router.dependencies == []


def test_manager_routes_require_manager_dependency():
    protected_routes = [
        (roster.router, "/roster/generate", "POST"),
        (roster.router, "/roster/week/{week_start_date}", "DELETE"),
        (roster.router, "/roster/assign", "POST"),
        (roster.router, "/roster/unassign", "POST"),
        (roster.router, "/roster/shifts/upsert", "POST"),
        (workplace.router, "/workplace/constraints", "GET"),
        (workplace.router, "/workplace/constraints", "PUT"),
        (users.router, "/users/{user_id}", "DELETE"),
    ]
    for router, path, method in protected_routes:
        route = _find_route(router, path, method)
        assert _has_route_dependency(route, auth.require_manager)
