from django.contrib import admin
from .models import Course, Rating

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

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("course", "user", "rating", "year", "semester", "created_at")
    list_filter = ("rating", "year", "semester")
    search_fields = ("course__name", "user__email", "comment")
    autocomplete_fields = ("course", "user")