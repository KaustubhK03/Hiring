from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

# All the main project urls are defined here
urlpatterns = [
    path('', views.landing_page, name="landing_page"),
    path('sign-up/', views.sign_up, name='sign_up'),
    path('logout/', views.logout_view, name="logout"),
    path("progress/<task_id>/", views.task_status, name="task_status"),
    path("user-profile/", views.user_profile, name="user-profile"),
    path('home/', views.home, name='automated_resume-home'),
    path('home/instructions/', views.display_instructions, name="automated_resume_instructions"),
    path('reset-password/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='automated_resume/reset_password_done.html'), name='password_reset_done'),
    path('admin-dashboard/', views.admin_home, name='admin_dashboard'),
    path('admin-dashboard/two', views.dashboard_page2, name='admin_dashboard_page2'),
    path('admin-dashboard/settings', views.dashboard_settings, name="admin-settings"),
    path('save-admin-settings/', views.save_admin_settings, name='save_admin_settings'),
    path('delete-user-data/', views.delete_user_data, name='delete_user_data'),
    path('home/instructions/results/', views.results, name="results-page"),
    path('setup/', views.setup_for_coding_with_instructions, name="setup-page"),
    path('setup/coding/', views.route_to_coding_test, name="coding_page"),
    path('save-recording/', views.save_recording, name='save_recording'),
    path("home/instructions/save_flags/", views.save_flags, name="save_flags"),
    path('setup/coding/save_flags/', views.save_flags, name='save_flags_coding'), # Save function but different URL
    path('verify-email/', views.send_otp_view, name='verify_email'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('setup/coding/get_code_from_frontend/', views.get_code_from_frontend, name='get_code_from_frontend'),
    path('setup/coding/run_test_cases/', views.run_test_cases, name='run_test_cases'),
    path('setup/coding/submit_code/', views.submit_code, name='submit_code'),
    path('setup/coding/get_result/', views.get_result, name='get_result'),
]