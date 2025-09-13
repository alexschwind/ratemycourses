from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.views.generic.base import TemplateView

from courses import views as cviews

urlpatterns = [
    # Custom admin views must come before admin.site.urls
    path("admin/courses/upload-csv/", cviews.upload_courses_csv, name="upload_courses_csv"),
    
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path("accounts/profile/", TemplateView.as_view(template_name="profile.html"), name="profile"),
    path("accounts/profile/edit/", cviews.edit_profile, name="edit_profile"),
    path("accounts/profile/reset-weights/", cviews.reset_profile_weights, name="reset_profile_weights"),
    
    path("", cviews.CourseListView.as_view(), name="home"),

    path("courses/<slug:slug>/", cviews.course_detail, name="course_detail"),
    path("courses/<slug:slug>/rate/", cviews.add_rating, name="rate_course"),
    
    # User rating management
    path("my-ratings/", cviews.my_ratings, name="my_ratings"),
    path("ratings/<int:rating_id>/edit/", cviews.edit_rating, name="edit_rating"),
    path("ratings/<int:rating_id>/delete/", cviews.delete_rating, name="delete_rating"),
    path("ratings/<int:rating_id>/flag/", cviews.flag_rating, name="flag_rating"),
    
    # Legal pages
    path("impressum/", cviews.ImpressumView.as_view(), name="impressum"),
    path("privacy/", cviews.PrivacyView.as_view(), name="privacy"),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
