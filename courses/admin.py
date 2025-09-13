from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Course, Rating, RatingFlag

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

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    readonly_fields = ("slug",)
    inlines = [RatingInline]
    
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