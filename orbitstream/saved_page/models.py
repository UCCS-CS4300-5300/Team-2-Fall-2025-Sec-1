from django.db import models
from django.contrib.auth.models import User


class SavedSatellite(models.Model):
    """Model to store saved satellite data from N2YO API"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_satellites')
    satellite_id = models.IntegerField()
    name = models.CharField(max_length=255)
    altitude = models.FloatField(null=True, blank=True)
    azimuth = models.FloatField(null=True, blank=True)
    elevation = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'satellite_id']
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class SavedGalleryItem(models.Model):
    """Model to store saved NASA gallery images/videos"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_gallery_items')
    nasa_id = models.CharField(max_length=255)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)

    # Original URLs (kept for reference)
    media_url = models.URLField(max_length=1000, blank=True, null=True)
    thumbnail_url = models.URLField(max_length=1000, blank=True, null=True)

    # Store media data directly in database
    media_data = models.BinaryField(blank=True, null=True)
    media_content_type = models.CharField(max_length=100, blank=True, null=True)
    media_filename = models.CharField(max_length=255, blank=True, null=True)

    thumbnail_data = models.BinaryField(blank=True, null=True)
    thumbnail_content_type = models.CharField(max_length=100, blank=True, null=True)
    thumbnail_filename = models.CharField(max_length=255, blank=True, null=True)

    media_type = models.CharField(max_length=50, default='image')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'nasa_id']
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class SavedLaunch(models.Model):
    """Model to store saved launch data from SpaceDev API"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_launches')
    launch_id = models.CharField(max_length=255)
    name = models.CharField(max_length=500)
    status = models.CharField(max_length=100, blank=True, null=True)
    net = models.CharField(max_length=100, blank=True, null=True)
    rocket_name = models.CharField(max_length=255, blank=True, null=True)
    pad_name = models.CharField(max_length=255, blank=True, null=True)
    pad_location = models.CharField(max_length=500, blank=True, null=True)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'launch_id']
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class SavedLearnTopic(models.Model):
    """Model to store saved learn topics and their AI-generated summaries"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_learn_topics')
    topic = models.CharField(max_length=255)
    summary = models.TextField()
    keywords = models.TextField(blank=True, null=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'topic']
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} - {self.topic}"


class SavedNewsArticle(models.Model):
    """Model to store saved news articles"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_news_articles')
    article_url = models.URLField(max_length=1000)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    source_name = models.CharField(max_length=255, blank=True, null=True)
    published_at = models.CharField(max_length=100, blank=True, null=True)
    full_html = models.TextField(blank=True, null=True)  # Store full article content
    content = models.TextField(blank=True, null=True)  # Store article content fallback
    author = models.CharField(max_length=255, blank=True, null=True)  # Store author info
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'article_url']
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
