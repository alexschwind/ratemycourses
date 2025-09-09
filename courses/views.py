from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from .models import Course, Rating
from .forms import RatingForm, CourseCSVUploadForm
from django.db.models import Avg, Count, Value
from django.db.models.functions import Coalesce
import csv
import io

from django.views.generic import ListView, TemplateView
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
    
    # Check if the current user has already rated this course
    user_has_rated = False
    if request.user.is_authenticated:
        user_has_rated = Rating.objects.filter(course=course, user=request.user).exists()
    
    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course, 
            "ratings": qs, 
            "avg": agg["avg"], 
            "count": agg["count"],
            "user_has_rated": user_has_rated
        },
    )

@login_required
def add_rating(request, slug):
    course = get_object_or_404(Course, slug=slug)
    # Check if user already has a rating for this course
    existing_rating = Rating.objects.filter(course=course, user=request.user).first()

    if request.method == "POST":
        form = RatingForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    if existing_rating:
                        # Update existing rating
                        existing_rating.rating = data["rating"]
                        existing_rating.comment = data["comment"]
                        existing_rating.year = data["year"]
                        existing_rating.semester = data["semester"]
                        existing_rating.save()
                        messages.success(request, "Your rating has been updated.")
                    else:
                        # Create new rating
                        Rating.objects.create(
                            course=course,
                            user=request.user,
                            rating=data["rating"],
                            comment=data["comment"],
                            year=data["year"],
                            semester=data["semester"],
                        )
                        messages.success(request, "Your rating has been saved.")
                return redirect("course_detail", slug=course.slug)
            except IntegrityError:
                messages.error(request, "You can only submit one rating per course.")
    else:
        # Pre-populate form with existing rating data if available
        if existing_rating:
            form = RatingForm(initial={
                'rating': existing_rating.rating,
                'comment': existing_rating.comment,
                'year': existing_rating.year,
                'semester': existing_rating.semester,
            })
        else:
            form = RatingForm()

    return render(request, "courses/rate_course.html", {
        "course": course, 
        "form": form, 
        "existing_rating": existing_rating
    })

class ImpressumView(TemplateView):
    template_name = "impressum.html"

class PrivacyView(TemplateView):
    template_name = "privacy.html"


def is_staff_user(user):
    """Check if user is staff/admin"""
    return user.is_staff


@user_passes_test(is_staff_user)
def upload_courses_csv(request):
    """Admin view to upload courses via CSV file"""
    if request.method == 'POST':
        form = CourseCSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            
            try:
                # Read and parse CSV
                content = csv_file.read().decode('utf-8')
                
                # First, try to detect if first row is a header by checking if it contains 'name'
                lines = content.strip().split('\n')
                first_line = lines[0] if lines else ""
                has_header = 'name' in first_line.lower()
                
                if has_header:
                    # Use DictReader for CSV with header
                    csv_reader = csv.DictReader(io.StringIO(content))
                    start_row = 2  # Skip header row
                else:
                    # Use regular reader for CSV without header
                    csv_reader = csv.reader(io.StringIO(content))
                    start_row = 1  # Start from first row
                
                created_courses = []
                skipped_courses = []
                errors = []
                
                with transaction.atomic():
                    for row_num, row in enumerate(csv_reader, start=start_row):
                        try:
                            # Get course name based on whether we have a header or not
                            if has_header:
                                # DictReader: get from 'name' column or first column
                                if 'name' in row and row['name'].strip():
                                    course_name = row['name'].strip()
                                elif row and list(row.values())[0].strip():
                                    course_name = list(row.values())[0].strip()
                                else:
                                    errors.append(f"Row {row_num}: Empty course name")
                                    continue
                            else:
                                # Regular reader: get from first column
                                if row and len(row) > 0 and row[0].strip():
                                    course_name = row[0].strip()
                                else:
                                    errors.append(f"Row {row_num}: Empty course name")
                                    continue
                            
                            # Create course if it doesn't exist
                            course, created = Course.objects.get_or_create(
                                name=course_name,
                                defaults={'name': course_name}
                            )
                            
                            if created:
                                created_courses.append(course_name)
                            else:
                                skipped_courses.append(course_name)
                                
                        except Exception as e:
                            errors.append(f"Row {row_num}: {str(e)}")
                
                # Prepare success message
                message_parts = []
                if created_courses:
                    message_parts.append(f"Successfully created {len(created_courses)} courses")
                if skipped_courses:
                    message_parts.append(f"Skipped {len(skipped_courses)} existing courses")
                if errors:
                    message_parts.append(f"Encountered {len(errors)} errors")
                
                if created_courses:
                    messages.success(request, "; ".join(message_parts))
                elif skipped_courses and not errors:
                    messages.info(request, "; ".join(message_parts))
                else:
                    messages.warning(request, "; ".join(message_parts))
                
                # Show detailed errors if any
                if errors:
                    for error in errors[:10]:  # Show first 10 errors
                        messages.error(request, error)
                    if len(errors) > 10:
                        messages.error(request, f"... and {len(errors) - 10} more errors")
                
                return redirect('admin:courses_course_changelist')
                
            except Exception as e:
                messages.error(request, f"Error processing CSV file: {str(e)}")
    else:
        form = CourseCSVUploadForm()
    
    return render(request, 'courses/upload_courses_csv.html', {'form': form})


@login_required
def my_ratings(request):
    """View to display all ratings by the current user"""
    ratings = Rating.objects.filter(user=request.user).select_related('course').order_by('-created_at')
    
    return render(request, 'courses/my_ratings.html', {
        'ratings': ratings
    })


@login_required
def edit_rating(request, rating_id):
    """View to edit an existing rating"""
    rating = get_object_or_404(Rating, id=rating_id, user=request.user)
    
    if request.method == "POST":
        form = RatingForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            rating.rating = data["rating"]
            rating.comment = data["comment"]
            rating.year = data["year"]
            rating.semester = data["semester"]
            rating.save()
            messages.success(request, "Your rating has been updated.")
            return redirect("my_ratings")
    else:
        form = RatingForm(initial={
            'rating': rating.rating,
            'comment': rating.comment,
            'year': rating.year,
            'semester': rating.semester,
        })
    
    return render(request, 'courses/edit_rating.html', {
        'form': form,
        'rating': rating,
        'course': rating.course
    })


@login_required
def delete_rating(request, rating_id):
    """View to delete a rating"""
    rating = get_object_or_404(Rating, id=rating_id, user=request.user)
    
    if request.method == "POST":
        course_name = rating.course.name
        rating.delete()
        messages.success(request, f"Your rating for '{course_name}' has been deleted.")
        return redirect("my_ratings")
    
    return render(request, 'courses/delete_rating.html', {
        'rating': rating
    })