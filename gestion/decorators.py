from functools import wraps
from django.http import HttpResponseForbidden


def role_required(entite_getter, allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            entite = entite_getter(request, *args, **kwargs)
            if entite is None:
                return HttpResponseForbidden("Entité introuvable.")

            from .utils import user_has_role
            if not user_has_role(request.user, entite, allowed_roles):
                return HttpResponseForbidden("Accès refusé.")

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator