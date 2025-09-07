from django import forms
from .models import Rating, SEMESTER_CHOICES
from datetime import date

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ("rating", "comment", "year", "semester")
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_year(self):
        year = self.cleaned_data["year"]
        current = date.today().year
        if year < 1990 or year > current + 1:
            raise forms.ValidationError("Please provide a sensible year.")
        return year