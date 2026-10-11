from rest_framework.permissions import BasePermission


def can_view_all_submissions(user):
    """Use the same viewing permissions as the Django submission admin."""
    if not user.is_authenticated or not user.is_active:
        return False
    return user.is_superuser or (
        user.is_staff
        and (
            user.has_perm("book.view_paragraphsubmission")
            or user.has_perm("book.change_paragraphsubmission")
        )
    )


class IsSuperUser(BasePermission):
    """
    Allows access only to superusers.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser
