from django.contrib import admin

from progress.models import Enrollment, LessonProgress


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "enrolled_at")
    list_select_related = ("user", "course")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "lesson", "first_opened_at", "last_opened_at", "completed_at")
    list_select_related = ("user", "lesson")
