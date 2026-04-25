from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from core import views

urlpatterns = [
    path('', views.index_gateway),
    path('admin', views.admin_site),
    path('lbas', views.lbas_site),
    path('landing', views.landing_site),
    path('welcome', views.welcome_site),
    path('creators', views.creators_site),
    path('user-tablet', views.user_tablet_site),
    path('api/', include('api.urls')),

    # Serve Profile/ (uploaded photos) — works with BOTH runserver AND Waitress
    re_path(r'^Profile/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

    # Serve static files — works with BOTH runserver AND Waitress
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT or (settings.BASE_DIR / 'static')}),
]
