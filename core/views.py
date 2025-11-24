from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@login_required
def health_check(request):
    """Simple health check endpoint."""
    return JsonResponse({'status': 'ok'})


