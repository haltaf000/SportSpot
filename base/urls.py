from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about_page, name="about"),
    path('rule/', views.rule_page, name="rule"),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('register/', views.register_page, name='register'),
    path('user/<str:pk>/', views.user_page, name='profile'),
    path('account/', views.account_page, name='account'),
    path('event/<str:pk>/', views.event_page, name='event'),
    path('confirmation/<str:pk>/', views.registration_conformation, name='confirmation'),
    path('project/<str:pk>/', views.project_submission, name='project_submission'),
    path('update/<str:pk>/', views.update_submission, name="update_submission")
]
