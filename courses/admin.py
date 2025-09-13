from django.contrib import admin
from django.urls import reverse, path
from django.utils.html import format_html
from django.shortcuts import render
from django.contrib.admin import AdminSite
from .models import Course, Rating, RatingFlag, Visitor, Faculty, Institute, Fachgebiet

class RatingInline(admin.TabularInline):  # or admin.StackedInline if you prefer
    model = Rating
    extra = 0                      # don’t show empty extra rows
    ordering = ("-created_at",)
    autocomplete_fields = ("user",)  # helpful if you have many users
    fields = (
        "user", "rating", "year", "semester",
        "short_comment", "created_at", "updated_at",
    )
    readonly_fields = ("short_comment", "created_at", "updated_at")
    show_change_link = True        # link to the full Rating change form

    def short_comment(self, obj):
        if not obj.comment:
            return ""
        return (obj.comment[:80] + "…") if len(obj.comment) > 80 else obj.comment
    short_comment.short_description = "Comment"

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "course_count")
    search_fields = ("name", "code")
    readonly_fields = ("code",)
    
    def course_count(self, obj):
        return obj.courses.count()
    course_count.short_description = "Courses"

@admin.register(Institute)
class InstituteAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty", "code", "course_count")
    list_filter = ("faculty",)
    search_fields = ("name", "code", "faculty__name")
    autocomplete_fields = ("faculty",)
    
    def course_count(self, obj):
        return obj.courses.count()
    course_count.short_description = "Courses"

@admin.register(Fachgebiet)
class FachgebietAdmin(admin.ModelAdmin):
    list_display = ("name", "professor", "institute", "course_count")
    list_filter = ("institute__faculty", "institute")
    search_fields = ("name", "professor", "institute__name")
    autocomplete_fields = ("institute",)
    
    def course_count(self, obj):
        return obj.courses.count()
    course_count.short_description = "Courses"

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty", "institute", "fachgebiet", "professor", "rating_count")
    list_filter = ("fachgebiet__institute__faculty", "fachgebiet__institute", "fachgebiet", "fachgebiet__professor")
    search_fields = ("name", "fachgebiet__institute__faculty__name", "fachgebiet__institute__name", "fachgebiet__name", "fachgebiet__professor")
    autocomplete_fields = ("fachgebiet",)
    readonly_fields = ("slug", "faculty", "institute", "professor")
    inlines = [RatingInline]
    
    def rating_count(self, obj):
        return obj.ratings.count()
    rating_count.short_description = "Ratings"
    
    def changelist_view(self, request, extra_context=None):
        """Add custom context for the changelist view"""
        extra_context = extra_context or {}
        extra_context['upload_csv_url'] = reverse('upload_courses_csv')
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("course", "user", "rating", "year", "semester", "is_disabled", "created_at", "flag_count")
    list_filter = ("rating", "year", "semester", "is_disabled")
    search_fields = ("course__name", "user__email", "comment")
    autocomplete_fields = ("course", "user")
    actions = ["disable_ratings", "enable_ratings"]
    
    def flag_count(self, obj):
        count = obj.flags.count()
        if count > 0:
            return format_html('<span style="color: red; font-weight: bold;">{} flag(s)</span>', count)
        return "0"
    flag_count.short_description = "Flags"
    
    def disable_ratings(self, request, queryset):
        updated = queryset.update(is_disabled=True)
        self.message_user(request, f"{updated} rating(s) disabled.")
    disable_ratings.short_description = "Disable selected ratings"
    
    def enable_ratings(self, request, queryset):
        updated = queryset.update(is_disabled=False)
        self.message_user(request, f"{updated} rating(s) enabled.")
    enable_ratings.short_description = "Enable selected ratings"


@admin.register(RatingFlag)
class RatingFlagAdmin(admin.ModelAdmin):
    list_display = ("rating", "flagged_by", "created_at", "rating_course")
    list_filter = ("created_at",)
    search_fields = ("rating__course__name", "flagged_by__email", "reason")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("rating", "flagged_by")
    
    fieldsets = (
        ("Flag Details", {
            "fields": ("rating", "flagged_by", "reason")
        }),
        ("Timestamps", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )
    
    def rating_course(self, obj):
        return obj.rating.course.name
    rating_course.short_description = "Course"


class VisitorAdmin(admin.ModelAdmin):
    list_display = ("ip_address", "path", "user", "status_code", "created_at")
    list_filter = ("status_code", "method", "created_at", "user__isnull")
    search_fields = ("ip_address", "path", "user_agent", "user__email")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Request Details", {
            "fields": ("ip_address", "path", "query_string", "method", "status_code")
        }),
        ("User Information", {
            "fields": ("user", "session_key")
        }),
        ("Technical Details", {
            "fields": ("user_agent", "referer"),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def has_add_permission(self, request):
        # Visitors are created automatically by middleware
        return False


class VisitorStatsAdmin(admin.ModelAdmin):
    """Custom admin for visitor statistics dashboard"""
    
    def changelist_view(self, request, extra_context=None):
        """Override changelist to show visitor statistics"""
        extra_context = extra_context or {}
        
        # Get visitor statistics
        stats_7d = Visitor.get_daily_stats(days=7)
        stats_30d = Visitor.get_daily_stats(days=30)
        
        # Get recent visitors
        recent_visitors = Visitor.objects.select_related('user').order_by('-created_at')[:50]
        
        extra_context.update({
            'stats_7d': stats_7d,
            'stats_30d': stats_30d,
            'recent_visitors': recent_visitors,
            'title': 'Visitor Statistics',
        })
        
        return render(request, 'admin/courses/visitor/stats.html', extra_context)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# Register both admin views
admin.site.register(Visitor, VisitorStatsAdmin)