from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('crear_cuenta/', views.crear_cuenta, name='crear_cuenta'),
    path('dashboard_usuario/', views.dashboard_usuario, name='dashboard_usuario'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('inventario/', views.inventario, name='inventario'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('notificaciones/', views.notificaciones, name='notificaciones'),
    path('perfil/', views.perfil, name='perfil'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('activar/<uidb64>/<token>/', views.activate_account, name='activate_account'),
    path('api/usuarios', views.api_usuarios, name='api_usuarios'),
    path('api/usuarios/', views.api_usuarios, name='api_usuarios_slash'),
    path('api/login/', views.api_login, name='api_login_legacy'),
    path('api/auth/login', views.api_login, name='api_login'),
    path('api/me/', views.api_me, name='api_me'),
    path('api/auth/me', views.api_me, name='api_auth_me'),
    path('api/perfil/estadisticas', views.api_profile_stats, name='api_profile_stats'),
    path('api/reportes-usuarios', views.api_user_reports, name='api_user_reports'),
]

