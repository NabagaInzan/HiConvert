from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('process', views.process_files, name='process_files'),
    path('view/<str:file_id>', views.view_file, name='view_file'),
    path('download/<str:file_id>', views.download_file, name='download_file'),
]
