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

class Course(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True, editable=False)

    class Meta:
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["name"])]
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:300]
        super().save(*args, **kwargs)


class Rating(models.Model):
    course = models.ForeignKey(Course, related_name="ratings", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="course_ratings", on_delete=models.CASCADE)

    # 1–5 rating
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

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

    class Meta:
        constraints = [
            # one rating per user per course per term
            UniqueConstraint(fields=["course", "user", "year", "semester"], name="uniq_user_course_term"),
            # enforce rating bounds at DB layer too
            CheckConstraint(check=Q(rating__gte=1, rating__lte=5), name="rating_between_1_5"),
        ]
        indexes = [
            models.Index(fields=["course", "-created_at"]),
            models.Index(fields=["user"]),
            models.Index(fields=["year", "semester"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.course} · {self.year} {self.semester} · {self.rating}/5 by {self.user_id}"