from django import forms
from .models import Rating, SEMESTER_CHOICES, Course, UserProfile, RatingFlag
from datetime import date
import csv
import io

class RatingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default year to current year
        self.fields['year'].initial = date.today().year
        # Set default practical/theoretical balance to 50 (balanced)
        self.fields['practical_theoretical_balance'].initial = 50
    
    class Meta:
        model = Rating
        fields = (
            "rating", "comment", "year", "semester",
            # Detailed rating fields
            "workload_rating", "difficulty_rating", "learning_gain_rating", 
            "teaching_quality_rating", "assessment_fairness_rating", 
            "practical_theoretical_balance", "relevance_rating", 
            "materials_rating", "support_rating", "organization_rating",
            # Text fields
            "workload_text", "difficulty_text", "learning_gain_text",
            "teaching_quality_text", "assessment_fairness_text",
            "practical_theoretical_text", "relevance_text", "materials_text",
            "support_text", "organization_text"
        )
        widgets = {
            "rating": forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-input', 'style': 'display: none;'}),
            "comment": forms.Textarea(attrs={"rows": 5}),
            # Detailed rating widgets
            "workload_rating": forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-input', 'style': 'display: none;'}),
            "difficulty_rating": forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-input', 'style': 'display: none;'}),
            "learning_gain_rating": forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-input', 'style': 'display: none;'}),
            "teaching_quality_rating": forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-input', 'style': 'display: none;'}),
            "assessment_fairness_rating": forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-input', 'style': 'display: none;'}),
            "practical_theoretical_balance": forms.NumberInput(attrs={'min': 0, 'max': 100, 'class': 'slider-input', 'style': 'display: none;'}),
            "relevance_rating": forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-input', 'style': 'display: none;'}),
            "materials_rating": forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-input', 'style': 'display: none;'}),
            "support_rating": forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-input', 'style': 'display: none;'}),
            "organization_rating": forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-input', 'style': 'display: none;'}),
            # Text field widgets
            "workload_text": forms.Textarea(attrs={"rows": 2, "placeholder": "e.g., ECTS credits, specific time breakdown"}),
            "difficulty_text": forms.Textarea(attrs={"rows": 2, "placeholder": "Additional details about difficulty"}),
            "learning_gain_text": forms.Textarea(attrs={"rows": 2, "placeholder": "Additional details about learning gain"}),
            "teaching_quality_text": forms.Textarea(attrs={"rows": 2, "placeholder": "Additional details about teaching quality"}),
            "assessment_fairness_text": forms.Textarea(attrs={"rows": 2, "placeholder": "Additional details about assessment fairness"}),
            "practical_theoretical_text": forms.Textarea(attrs={"rows": 2, "placeholder": "Additional details about practical/theoretical balance"}),
            "relevance_text": forms.Textarea(attrs={"rows": 2, "placeholder": "Additional details about relevance/applicability"}),
            "materials_text": forms.Textarea(attrs={"rows": 2, "placeholder": "Additional details about materials and resources"}),
            "support_text": forms.Textarea(attrs={"rows": 2, "placeholder": "Additional details about support and responsiveness"}),
            "organization_text": forms.Textarea(attrs={"rows": 2, "placeholder": "Additional details about course organization"}),
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


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile weights using importance scale"""
    
    # Define importance scale choices (1-5 scale)
    IMPORTANCE_CHOICES = [
        (1, 'Not Important'),
        (2, 'Slightly Important'),
        (3, 'Moderately Important'),
        (4, 'Very Important'),
        (5, 'Extremely Important'),
    ]
    
    # Create form fields for importance scale (not the actual weight fields)
    workload_importance = forms.IntegerField(
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'step': 1, 'class': 'importance-slider'}),
        label='Workload/Time Required',
        help_text='How important is workload to you?',
        initial=3
    )
    difficulty_importance = forms.IntegerField(
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'step': 1, 'class': 'importance-slider'}),
        label='Perceived Difficulty',
        help_text='How important is difficulty to you?',
        initial=3
    )
    learning_gain_importance = forms.IntegerField(
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'step': 1, 'class': 'importance-slider'}),
        label='Learning Gain',
        help_text='How important is learning gain to you?',
        initial=3
    )
    teaching_quality_importance = forms.IntegerField(
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'step': 1, 'class': 'importance-slider'}),
        label='Teaching Quality',
        help_text='How important is teaching quality to you?',
        initial=3
    )
    assessment_fairness_importance = forms.IntegerField(
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'step': 1, 'class': 'importance-slider'}),
        label='Assessment Fairness',
        help_text='How important is assessment fairness to you?',
        initial=3
    )
    practical_theoretical_importance = forms.IntegerField(
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'step': 1, 'class': 'importance-slider'}),
        label='Practical ↔ Theoretical Balance',
        help_text='How important is practical/theoretical balance to you?',
        initial=3
    )
    
    # Special field for practical/theoretical preference
    practical_theoretical_preference = forms.IntegerField(
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 0, 'max': 100, 'step': 5, 'class': 'preference-slider'}),
        label='Your Preference: Theory ↔ Practical',
        help_text='Where do you prefer courses on the theory-practical spectrum? (0=Very Theoretical, 100=Very Practical)',
        initial=50
    )
    relevance_importance = forms.IntegerField(
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'step': 1, 'class': 'importance-slider'}),
        label='Relevance/Applicability',
        help_text='How important is relevance to you?',
        initial=3
    )
    materials_importance = forms.IntegerField(
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'step': 1, 'class': 'importance-slider'}),
        label='Materials & Resources',
        help_text='How important are materials & resources to you?',
        initial=3
    )
    support_importance = forms.IntegerField(
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'step': 1, 'class': 'importance-slider'}),
        label='Support & Responsiveness',
        help_text='How important is support & responsiveness to you?',
        initial=3
    )
    organization_importance = forms.IntegerField(
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'step': 1, 'class': 'importance-slider'}),
        label='Course Organization',
        help_text='How important is course organization to you?',
        initial=3
    )
    
    class Meta:
        model = UserProfile
        fields = []  # We'll handle the weight fields manually
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values for importance fields based on current weights
        if self.instance and self.instance.pk:
            # Convert weights to importance scale (1-5)
            weight_to_importance = {
                0: 1, 5: 1, 10: 1, 15: 1, 20: 2, 25: 2, 30: 2, 35: 3, 40: 3, 45: 3,
                50: 3, 55: 4, 60: 4, 65: 4, 70: 4, 75: 4, 80: 5, 85: 5, 90: 5, 95: 5, 100: 5
            }
            
            self.fields['workload_importance'].initial = weight_to_importance.get(self.instance.workload_weight, 3)
            self.fields['difficulty_importance'].initial = weight_to_importance.get(self.instance.difficulty_weight, 3)
            self.fields['learning_gain_importance'].initial = weight_to_importance.get(self.instance.learning_gain_weight, 3)
            self.fields['teaching_quality_importance'].initial = weight_to_importance.get(self.instance.teaching_quality_weight, 3)
            self.fields['assessment_fairness_importance'].initial = weight_to_importance.get(self.instance.assessment_fairness_weight, 3)
            self.fields['practical_theoretical_importance'].initial = weight_to_importance.get(self.instance.practical_theoretical_weight, 3)
            self.fields['relevance_importance'].initial = weight_to_importance.get(self.instance.relevance_weight, 3)
            self.fields['materials_importance'].initial = weight_to_importance.get(self.instance.materials_weight, 3)
            self.fields['support_importance'].initial = weight_to_importance.get(self.instance.support_weight, 3)
            self.fields['organization_importance'].initial = weight_to_importance.get(self.instance.organization_weight, 3)
            
            # Set practical/theoretical preference
            self.fields['practical_theoretical_preference'].initial = getattr(self.instance, 'practical_theoretical_preference', 50)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Convert importance scale to weights
        importance_to_weight = {
            1: 0,   # Not Important -> 0%
            2: 10,   # Slightly Important -> 10%
            3: 20,   # Moderately Important -> 20%
            4: 50,   # Very Important -> 50%
            5: 80,   # Extremely Important -> 80%
        }
        
        # Map importance fields to weight fields
        importance_fields = [
            ('workload_importance', 'workload_weight'),
            ('difficulty_importance', 'difficulty_weight'),
            ('learning_gain_importance', 'learning_gain_weight'),
            ('teaching_quality_importance', 'teaching_quality_weight'),
            ('assessment_fairness_importance', 'assessment_fairness_weight'),
            ('practical_theoretical_importance', 'practical_theoretical_weight'),
            ('relevance_importance', 'relevance_weight'),
            ('materials_importance', 'materials_weight'),
            ('support_importance', 'support_weight'),
            ('organization_importance', 'organization_weight'),
        ]
        
        # Convert importance to weights
        for importance_field, weight_field in importance_fields:
            importance_value = cleaned_data.get(importance_field)
            if importance_value is not None:
                # Ensure value is within valid range
                if 1 <= importance_value <= 5:
                    cleaned_data[weight_field] = importance_to_weight.get(importance_value, 30)
                else:
                    self.add_error(importance_field, "Value must be between 1 and 5")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Convert importance to weights before saving
        importance_to_weight = {
            1: 0,   # Not Important -> 0%
            2: 10,   # Slightly Important -> 10%
            3: 20,   # Moderately Important -> 20%
            4: 50,   # Very Important -> 50%
            5: 80,   # Extremely Important -> 80%
        }
        
        # Map importance fields to weight fields
        importance_fields = [
            ('workload_importance', 'workload_weight'),
            ('difficulty_importance', 'difficulty_weight'),
            ('learning_gain_importance', 'learning_gain_weight'),
            ('teaching_quality_importance', 'teaching_quality_weight'),
            ('assessment_fairness_importance', 'assessment_fairness_weight'),
            ('practical_theoretical_importance', 'practical_theoretical_weight'),
            ('relevance_importance', 'relevance_weight'),
            ('materials_importance', 'materials_weight'),
            ('support_importance', 'support_weight'),
            ('organization_importance', 'organization_weight'),
        ]
        
        # Convert and set weights
        for importance_field, weight_field in importance_fields:
            importance_value = self.cleaned_data.get(importance_field)
            if importance_value is not None and 1 <= importance_value <= 5:
                setattr(self.instance, weight_field, importance_to_weight.get(importance_value, 30))
        
        # Set practical/theoretical preference
        preference_value = self.cleaned_data.get('practical_theoretical_preference')
        if preference_value is not None and 0 <= preference_value <= 100:
            setattr(self.instance, 'practical_theoretical_preference', preference_value)
        
        return super().save(commit=commit)


class RatingFlagForm(forms.ModelForm):
    """Form for flagging a rating"""
    
    class Meta:
        model = RatingFlag
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Please explain why you think this rating is inappropriate...',
                'maxlength': 1000
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reason'].required = True
        self.fields['reason'].label = 'Reason for flagging'
        self.fields['reason'].help_text = 'Please provide a detailed explanation for why this rating should be reviewed.'