from django.conf import settings
from django.db import models


class LessonAIProcessing(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    lesson = models.OneToOneField(
        "courses.Lesson",
        on_delete=models.CASCADE,
        related_name="ai_processing",
        db_index=True,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    transcript_text = models.TextField(blank=True)
    analysis_json = models.JSONField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "lesson AI processing"
        verbose_name_plural = "lesson AI processing records"

    def __str__(self):
        return f"AI processing lesson={self.lesson_id} status={self.status}"


class WeakTopic(models.Model):
    class WeaknessLevel(models.TextChoices):
        HIGH = "HIGH", "High"
        MEDIUM = "MEDIUM", "Medium"
        LOW = "LOW", "Low"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weak_topics",
        db_index=True,
    )
    topic_tag = models.CharField(max_length=100, db_index=True)
    attempt_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    weakness_level = models.CharField(
        max_length=16,
        choices=WeaknessLevel.choices,
        null=True,
        blank=True,
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-last_updated",)
        verbose_name = "weak topic"
        verbose_name_plural = "weak topics"
        unique_together = [("user", "topic_tag")]

    def __str__(self):
        return f"{self.user_id}:{self.topic_tag}"


class Recommendation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendations",
        db_index=True,
    )
    lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.CASCADE,
        related_name="recommendations",
        db_index=True,
    )
    reason = models.TextField(blank=True)
    weak_topic_tag = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=16, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "recommendation"
        verbose_name_plural = "recommendations"

    def __str__(self):
        return f"{self.user_id} -> lesson {self.lesson_id}"
