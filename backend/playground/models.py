from django.conf import settings
from django.db import models


class PlaygroundChallenge(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SOLVED = "solved", "Solved"
        ABANDONED = "abandoned", "Abandoned"

    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="playground_challenges",
        db_index=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=16, choices=Difficulty.choices, default=Difficulty.BEGINNER)
    starter_code = models.TextField()
    test_cases = models.JSONField(default=list)
    xp_reward = models.PositiveIntegerField(default=50)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    solved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.user_id}, {self.status})"


class PlaygroundSubmission(models.Model):
    challenge = models.ForeignKey(
        PlaygroundChallenge,
        on_delete=models.CASCADE,
        related_name="submissions",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="playground_submissions",
        db_index=True,
    )
    code = models.TextField()
    passed = models.BooleanField(default=False)
    test_results = models.JSONField(default=list)
    xp_earned = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-submitted_at",)

    def __str__(self):
        return f"submission challenge={self.challenge_id} passed={self.passed}"
