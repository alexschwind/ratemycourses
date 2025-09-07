from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from .models import Course, Rating
from .forms import RatingForm
from django.db.models import Avg, Count, Value
from django.db.models.functions import Coalesce

from django.views.generic import ListView
from .models import Course

class CourseListView(ListView):
    model = Course
    template_name = "index.html"
    context_object_name = "courses"
    ordering = ["name"]
    paginate_by = 20

    def get_queryset(self):
        q = (self.request.GET.get("q") or "").strip()
        sort = (self.request.GET.get("sort") or "name").lower()

        qs = Course.objects.all()

        if q:
            qs = qs.filter(name__icontains=q)

        # Annotate averages & counts for listing and sorting
        qs = qs.annotate(
            avg_rating=Avg("ratings__rating"),
            rating_count=Count("ratings"),
        )

        # Sorting
        if sort == "rating":           # highest first
            qs = qs.order_by(Coalesce("avg_rating", Value(0)).desc(), "name")
        elif sort == "rating_asc":     # lowest first
            qs = qs.order_by(Coalesce("avg_rating", Value(0)).asc(), "name")
        else:                          # default: name
            qs = qs.order_by("name")

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx["sort"] = (self.request.GET.get("sort") or "name").lower()
        return ctx

def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    qs = course.ratings.select_related("user")
    agg = qs.aggregate(avg=Avg("rating"), count=Count("id"))
    return render(
        request,
        "courses/course_detail.html",
        {"course": course, "ratings": qs, "avg": agg["avg"], "count": agg["count"]},
    )

@login_required
def add_rating(request, slug):
    course = get_object_or_404(Course, slug=slug)

    if request.method == "POST":
        form = RatingForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    rating_obj, created = Rating.objects.update_or_create(
                        course=course,
                        user=request.user,
                        year=data["year"],
                        semester=data["semester"],
                        defaults={
                            "rating": data["rating"],
                            "comment": data["comment"],
                        },
                    )
                messages.success(request, "Your rating has been saved.")
                return redirect("course_detail", slug=course.slug)
            except IntegrityError:
                messages.error(request, "You already rated this course for that term.")
    else:
        form = RatingForm()

    return render(request, "courses/rate_course.html", {"course": course, "form": form})