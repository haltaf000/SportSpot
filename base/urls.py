from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Core URLs
    path('', views.home, name='home'),
    path('account/', views.account_page, name='account'),
    path('account/edit/', views.edit_account, name='edit-account'),
    path('rules/', views.rule_page, name='rules'),
    path('about/', views.about_page, name='about'),
    path('teams/', views.team_list, name='teams'),
    path('user/<int:pk>/', views.user_page, name='user-profile'),
    
    # Authentication URLs
    path('login/', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('verify-email/<str:token>/', views.verify_email, name='verify-email'),
    path('logout/', views.logout_user, name='logout'),
    
    # Password Reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='authentication/password_reset.html',
             email_template_name='authentication/password_reset_email.html',
             subject_template_name='authentication/password_reset_subject.txt'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='authentication/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='authentication/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='authentication/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    
    # Event URLs
    path('create-event/', views.create_event, name='create-event'),
    path('event/<int:pk>/', views.event, name='event'),
    path('event/<int:pk>/edit/', views.edit_event, name='edit-event'),
    
    # Team URLs
    path('event/<int:event_id>/create-team/', views.create_team, name='create-team'),
    path('team/<int:pk>/', views.team_detail, name='team-detail'),
    path('team/<int:pk>/edit/', views.edit_team, name='edit-team'),
    path('team/<int:pk>/join/', views.join_team, name='join-team'),
    path('team/<int:pk>/leave/', views.leave_team, name='leave-team'),
    path('team/<int:pk>/delete/', views.delete_team, name='delete-team'),
    
    # Draft URLs
    path('event/<int:pk>/draft/', views.live_draft, name='live-draft'),
    path('event/<int:pk>/draft/start/', views.start_draft, name='start-draft'),
    path('event/<int:pk>/draft/stop/', views.stop_draft, name='stop-draft'),
    path('event/<int:pk>/manage-teams/', views.manage_teams, name='manage-teams'),
    
    # Player Registration URL
    path('event/<int:pk>/register-player/', views.register_player, name='register-player'),

    # Staff Management URLs
    path('manage/event/<int:event_id>/teams/', views.admin_manage_teams, name='admin-manage-teams'),
    path('manage/team/<int:team_id>/delete/', views.admin_delete_team, name='admin-delete-team'),
    path('manage/team/<int:team_id>/player/<int:player_id>/remove/', views.admin_remove_player, name='admin-remove-player'),
]
