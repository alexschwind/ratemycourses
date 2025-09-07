from django import forms
from .models import Rating, SEMESTER_CHOICES, Course
from datetime import date
import csv
import io

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ("rating", "comment", "year", "semester")
        widgets = {
            "rating": forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-input', 'style': 'display: none;'}),
            "comment": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_year(self):
        year = self.cleaned_data["year"]
        current = date.today().year
        if year < 1990 or year > current + 1:
            raise forms.ValidationError("Please provide a sensible year.")
        return year


class CourseCSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Upload a CSV file with course names. The file should have a 'name' column or the first column should contain course names.",
        widget=forms.FileInput(attrs={'accept': '.csv'})
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if not csv_file:
            raise forms.ValidationError("Please select a CSV file.")
        
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError("File must be a CSV file.")
        
        # Check file size (limit to 5MB)
        if csv_file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("File size must be less than 5MB.")
        
        # Try to read and validate the CSV
        try:
            csv_file.seek(0)
            content = csv_file.read().decode('utf-8')
            csv_file.seek(0)  # Reset file pointer
            
            # Parse CSV to check format
            lines = content.strip().split('\n')
            if not lines or not lines[0].strip():
                raise forms.ValidationError("CSV file is empty.")
            
            # Check if first row looks like a header (contains 'name') or is data
            first_line = lines[0].strip().lower()
            has_header = 'name' in first_line
            
            if has_header:
                # Use DictReader to validate header format
                csv_reader = csv.DictReader(io.StringIO(content))
                rows = list(csv_reader)
                if not rows:
                    raise forms.ValidationError("CSV file has header but no data rows.")
            else:
                # Use regular reader to validate data format
                csv_reader = csv.reader(io.StringIO(content))
                rows = list(csv_reader)
                if not rows:
                    raise forms.ValidationError("CSV file has no data rows.")
                if not rows[0] or not rows[0][0].strip():
                    raise forms.ValidationError("CSV file first row is empty.")
            
        except UnicodeDecodeError:
            raise forms.ValidationError("CSV file must be encoded in UTF-8.")
        except Exception as e:
            raise forms.ValidationError(f"Invalid CSV file format: {str(e)}")
        
        return csv_file