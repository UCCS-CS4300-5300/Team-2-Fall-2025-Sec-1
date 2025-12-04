from django.db import models
from django.contrib.auth.models import User


class FilterPreset(models.Model):
    """Model to store user's custom filter presets for the news page."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='filter_presets')
    name = models.CharField(max_length=100)

    # Filter fields matching NewsFilterForm
    search_query = models.CharField(max_length=255, blank=True, default='')
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    sort_by = models.CharField(
        max_length=20,
        choices=[
            ('publishedAt', 'Latest'),
            ('relevancy', 'Relevancy'),
            ('popularity', 'Popularity'),
        ],
        default='publishedAt'
    )
    source = models.CharField(
        max_length=50,
        choices=[
            ('', 'All Sources'),
            ('nasa', 'NASA'),
            ('spacex', 'SpaceX'),
            ('space', 'General Space'),
        ],
        default=''
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'name']

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    def to_filter_dict(self):
        """Convert preset to dictionary format compatible with NewsFilterForm."""
        return {
            'search_query': self.search_query,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'sort_by': self.sort_by,
            'source': self.source,
        }
