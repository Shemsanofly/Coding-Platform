from django.conf import settings
from django.db import models


class Quiz(models.Model):
    class GenerationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    lesson = models.OneToOneField(
        "courses.Lesson",
        on_delete=models.CASCADE,
        related_name="quiz",
        db_index=True,
    )
    passing_score = models.PositiveSmallIntegerField(default=60)
    generation_status = models.CharField(
        max_length=16,
        choices=GenerationStatus.choices,
        default=GenerationStatus.PENDING,
    )
    generation_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Quiz"
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return f"Quiz for {self.lesson}"


class Question(models.Model):
    class QuestionType(models.TextChoices):
        MCQ = "mcq", "Multiple Choice"
        TRUE_FALSE = "true_false", "True/False"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    class BloomLevel(models.TextChoices):
        REMEMBER = "remember", "Remember"
        UNDERSTAND = "understand", "Understand"
        APPLY = "apply", "Apply"
        ANALYZE = "analyze", "Analyze"

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
        db_index=True,
    )
    order = models.PositiveSmallIntegerField(default=0)
    stem = models.TextField()
    choices = models.JSONField()
    correct_index = models.PositiveSmallIntegerField()
    topic_tag = models.CharField(max_length=100)
    question_type = models.CharField(
        max_length=16,
        choices=QuestionType.choices,
        default=QuestionType.MCQ,
        blank=True,
    )
    difficulty = models.CharField(
        max_length=16,
        choices=Difficulty.choices,
        null=True,
        blank=True,
    )
    bloom_level = models.CharField(
        max_length=16,
        choices=BloomLevel.choices,
        null=True,
        blank=True,
    )
    explanation = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "Question"
        verbose_name_plural = "Questions"

    def __str__(self):
        return f"Q{self.order} ({self.topic_tag})"


class QuizResult(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_results",
        db_index=True,
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="results",
        db_index=True,
    )
    score = models.PositiveSmallIntegerField()
    answers = models.JSONField()
    taken_at = models.DateTimeField()

    class Meta:
        ordering = ("-taken_at",)
        verbose_name = "quiz result"
        verbose_name_plural = "quiz results"

    def __str__(self):
        return f"{self.user_id} quiz={self.quiz_id} score={self.score}"
