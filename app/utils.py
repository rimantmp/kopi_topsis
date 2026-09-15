from functools import wraps
from flask import abort
from flask_login import current_user


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def roles_required(*role_names):
    """Batasi halaman ke role tertentu tanpa menggandakan pemeriksaan akses."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            role_name = current_user.role.name if current_user.is_authenticated and current_user.role else None
            if role_name not in role_names:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator
