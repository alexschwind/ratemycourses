from django.contrib import admin
from django.urls import path, include

from django.views.generic.base import TemplateView

from courses import views as cviews

urlpatterns = [
    # Custom admin views must come before admin.site.urls
    path("admin/courses/upload-csv/", cviews.upload_courses_csv, name="upload_courses_csv"),
    
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path("accounts/profile/", TemplateView.as_view(template_name="profile.html"), name="profile"),
    
    path("", cviews.CourseListView.as_view(), name="home"),

    path("courses/<slug:slug>/", cviews.course_detail, name="course_detail"),
    path("courses/<slug:slug>/rate/", cviews.add_rating, name="rate_course"),
    
    # Legal pages
    path("impressum/", cviews.ImpressumView.as_view(), name="impressum"),
    path("privacy/", cviews.PrivacyView.as_view(), name="privacy"),
]
