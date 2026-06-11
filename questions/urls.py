from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "questions"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="questions:home"), name="logout"),
    path("questions/", views.question_list, name="question_list"),
    path("questions/new/", views.question_create, name="question_create"),
    path("questions/<int:pk>/edit/", views.question_update, name="question_update"),
    path("import/", views.import_questions_view, name="import"),
    path("references/", views.references, name="references"),
    path("settings/", views.settings_view, name="settings"),
    path("settings/backups/create/", views.create_backup_view, name="create_backup"),
    path("settings/backups/<int:pk>/restore/", views.restore_backup_view, name="restore_backup"),
]
