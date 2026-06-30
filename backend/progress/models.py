from django.conf import settings
from django.db import models


class Enrollment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        db_index=True,
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="enrollments",
        db_index=True,
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-enrolled_at",)
        verbose_name = "enrollment"
        verbose_name_plural = "enrollments"
        unique_together = [("user", "course")]

    def __str__(self):
        return f"{self.user_id} → {self.course_id}"


class LessonProgress(models.Model):
    """Study engagement for adaptive signals (pace, completion), separate from quiz results."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
        db_index=True,
    )
    lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.CASCADE,
        related_name="progress_records",
        db_index=True,
    )
    first_opened_at = models.DateTimeField(auto_now_add=True)
    last_opened_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Official completion: quiz passed plus engagement thresholds (time / scroll / video).",
    )
    seconds_engaged = models.PositiveIntegerField(
        default=0,
        help_text="Cumulative active study seconds reported by the client.",
    )
    max_scroll_depth_pct = models.PositiveSmallIntegerField(
        default=0,
        help_text="Maximum scroll depth observed for inline content (0–100).",
    )
    video_watch_pct = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="YouTube or tracked video completion estimate (0–100).",
    )
    notes_viewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the student opened PDF study notes for this lesson.",
    )
    notes_downloaded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the student downloaded PDF study notes for this lesson.",
    )

    class Meta:
        ordering = ("-last_opened_at",)
        verbose_name = "lesson progress"
        verbose_name_plural = "lesson progress records"
        unique_together = [("user", "lesson")]

    def __str__(self):
        return f"{self.user_id}:{self.lesson_id}"
