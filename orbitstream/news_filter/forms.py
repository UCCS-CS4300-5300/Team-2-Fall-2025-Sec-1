# news_filters/forms.py
from django import forms
from datetime import datetime, timedelta
from .models import FilterPreset

class NewsFilterForm(forms.Form):
    search_query = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search articles...',
            'class': 'filter-input'
        }),
        label='Search'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'filter-input'
        }),
        label='From Date'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'filter-input'
        }),
        label='To Date'
    )
    
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('publishedAt', 'Date (Newest)'),
            ('relevancy', 'Relevance'),
            ('popularity', 'Popularity'),
        ],
        initial='publishedAt',
        widget=forms.Select(attrs={'class': 'filter-select'}),
        label='Sort By'
    )
    
    source = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Sources'),
            ('nasa', 'NASA'),
            ('spacex', 'SpaceX'),
            ('space', 'General Space'),
        ],
        widget=forms.Select(attrs={'class': 'filter-select'}),
        label='Source Filter'
    )


class FilterPresetForm(forms.ModelForm):
    """Form for creating and editing filter presets."""

    class Meta:
        model = FilterPreset
        fields = ['name', 'search_query', 'date_from', 'date_to', 'sort_by', 'source']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter preset name (e.g., "NASA Articles")',
                'maxlength': '100'
            }),
            'search_query': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Search keywords...'
            }),
            'date_from': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'date_to': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'sort_by': forms.Select(attrs={'class': 'form-control'}),
            'source': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Preset Name',
            'search_query': 'Search Keywords',
            'date_from': 'From Date',
            'date_to': 'To Date',
            'sort_by': 'Sort By',
            'source': 'Source',
        }