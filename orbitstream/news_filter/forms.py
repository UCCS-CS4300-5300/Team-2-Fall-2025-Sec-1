# news_filters/forms.py
from django import forms
from datetime import datetime, timedelta

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