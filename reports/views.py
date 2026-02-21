from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.decorators import login_required_custom
from .models import Report, TARGET_TYPES, REPORT_REASONS


@login_required_custom
def submit_report(request):
    if request.method == 'POST':
        target_type = request.POST.get('target_type', '')
        target_id = request.POST.get('target_id', '').strip()
        reason = request.POST.get('reason', '')
        description = request.POST.get('description', '').strip()

        errors = []
        if not target_type:
            errors.append("Target type required.")
        if not target_id or not target_id.isdigit():
            errors.append("Valid target ID required.")
        if not reason:
            errors.append("Reason required.")
        if not description:
            errors.append("Description required.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            r = Report(
                reporter=request.user,
                target_type=target_type,
                target_id=int(target_id),
                reason=reason,
                description=description,
            )
            if request.FILES.get('evidence'):
                r.evidence = request.FILES['evidence']
            r.save()
            messages.success(request, "Report submitted. Our team will review it.")
            return redirect('feed')

    return render(request, 'reports/submit.html', {
        'target_types': TARGET_TYPES,
        'reasons': REPORT_REASONS,
    })