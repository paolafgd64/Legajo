from django.urls import path

from . import views


urlpatterns = [
    path('dashboard_admin/', views.dashboard_admin, name='dashboard_admin'),
    path('usuarios_admin/', views.usuarios_admin, name='usuarios_admin'),
    path('carga_masiva_usuarios/', views.carga_masiva_usuarios, name='carga_masiva_usuarios'),
    path('inventario_admi/', views.inventario_admi_redirect, name='inventario_admi'),
    path('novedades_usuarios/', views.novedades_usuarios, name='novedades_usuarios'),
    path('perfil_admin/', views.perfil_admin, name='perfil_admin'),
    path('api/admin/dashboard/reported-users', views.api_admin_reported_users, name='api_admin_reported_users'),
    path('api/admin/dashboard/completed-exchanges', views.api_admin_completed_exchanges, name='api_admin_completed_exchanges'),
    path('api/admin/reportes-usuarios', views.api_admin_user_reports, name='api_admin_user_reports'),
    path('api/admin/reportes-usuarios/<int:report_id>', views.api_admin_update_user_report, name='api_admin_update_user_report'),
    path('api/admin/usuarios', views.api_admin_users, name='api_admin_users'),
]
