from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),            #homepage
    path('accounts/', include('accounts.urls')), #user accounts
    path('tutoringsession/', include('tutoringsession.urls')), #tutoring sessions
    path('classes/', include('classes.urls')),
    #path('classes/', include('classes.urls')),   #classes
    #path('communication/', include('communication.urls')), #messaging system
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
