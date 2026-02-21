from reports.models import Report

def admin_context(request):
    if request.user.is_authenticated and request.user.is_staff:
        return {'pending_reports_count': Report.objects.filter(status='pending').count()}
    return {'pending_reports_count': 0}