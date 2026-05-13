from rest_framework.permissions import DjangoModelPermissions, IsAuthenticated


class ModelPermissions(DjangoModelPermissions):
    """
    Extends DjangoModelPermissions to also enforce the auto-generated
    `view_<model>` permission on GET/HEAD requests.

    Django creates four permissions per model automatically:
        add_<model>, change_<model>, delete_<model>, view_<model>

    Assign these to auth.Group instances via the admin and add staff
    CustomUser accounts to the appropriate groups. No code changes are
    needed when permission requirements change — just adjust groups in
    the admin panel.
    """

    perms_map = {
        **DjangoModelPermissions.perms_map,
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
    }


class IsSystemUser(IsAuthenticated):
    """
    Passes only for authenticated CustomUsers that have an active SystemUser
    profile record. Devices and anonymous users are rejected.
    Used to gate endpoints that any staff member can read, regardless of
    their specific permissions.
    """

    message = "You must be an active system user to access this resource."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if hasattr(request, "_is_system_user"):
            return request._is_system_user
        from .models import CustomUser

        user = request.user
        result = (
            isinstance(user, CustomUser)
            and bool(getattr(user, "user_type", ""))
            and user.is_active
        )
        request._is_system_user = result
        return result
