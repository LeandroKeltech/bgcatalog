"""Public site integrations exposed to templates."""
from django.conf import settings


def analytics(request):
    project_id = settings.CLARITY_PROJECT_ID
    if settings.DEBUG or getattr(request.user, 'is_staff', False):
        project_id = ''
    return {'clarity_project_id': project_id}
