from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Course, Rating, UserProfile, RatingFlag, Visitor, Faculty, Institute, Fachgebiet
from .forms import RatingForm, CourseForm, CourseCSVUploadForm, UserProfileForm, RatingFlagForm
from django.db.models import Avg, Count, Value
from django.db.models.functions import Coalesce
import csv
import io

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create a UserProfile when a new user is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Automatically save the UserProfile when the user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()

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
        sort = (self.request.GET.get("sort") or "rating").lower()
        faculty_filter = (self.request.GET.get("faculty") or "").strip()
        fachgebiet_filter = (self.request.GET.get("fachgebiet") or "").strip()
        professor_filter = (self.request.GET.get("professor") or "").strip()
        institut_filter = (self.request.GET.get("institut") or "").strip()

        qs = Course.objects.all()

        if q:
            qs = qs.filter(name__icontains=q)
        
        if faculty_filter:
            qs = qs.filter(fachgebiet__institute__faculty__name__icontains=faculty_filter)
        
        if fachgebiet_filter:
            qs = qs.filter(fachgebiet__name__icontains=fachgebiet_filter)
        
        if professor_filter:
            qs = qs.filter(fachgebiet__professor__icontains=professor_filter)
        
        if institut_filter:
            qs = qs.filter(fachgebiet__institute__name__icontains=institut_filter)

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
        elif sort == "personal" and self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            # Sort by personal weighted rating
            # This is a simplified approach - for better performance, you might want to pre-calculate these
            courses_with_personal_ratings = []
            for course in qs:
                user_rating = Rating.objects.filter(course=course, user=self.request.user).first()
                if user_rating:
                    personal_rating = self.request.user.profile.calculate_weighted_rating(user_rating)
                    courses_with_personal_ratings.append((course, personal_rating))
            
            # Sort by personal rating (highest first)
            courses_with_personal_ratings.sort(key=lambda x: x[1] or 0, reverse=True)
            qs = [course for course, _ in courses_with_personal_ratings]
        else:                          # default: name
            qs = qs.order_by("name")

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx["sort"] = (self.request.GET.get("sort") or "rating").lower()
        ctx["faculty_filter"] = (self.request.GET.get("faculty") or "").strip()
        ctx["fachgebiet_filter"] = (self.request.GET.get("fachgebiet") or "").strip()
        ctx["professor_filter"] = (self.request.GET.get("professor") or "").strip()
        ctx["institut_filter"] = (self.request.GET.get("institut") or "").strip()
        
        # Get unique values for filter dropdowns - query models directly
        ctx["faculties"] = Faculty.objects.values_list('name', flat=True).distinct().order_by('name')
        ctx["fachgebiete"] = Fachgebiet.objects.values_list('name', flat=True).distinct().order_by('name')
        ctx["professors"] = Fachgebiet.objects.values_list('professor', flat=True).distinct().order_by('professor')
        ctx["institute"] = Institute.objects.values_list('name', flat=True).distinct().order_by('name')
        
        return ctx

def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    qs = course.ratings.filter(is_disabled=False).select_related("user").prefetch_related("flags")
    
    # Calculate averages for all rating dimensions
    agg = qs.aggregate(
        avg=Avg("rating"), 
        count=Count("id"),
        # Detailed rating averages
        avg_workload=Avg("workload_rating"),
        avg_difficulty=Avg("difficulty_rating"),
        avg_learning_gain=Avg("learning_gain_rating"),
        avg_teaching_quality=Avg("teaching_quality_rating"),
        avg_assessment_fairness=Avg("assessment_fairness_rating"),
        avg_practical_theoretical=Avg("practical_theoretical_balance"),
        avg_relevance=Avg("relevance_rating"),
        avg_materials=Avg("materials_rating"),
        avg_support=Avg("support_rating"),
        avg_organization=Avg("organization_rating"),
    )
    
    # Check if the current user has already rated this course
    user_has_rated = False
    user_rating = None
    personal_weighted_rating = None
    
    if request.user.is_authenticated:
        user_has_rated = Rating.objects.filter(course=course, user=request.user).exists()
        if user_has_rated:
            user_rating = Rating.objects.filter(course=course, user=request.user).first()
            # Calculate personal weighted rating
            if hasattr(request.user, 'profile'):
                personal_weighted_rating = request.user.profile.calculate_weighted_rating(user_rating)
    
    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course, 
            "ratings": qs, 
            "avg": agg["avg"], 
            "count": agg["count"],
            "user_has_rated": user_has_rated,
            "user_rating": user_rating,
            "personal_weighted_rating": personal_weighted_rating,
            "rating_averages": agg
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
                        # Update detailed ratings - convert empty strings to None for integer fields
                        existing_rating.workload_rating = data.get("workload_rating") or None
                        existing_rating.difficulty_rating = data.get("difficulty_rating") or None
                        existing_rating.learning_gain_rating = data.get("learning_gain_rating") or None
                        existing_rating.teaching_quality_rating = data.get("teaching_quality_rating") or None
                        existing_rating.assessment_fairness_rating = data.get("assessment_fairness_rating") or None
                        existing_rating.practical_theoretical_balance = data.get("practical_theoretical_balance") or None
                        existing_rating.relevance_rating = data.get("relevance_rating") or None
                        existing_rating.materials_rating = data.get("materials_rating") or None
                        existing_rating.support_rating = data.get("support_rating") or None
                        existing_rating.organization_rating = data.get("organization_rating") or None
                        # Update text fields
                        existing_rating.workload_text = data.get("workload_text", "")
                        existing_rating.difficulty_text = data.get("difficulty_text", "")
                        existing_rating.learning_gain_text = data.get("learning_gain_text", "")
                        existing_rating.teaching_quality_text = data.get("teaching_quality_text", "")
                        existing_rating.assessment_fairness_text = data.get("assessment_fairness_text", "")
                        existing_rating.practical_theoretical_text = data.get("practical_theoretical_text", "")
                        existing_rating.relevance_text = data.get("relevance_text", "")
                        existing_rating.materials_text = data.get("materials_text", "")
                        existing_rating.support_text = data.get("support_text", "")
                        existing_rating.organization_text = data.get("organization_text", "")
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
                            # Detailed ratings - convert empty strings to None for integer fields
                            workload_rating=data.get("workload_rating") or None,
                            difficulty_rating=data.get("difficulty_rating") or None,
                            learning_gain_rating=data.get("learning_gain_rating") or None,
                            teaching_quality_rating=data.get("teaching_quality_rating") or None,
                            assessment_fairness_rating=data.get("assessment_fairness_rating") or None,
                            practical_theoretical_balance=data.get("practical_theoretical_balance") or None,
                            relevance_rating=data.get("relevance_rating") or None,
                            materials_rating=data.get("materials_rating") or None,
                            support_rating=data.get("support_rating") or None,
                            organization_rating=data.get("organization_rating") or None,
                            # Text fields
                            workload_text=data.get("workload_text", ""),
                            difficulty_text=data.get("difficulty_text", ""),
                            learning_gain_text=data.get("learning_gain_text", ""),
                            teaching_quality_text=data.get("teaching_quality_text", ""),
                            assessment_fairness_text=data.get("assessment_fairness_text", ""),
                            practical_theoretical_text=data.get("practical_theoretical_text", ""),
                            relevance_text=data.get("relevance_text", ""),
                            materials_text=data.get("materials_text", ""),
                            support_text=data.get("support_text", ""),
                            organization_text=data.get("organization_text", ""),
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
                # Detailed ratings
                'workload_rating': existing_rating.workload_rating,
                'difficulty_rating': existing_rating.difficulty_rating,
                'learning_gain_rating': existing_rating.learning_gain_rating,
                'teaching_quality_rating': existing_rating.teaching_quality_rating,
                'assessment_fairness_rating': existing_rating.assessment_fairness_rating,
                'practical_theoretical_balance': existing_rating.practical_theoretical_balance,
                'relevance_rating': existing_rating.relevance_rating,
                'materials_rating': existing_rating.materials_rating,
                'support_rating': existing_rating.support_rating,
                'organization_rating': existing_rating.organization_rating,
                # Text fields
                'workload_text': existing_rating.workload_text,
                'difficulty_text': existing_rating.difficulty_text,
                'learning_gain_text': existing_rating.learning_gain_text,
                'teaching_quality_text': existing_rating.teaching_quality_text,
                'assessment_fairness_text': existing_rating.assessment_fairness_text,
                'practical_theoretical_text': existing_rating.practical_theoretical_text,
                'relevance_text': existing_rating.relevance_text,
                'materials_text': existing_rating.materials_text,
                'support_text': existing_rating.support_text,
                'organization_text': existing_rating.organization_text,
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
                            # Get course data based on whether we have a header or not
                            if has_header:
                                # DictReader: get from columns
                                course_name = row.get('name', '').strip() if 'name' in row else ''
                                faculty_name = row.get('faculty', '').strip() if 'faculty' in row else ''
                                institute_name = row.get('institute', '').strip() if 'institute' in row else ''
                                fachgebiet = row.get('fachgebiet', '').strip() if 'fachgebiet' in row else ''
                                professor = row.get('professor', '').strip() if 'professor' in row else ''
                                
                                # Fallback to first column if name is empty
                                if not course_name and row and list(row.values())[0].strip():
                                    course_name = list(row.values())[0].strip()
                                
                                if not course_name:
                                    errors.append(f"Row {row_num}: Empty course name")
                                    continue
                            else:
                                # Regular reader: get from columns by position
                                if row and len(row) > 0 and row[0].strip():
                                    course_name = row[0].strip()
                                    faculty_name = row[1].strip() if len(row) > 1 else ''
                                    institute_name = row[2].strip() if len(row) > 2 else ''
                                    fachgebiet = row[3].strip() if len(row) > 3 else ''
                                    professor = row[4].strip() if len(row) > 4 else ''
                                else:
                                    errors.append(f"Row {row_num}: Empty course name")
                                    continue
                            
                            # Look up or create faculty, institute, and fachgebiet
                            faculty_obj = None
                            institute_obj = None
                            fachgebiet_obj = None
                            
                            if faculty_name:
                                faculty_obj, _ = Faculty.objects.get_or_create(
                                    name=faculty_name
                                )
                            
                            if institute_name:
                                # If we have a faculty, use it; otherwise create a default one
                                if not faculty_obj:
                                    if faculty_name:
                                        faculty_obj, _ = Faculty.objects.get_or_create(
                                            name=faculty_name
                                        )
                                    else:
                                        # Create a default faculty if no faculty name provided
                                        faculty_obj, _ = Faculty.objects.get_or_create(
                                            name='Unknown Faculty'
                                        )
                                
                                institute_obj, _ = Institute.objects.get_or_create(
                                    name=institute_name,
                                    defaults={
                                        'faculty': faculty_obj
                                    }
                                )
                            
                            if fachgebiet and professor:
                                # Create fachgebiet if we have both name and professor
                                if not institute_obj:
                                    # Create a default institute if none exists
                                    if not faculty_obj:
                                        faculty_obj, _ = Faculty.objects.get_or_create(
                                            name='Unknown Faculty'
                                        )
                                    institute_obj, _ = Institute.objects.get_or_create(
                                        name='Unknown Institute',
                                        defaults={
                                            'faculty': faculty_obj
                                        }
                                    )
                                
                                fachgebiet_obj, _ = Fachgebiet.objects.get_or_create(
                                    name=fachgebiet,
                                    defaults={
                                        'professor': professor,
                                        'institute': institute_obj
                                    }
                                )
                            
                            # Create course if it doesn't exist
                            course, created = Course.objects.get_or_create(
                                name=course_name,
                                defaults={
                                    'name': course_name,
                                    'fachgebiet': fachgebiet_obj
                                }
                            )
                            
                            # Update existing course with new fachgebiet if provided
                            if not created and fachgebiet_obj and not course.fachgebiet:
                                course.fachgebiet = fachgebiet_obj
                                course.save()
                            
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
            # Update detailed ratings - convert empty strings to None for integer fields
            rating.workload_rating = data.get("workload_rating") or None
            rating.difficulty_rating = data.get("difficulty_rating") or None
            rating.learning_gain_rating = data.get("learning_gain_rating") or None
            rating.teaching_quality_rating = data.get("teaching_quality_rating") or None
            rating.assessment_fairness_rating = data.get("assessment_fairness_rating") or None
            rating.practical_theoretical_balance = data.get("practical_theoretical_balance") or None
            rating.relevance_rating = data.get("relevance_rating") or None
            rating.materials_rating = data.get("materials_rating") or None
            rating.support_rating = data.get("support_rating") or None
            rating.organization_rating = data.get("organization_rating") or None
            # Update text fields
            rating.workload_text = data.get("workload_text", "")
            rating.difficulty_text = data.get("difficulty_text", "")
            rating.learning_gain_text = data.get("learning_gain_text", "")
            rating.teaching_quality_text = data.get("teaching_quality_text", "")
            rating.assessment_fairness_text = data.get("assessment_fairness_text", "")
            rating.practical_theoretical_text = data.get("practical_theoretical_text", "")
            rating.relevance_text = data.get("relevance_text", "")
            rating.materials_text = data.get("materials_text", "")
            rating.support_text = data.get("support_text", "")
            rating.organization_text = data.get("organization_text", "")
            rating.save()
            messages.success(request, "Your rating has been updated.")
            return redirect("my_ratings")
    else:
        form = RatingForm(initial={
            'rating': rating.rating,
            'comment': rating.comment,
            'year': rating.year,
            'semester': rating.semester,
            # Detailed ratings
            'workload_rating': rating.workload_rating,
            'difficulty_rating': rating.difficulty_rating,
            'learning_gain_rating': rating.learning_gain_rating,
            'teaching_quality_rating': rating.teaching_quality_rating,
            'assessment_fairness_rating': rating.assessment_fairness_rating,
            'practical_theoretical_balance': rating.practical_theoretical_balance,
            'relevance_rating': rating.relevance_rating,
            'materials_rating': rating.materials_rating,
            'support_rating': rating.support_rating,
            'organization_rating': rating.organization_rating,
            # Text fields
            'workload_text': rating.workload_text,
            'difficulty_text': rating.difficulty_text,
            'learning_gain_text': rating.learning_gain_text,
            'teaching_quality_text': rating.teaching_quality_text,
            'assessment_fairness_text': rating.assessment_fairness_text,
            'practical_theoretical_text': rating.practical_theoretical_text,
            'relevance_text': rating.relevance_text,
            'materials_text': rating.materials_text,
            'support_text': rating.support_text,
            'organization_text': rating.organization_text,
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


@login_required
def edit_profile(request):
    """View to edit user profile weights"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile weights have been updated.")
            return redirect("profile")
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'courses/edit_profile.html', {
        'form': form,
        'profile': profile
    })


@login_required
def reset_profile_weights(request):
    """View to reset profile weights to default values"""
    if request.method == "POST":
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        # Reset all weights to default (20 each)
        for field in UserProfile._meta.fields:
            if field.name.endswith('_weight'):
                setattr(profile, field.name, 20)
        profile.save()
        messages.success(request, "Your profile weights have been reset to default values.")
        return redirect("edit_profile")
    
    return render(request, 'courses/reset_profile_weights.html')


@login_required
def flag_rating(request, rating_id):
    """View to flag a rating as inappropriate"""
    rating = get_object_or_404(Rating, id=rating_id)
    
    # Prevent users from flagging their own ratings
    if rating.user == request.user:
        messages.error(request, "You cannot flag your own rating.")
        return redirect("course_detail", slug=rating.course.slug)
    
    # Check if user has already flagged this rating
    existing_flag = RatingFlag.objects.filter(rating=rating, flagged_by=request.user).first()
    if existing_flag:
        messages.info(request, "You have already flagged this rating.")
        return redirect("course_detail", slug=rating.course.slug)
    
    if request.method == "POST":
        form = RatingFlagForm(request.POST)
        if form.is_valid():
            flag = form.save(commit=False)
            flag.rating = rating
            flag.flagged_by = request.user
            flag.save()
            messages.success(request, "Thank you for reporting this rating. It will be reviewed by our moderators.")
            return redirect("course_detail", slug=rating.course.slug)
    else:
        form = RatingFlagForm()
    
    return render(request, 'courses/flag_rating.html', {
        'form': form,
        'rating': rating,
        'course': rating.course
    })