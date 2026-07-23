from django.contrib import admin

from progress.models import Certificate, Enrollment, LessonProgress


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "status", "enrolled_at", "completed_at")
    list_filter = ("status",)
    list_select_related = ("user", "course")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "lesson", "first_opened_at", "last_opened_at", "completed_at")
    list_select_related = ("user", "lesson")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "certificate_number",
        "student_name",
        "course_title",
        "status",
        "issue_date",
        "revoked_at",
    )
    list_filter = ("status", "issue_date", "revoked_at")
    search_fields = (
        "certificate_number",
        "verification_code",
        "student_name",
        "course_title",
        "platform_name",
    )
    list_select_related = ("student", "course", "enrollment")
