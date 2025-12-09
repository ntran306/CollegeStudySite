from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Class


@require_http_methods(["POST"])
def create_class(request):
    """API endpoint to create a new class dynamically"""
    try:
        data = json.loads(request.body)
        class_name = data.get('name', '').strip()
        
        if not class_name:
            return JsonResponse({'error': 'Class name is required'}, status=400)
        
        # Check if class already exists (case-insensitive)
        existing = Class.objects.filter(name__iexact=class_name).first()
        if existing:
            return JsonResponse({'id': existing.id, 'name': existing.name})
        
        # Create new class
        new_class = Class.objects.create(name=class_name)
        return JsonResponse({'id': new_class.id, 'name': new_class.name}, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)