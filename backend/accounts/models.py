from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        ADMIN = "admin", "Admin"

    class ExperienceLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    username = None
    email = models.EmailField("email address", unique=True, db_index=True)
    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )
    experience_level = models.CharField(
        max_length=16,
        choices=ExperienceLevel.choices,
        blank=True,
        null=True,
        help_text="Declared learning level for adaptive personalization (students).",
    )
    profile_image = models.ImageField(
        upload_to="profile_images/%Y/%m/",
        blank=True,
        null=True,
        help_text="Optional profile photo shown in the app.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email
