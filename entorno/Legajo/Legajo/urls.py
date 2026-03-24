"""
URL configuration for Legajo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from web import views

urlpatterns = [
    path('', views.index, name='index'),
    path('admin/', admin.site.urls),
    path('chats/', views.chats, name='chats'),
    path('crear_cuenta/', views.crear_cuenta, name='crear_cuenta'),
    path('dashboard_admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard_usuario/', views.dashboard_usuario, name='dashboard_usuario'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('inventario_admi/', views.inventario_admi, name='inventario_admi'),
    path('inventario/', views.inventario, name='inventario'),
    path('login/', views.login, name='login'),
    path('notificaciones/', views.notificaciones, name='notificaciones'),
    path('novedades_usuarios/', views.novedades_usuarios, name='novedades_usuarios'),
    path('perfil_admin/', views.perfil_admin, name='perfil_admin'),
    path('perfil/', views.perfil, name='perfil'),
    path('registrar_libro/', views.registrar_libro, name='registrar_libro'),
    path('reporte_libros/', views.reporte_libros, name='reporte_libros'),
    path('reset_password/', views.reset_password, name='reset_password'),
<<<<<<< HEAD
    path('api/usuarios/', views.api_usuarios, name='api_usuarios'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/me/', views.api_me, name='api_me'),



=======
    path('api/usuarios', views.api_usuarios, name='api_usuarios'),
    path('api/auth/login', views.api_login, name='api_login'),
>>>>>>> 00e45309638ed4bf1e4ae15a6b5121f5aa5736dd


]
