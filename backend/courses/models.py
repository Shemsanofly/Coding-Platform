from django.conf import settings
from django.db import models


class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=255)
    level = models.CharField(max_length=16, choices=Level.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "course"
        verbose_name_plural = "courses"

    def __str__(self):
        return self.title


class CourseSource(models.Model):
    """Ingestion source for course content pipelines."""

    class SourceType(models.TextChoices):
        YOUTUBE = "youtube", "YouTube"
        PDF = "pdf", "PDF"
        WEBPAGE = "webpage", "Web page"
        LINK = "link", "External link"
        INTERNAL = "internal", "Platform content"

    class FetchStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        FETCHING = "fetching", "Fetching"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="sources",
        db_index=True,
    )
    url = models.URLField(max_length=500)
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    fetch_status = models.CharField(
        max_length=16,
        choices=FetchStatus.choices,
        default=FetchStatus.PENDING,
    )
    fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("pk",)
        verbose_name = "course source"
        verbose_name_plural = "course sources"
        unique_together = [("course", "url")]

    def __str__(self):
        return f"{self.course_id}: {self.url[:48]}"


class Lesson(models.Model):
    """Platform-controlled lesson backed by a video, document, page, or internal content."""

    class SourceType(models.TextChoices):
        YOUTUBE = "youtube", "YouTube"
        PDF = "pdf", "PDF"
        WEBPAGE = "webpage", "Web page"
        LINK = "link", "External link"
        INTERNAL = "internal", "Platform content"

    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    @classmethod
    def allowed_source_types_for_course_level(cls, course_level: str) -> frozenset[str]:
        _ = course_level
        return frozenset(choice for choice, _ in cls.SourceType.choices)

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
        db_index=True,
    )
    title = models.CharField(max_length=255)
    source_type = models.CharField(
        max_length=32,
        choices=SourceType.choices,
        default=SourceType.YOUTUBE,
    )
    resource_url = models.URLField(max_length=500, blank=True)
    content = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=16,
        choices=Difficulty.choices,
        default=Difficulty.BEGINNER,
    )
    estimated_minutes = models.PositiveSmallIntegerField(default=15)
    tags = models.JSONField(default=list, blank=True)
    learning_objective = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    topic_tag = models.CharField(max_length=100, blank=True)
    is_auto_generated = models.BooleanField(default=True)
    embedded_url = models.URLField(max_length=500, blank=True)
    transcript_text = models.TextField(blank=True)
    ai_summary = models.JSONField(null=True, blank=True)
    pdf_notes = models.FileField(upload_to="pdf_notes/", blank=True)
    notes_generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "pk")
        verbose_name = "lesson"
        verbose_name_plural = "lessons"
        unique_together = [("course", "order")]

    def __str__(self):
        return f"{self.course_id}: {self.title}"
