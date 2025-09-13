from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint
from django.utils.text import slugify
from datetime import date

User = settings.AUTH_USER_MODEL

SEMESTER_CHOICES = [
    ("SS", "Sommersemester"),
    ("WS", "Wintersemester"),
]

class Faculty(models.Model):
    """Model for university faculties"""
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text="Short code for the faculty (e.g., 'CS', 'MATH')")
    description = models.TextField(blank=True, help_text="Optional description of the faculty")
    
    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Faculties"
    
    def __str__(self):
        return self.name

class Institute(models.Model):
    """Model for institutes within faculties"""
    name = models.CharField(max_length=255, unique=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="institutes")
    code = models.CharField(max_length=20, unique=True, help_text="Short code for the institute")
    description = models.TextField(blank=True, help_text="Optional description of the institute")
    
    class Meta:
        ordering = ["faculty__name", "name"]
    
    def __str__(self):
        return f"{self.name} ({self.faculty.name})"

class Fachgebiet(models.Model):
    """Model for subject areas with associated professor"""
    name = models.CharField(max_length=255, unique=True, help_text="Subject area name (e.g., Algorithms, Statistics)")
    professor = models.CharField(max_length=255, help_text="Professor or instructor name")
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name="fachgebiete")
    description = models.TextField(blank=True, help_text="Optional description of the subject area")
    
    class Meta:
        ordering = ["institute__faculty__name", "institute__name", "name"]
        verbose_name_plural = "Fachgebiete"
    
    def __str__(self):
        return f"{self.name} - {self.professor} ({self.institute.name})"

class Course(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True, editable=False)
    fachgebiet = models.ForeignKey(Fachgebiet, on_delete=models.SET_NULL, null=True, blank=True, related_name="courses")

    class Meta:
        indexes = [
            models.Index(fields=["slug"]), 
            models.Index(fields=["name"]),
            models.Index(fields=["fachgebiet"])
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def faculty(self):
        """Get faculty through fachgebiet relationship"""
        return self.fachgebiet.institute.faculty if self.fachgebiet else None

    @property
    def institute(self):
        """Get institute through fachgebiet relationship"""
        return self.fachgebiet.institute if self.fachgebiet else None

    @property
    def professor(self):
        """Get professor through fachgebiet relationship"""
        return self.fachgebiet.professor if self.fachgebiet else None

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:300]
        super().save(*args, **kwargs)


class Rating(models.Model):
    course = models.ForeignKey(Course, related_name="ratings", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="course_ratings", on_delete=models.CASCADE)

    # Overall 1–5 rating (keeping for backward compatibility)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    # Detailed rating dimensions (1-5 scale)
    workload_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Workload/Time Required (1=≤3h, 2=4–6h, 3=7–9h, 4=10–12h, 5=≥13h)",
        null=True, blank=True
    )
    difficulty_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Perceived Difficulty (1=Very easy, 5=Extremely hard)",
        null=True, blank=True
    )
    learning_gain_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Learning Gain (1=None, 5=A great deal)",
        null=True, blank=True
    )
    teaching_quality_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Teaching Quality (1=Very poor, 5=Excellent)",
        null=True, blank=True
    )
    assessment_fairness_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Assessment Fairness (1=Very unfair, 5=Very fair)",
        null=True, blank=True
    )
    practical_theoretical_balance = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Practical ↔ Theoretical Balance (0=Purely theoretical, 100=Highly practical)",
        null=True, blank=True
    )
    relevance_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Relevance/Applicability (1=Not relevant, 5=Highly relevant)",
        null=True, blank=True
    )
    materials_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Materials & Resources (1=Very poor, 5=Excellent)",
        null=True, blank=True
    )
    support_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Support & Responsiveness (1=Unresponsive, 5=Very responsive)",
        null=True, blank=True
    )
    organization_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Course Organization (1=Chaotic, 5=Very well organized)",
        null=True, blank=True
    )

    # Text fields for additional details
    workload_text = models.TextField(
        blank=True, max_length=500,
        help_text="Additional details about workload (e.g., ECTS credits, specific time breakdown)"
    )
    difficulty_text = models.TextField(
        blank=True, max_length=500,
        help_text="Additional details about difficulty"
    )
    learning_gain_text = models.TextField(
        blank=True, max_length=500,
        help_text="Additional details about learning gain"
    )
    teaching_quality_text = models.TextField(
        blank=True, max_length=500,
        help_text="Additional details about teaching quality"
    )
    assessment_fairness_text = models.TextField(
        blank=True, max_length=500,
        help_text="Additional details about assessment fairness"
    )
    practical_theoretical_text = models.TextField(
        blank=True, max_length=500,
        help_text="Additional details about practical/theoretical balance"
    )
    relevance_text = models.TextField(
        blank=True, max_length=500,
        help_text="Additional details about relevance/applicability"
    )
    materials_text = models.TextField(
        blank=True, max_length=500,
        help_text="Additional details about materials and resources"
    )
    support_text = models.TextField(
        blank=True, max_length=500,
        help_text="Additional details about support and responsiveness"
    )
    organization_text = models.TextField(
        blank=True, max_length=500,
        help_text="Additional details about course organization"
    )

    # General comment (keeping existing)
    comment = models.TextField(blank=True, max_length=4000)

    # when the user took the course
    year = models.PositiveSmallIntegerField(
        help_text="Year you took the course (e.g. 2024)",
        validators=[
            MinValueValidator(1990),
            MaxValueValidator(date.today().year + 1),  # allow next year a bit
        ],
    )
    semester = models.CharField(max_length=2, choices=SEMESTER_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_disabled = models.BooleanField(default=False, help_text="Disable this rating from being displayed")

    class Meta:
        constraints = [
            # one rating per user per course (regardless of term)
            UniqueConstraint(fields=["course", "user"], name="uniq_user_course"),
            # enforce rating bounds at DB layer too
            CheckConstraint(check=Q(rating__gte=1, rating__lte=5), name="rating_between_1_5"),
            # enforce detailed rating bounds
            CheckConstraint(check=Q(workload_rating__gte=1, workload_rating__lte=5), name="workload_rating_between_1_5"),
            CheckConstraint(check=Q(difficulty_rating__gte=1, difficulty_rating__lte=5), name="difficulty_rating_between_1_5"),
            CheckConstraint(check=Q(learning_gain_rating__gte=1, learning_gain_rating__lte=5), name="learning_gain_rating_between_1_5"),
            CheckConstraint(check=Q(teaching_quality_rating__gte=1, teaching_quality_rating__lte=5), name="teaching_quality_rating_between_1_5"),
            CheckConstraint(check=Q(assessment_fairness_rating__gte=1, assessment_fairness_rating__lte=5), name="assessment_fairness_rating_between_1_5"),
            CheckConstraint(check=Q(practical_theoretical_balance__gte=0, practical_theoretical_balance__lte=100), name="practical_theoretical_balance_between_0_100"),
            CheckConstraint(check=Q(relevance_rating__gte=1, relevance_rating__lte=5), name="relevance_rating_between_1_5"),
            CheckConstraint(check=Q(materials_rating__gte=1, materials_rating__lte=5), name="materials_rating_between_1_5"),
            CheckConstraint(check=Q(support_rating__gte=1, support_rating__lte=5), name="support_rating_between_1_5"),
            CheckConstraint(check=Q(organization_rating__gte=1, organization_rating__lte=5), name="organization_rating_between_1_5"),
        ]
        indexes = [
            models.Index(fields=["course", "-created_at"]),
            models.Index(fields=["user"]),
            models.Index(fields=["year", "semester"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.course} · {self.year} {self.semester} · {self.rating}/5 by {self.user_id}"


class UserProfile(models.Model):
    """User profile with personalized rating dimension weights"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Weight fields for each rating dimension (0-100, default 20 for equal weighting)
    workload_weight = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight for workload rating (0-100)"
    )
    difficulty_weight = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight for difficulty rating (0-100)"
    )
    learning_gain_weight = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight for learning gain rating (0-100)"
    )
    teaching_quality_weight = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight for teaching quality rating (0-100)"
    )
    assessment_fairness_weight = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight for assessment fairness rating (0-100)"
    )
    practical_theoretical_weight = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight for practical/theoretical balance (0-100)"
    )
    relevance_weight = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight for relevance rating (0-100)"
    )
    materials_weight = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight for materials rating (0-100)"
    )
    support_weight = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight for support rating (0-100)"
    )
    organization_weight = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight for organization rating (0-100)"
    )
    
    # Special field for practical/theoretical preference (0-100, 50=balanced)
    practical_theoretical_preference = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="User's preference on theory-practical spectrum (0=Very Theoretical, 100=Very Practical)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            # Ensure weights sum to 100 (or close to it)
            CheckConstraint(
                check=Q(
                    workload_weight__gte=0, workload_weight__lte=100,
                    difficulty_weight__gte=0, difficulty_weight__lte=100,
                    learning_gain_weight__gte=0, learning_gain_weight__lte=100,
                    teaching_quality_weight__gte=0, teaching_quality_weight__lte=100,
                    assessment_fairness_weight__gte=0, assessment_fairness_weight__lte=100,
                    practical_theoretical_weight__gte=0, practical_theoretical_weight__lte=100,
                    relevance_weight__gte=0, relevance_weight__lte=100,
                    materials_weight__gte=0, materials_weight__lte=100,
                    support_weight__gte=0, support_weight__lte=100,
                    organization_weight__gte=0, organization_weight__lte=100,
                    practical_theoretical_preference__gte=0, practical_theoretical_preference__lte=100,
                ),
                name="weights_and_preference_between_0_100"
            )
        ]
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    def get_weights(self):
        """Return a dictionary of all weights"""
        return {
            'workload': self.workload_weight,
            'difficulty': self.difficulty_weight,
            'learning_gain': self.learning_gain_weight,
            'teaching_quality': self.teaching_quality_weight,
            'assessment_fairness': self.assessment_fairness_weight,
            'practical_theoretical': self.practical_theoretical_weight,
            'relevance': self.relevance_weight,
            'materials': self.materials_weight,
            'support': self.support_weight,
            'organization': self.organization_weight,
        }
    
    def calculate_weighted_rating(self, rating):
        """Calculate weighted rating for a given rating instance"""
        if not rating:
            return None
            
        weights = self.get_weights()
        weighted_sum = 0
        total_weight = 0
        
        # Map rating fields to weight fields
        rating_fields = {
            'workload_rating': 'workload',
            'difficulty_rating': 'difficulty',
            'learning_gain_rating': 'learning_gain',
            'teaching_quality_rating': 'teaching_quality',
            'assessment_fairness_rating': 'assessment_fairness',
            'practical_theoretical_balance': 'practical_theoretical',
            'relevance_rating': 'relevance',
            'materials_rating': 'materials',
            'support_rating': 'support',
            'organization_rating': 'organization',
        }
        
        for rating_field, weight_key in rating_fields.items():
            rating_value = getattr(rating, rating_field, None)
            if rating_value is not None:
                weight = weights[weight_key]
                
                # Special handling for practical/theoretical balance
                if rating_field == 'practical_theoretical_balance':
                    # Calculate how well the course matches user's preference
                    user_preference = self.practical_theoretical_preference
                    course_balance = rating_value
                    
                    # Calculate alignment score (0-1, where 1 is perfect match)
                    # The closer the course is to user preference, the higher the score
                    alignment_score = 1 - abs(course_balance - user_preference) / 100
                    
                    # Convert to 1-5 scale (1=no alignment, 5=perfect alignment)
                    normalized_value = alignment_score * 4 + 1
                else:
                    normalized_value = rating_value
                
                weighted_sum += normalized_value * weight
                total_weight += weight
        
        if total_weight == 0:
            return None
            
        return round(weighted_sum / total_weight, 2)


class RatingFlag(models.Model):
    """Model to store flags for inappropriate ratings"""
    
    rating = models.ForeignKey(Rating, related_name="flags", on_delete=models.CASCADE)
    flagged_by = models.ForeignKey(User, related_name="rating_flags", on_delete=models.CASCADE)
    reason = models.TextField(max_length=1000, help_text="Reason for flagging this rating")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            # One flag per user per rating
            UniqueConstraint(fields=["rating", "flagged_by"], name="uniq_user_rating_flag"),
        ]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["rating"]),
            models.Index(fields=["flagged_by"]),
        ]
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"Flag for {self.rating} by {self.flagged_by.username}"


class Visitor(models.Model):
    """Model to track website visitors and page views"""
    
    ip_address = models.GenericIPAddressField(help_text="Visitor's IP address")
    user_agent = models.TextField(blank=True, help_text="Visitor's user agent string")
    referer = models.URLField(blank=True, null=True, help_text="Referring URL")
    path = models.CharField(max_length=500, help_text="Page path visited")
    query_string = models.CharField(max_length=1000, blank=True, help_text="URL query parameters")
    method = models.CharField(max_length=10, default="GET", help_text="HTTP method")
    status_code = models.PositiveSmallIntegerField(default=200, help_text="HTTP response status code")
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, help_text="Logged in user (if any)")
    session_key = models.CharField(max_length=40, blank=True, help_text="Django session key")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["ip_address"]),
            models.Index(fields=["path"]),
            models.Index(fields=["user"]),
            models.Index(fields=["created_at", "ip_address"]),  # For daily unique visitor counts
        ]
        ordering = ["-created_at"]
    
    def __str__(self):
        user_info = f" (user: {self.user.username})" if self.user else ""
        return f"{self.ip_address} - {self.path}{user_info} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def get_daily_stats(cls, days=30):
        """Get visitor statistics for the last N days"""
        from django.db.models import Count, Q
        from django.utils import timezone
        from datetime import timedelta
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Total page views
        total_views = cls.objects.filter(created_at__gte=start_date).count()
        
        # Unique visitors (by IP)
        unique_visitors = cls.objects.filter(
            created_at__gte=start_date
        ).values('ip_address').distinct().count()
        
        # Logged in users
        logged_in_views = cls.objects.filter(
            created_at__gte=start_date,
            user__isnull=False
        ).count()
        
        # Most visited pages
        popular_pages = cls.objects.filter(
            created_at__gte=start_date
        ).values('path').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return {
            'total_views': total_views,
            'unique_visitors': unique_visitors,
            'logged_in_views': logged_in_views,
            'popular_pages': list(popular_pages),
            'period_days': days,
            'start_date': start_date,
            'end_date': end_date,
        }