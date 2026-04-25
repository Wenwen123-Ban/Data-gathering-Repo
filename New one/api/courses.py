import json
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .utils import parse_json_body, require_admin, unauth

_DEFAULT_COURSES = ['BSIT', 'BSAM', 'BSIS', 'BSCS', 'BSED', 'BSBA']
_COURSES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'courses.json')


def _load_courses():
    try:
        with open(_COURSES_FILE, 'r') as f:
            data = json.load(f)
            if isinstance(data, list) and data:
                return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return list(_DEFAULT_COURSES)


def _save_courses(courses):
    try:
        with open(_COURSES_FILE, 'w') as f:
            json.dump(courses, f)
    except Exception:
        pass


@csrf_exempt
def api_courses(request):
    if request.method == 'GET':
        return JsonResponse({
            'courses': _load_courses(),
            'hs_grades': [7, 8, 9, 10],
            'college_years': [1, 2, 3, 4],
        })
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def api_admin_courses(request):
    if not require_auth(request):
        return unauth()
    data = parse_json_body(request)
    if isinstance(data.get('courses'), list):
        courses = [str(c).strip() for c in data['courses'] if str(c).strip()]
        _save_courses(courses)
        return JsonResponse({'success': True, 'courses': courses})
    return JsonResponse({'success': False, 'message': 'Invalid data'}, status=400)
