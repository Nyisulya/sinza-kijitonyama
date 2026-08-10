from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_member, name='register_member'),
    path('rsvp/<int:ibada_id>/', views.submit_rsvp, name='submit_rsvp'),
    path('schedule/', views.schedule, name='schedule'),
    path('dashboard/', views.leader_dashboard, name='leader_dashboard'),
    path('dashboard/sms/<int:ibada_id>/', views.trigger_sms, name='trigger_sms'),
    path('dashboard/sms/reminder/<int:ibada_id>/', views.send_rsvp_reminder, name='send_rsvp_reminder'),
    path('dashboard/ibada/create/', views.create_ibada, name='create_ibada'),
    path('dashboard/attendance/<int:ibada_id>/', views.take_attendance, name='take_attendance'),
    path('dashboard/attendance/<int:ibada_id>/save/', views.save_attendance, name='save_attendance'),
    path('dashboard/login/', views.leader_login, name='leader_login'),
    path('dashboard/attendance/history/', views.attendance_history, name='attendance_history'),
    path('dashboard/sms-settings/', views.sms_settings, name='sms_settings'),
    path('dashboard/sms-logs/', views.sms_logs, name='sms_logs'),
    path('dashboard/members/', views.members_list, name='members_list'),
    path('dashboard/members/<int:member_id>/toggle/', views.toggle_member_active, name='toggle_member_active'),
]
