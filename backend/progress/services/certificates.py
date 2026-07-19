from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Q
from django.utils import timezone
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from accounts.serializers import build_full_name
from courses.models import Course, Lesson
from progress.models import Certificate, Enrollment, LessonProgress
from quizzes.models import Quiz, QuizResult

logger = logging.getLogger(__name__)


DEFAULT_PASSING_SCORE = 50


@dataclass(frozen=True)
class CertificateEligibility:
    eligible: bool
    reasons: list[str]
    progress_percent: float
    completed_lessons: int
    total_lessons: int
    final_score: int | None
    passing_score: int
    enrollment: Enrollment | None
    certificate: Certificate | None


def _student_name(user) -> str:
    return build_full_name(user)


def _instructor_name(course: Course) -> str:
    creator = getattr(course, "created_by", None)
    if not creator:
        return ""
    return build_full_name(creator)


def _verification_url(verification_code: str) -> str:
    base_url = getattr(settings, "CERTIFICATE_VERIFY_BASE_URL", "") or "http://localhost:5173/verify-certificate"
    return f"{base_url.rstrip('/')}/{verification_code}"


def _unique_certificate_number() -> str:
    today = timezone.now().strftime("%Y%m%d")
    while True:
        value = f"LC-{today}-{secrets.token_hex(4).upper()}"
        if not Certificate.objects.filter(certificate_number=value).exists():
            return value


def _unique_verification_code() -> str:
    while True:
        value = secrets.token_urlsafe(24)
        if not Certificate.objects.filter(verification_code=value).exists():
            return value


def _final_lesson(course: Course) -> Lesson | None:
    return course.lessons.order_by("-order", "-pk").first()


def _final_assessment_score(user_id: int, course: Course) -> tuple[int | None, int, bool, str]:
    lesson = _final_lesson(course)
    if lesson is None:
        return None, DEFAULT_PASSING_SCORE, False, "missing"

    quiz = (
        Quiz.objects.filter(lesson=lesson)
        .annotate(published_count=Count("questions", filter=Q(questions__is_published=True)))
        .first()
    )
    if quiz is None:
        return None, DEFAULT_PASSING_SCORE, False, "missing"
    if quiz.generation_status != Quiz.GenerationStatus.DONE or quiz.published_count == 0:
        return None, quiz.passing_score or DEFAULT_PASSING_SCORE, False, "unavailable"

    passing_score = quiz.passing_score or DEFAULT_PASSING_SCORE
    best = (
        QuizResult.objects.filter(user_id=user_id, quiz=quiz)
        .aggregate(value=Max("score"))
        .get("value")
    )
    return best, passing_score, best is not None and best >= passing_score, "ready"


def check_certificate_eligibility(user, course: Course) -> CertificateEligibility:
    enrollment = Enrollment.objects.filter(user=user, course=course).first()
    certificate = None
    reasons: list[str] = []
    if enrollment is None:
        reasons.append("Enroll in this course.")
    else:
        certificate = Certificate.objects.filter(enrollment=enrollment).first()

    lessons = list(course.lessons.order_by("order", "pk").only("id"))
    total_lessons = len(lessons)
    lesson_ids = [lesson.id for lesson in lessons]
    completed_lessons = 0
    if lesson_ids:
        completed_lessons = LessonProgress.objects.filter(
            user=user,
            lesson_id__in=lesson_ids,
            completed_at__isnull=False,
        ).count()
    progress_percent = round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0.0

    if total_lessons == 0:
        reasons.append("Course has no lessons.")
    elif completed_lessons < total_lessons:
        reasons.append("Complete all required lessons.")

    final_score, passing_score, final_passed, assessment_status = _final_assessment_score(user.id, course)
    if not final_passed:
        if assessment_status == "unavailable":
            reasons.append("Final assessment is not available yet.")
        else:
            reasons.append("Pass the final assessment.")

    # No assignment model exists in this codebase. Absence of assignment rows means this rule passes.
    eligible = bool(enrollment and total_lessons > 0 and progress_percent == 100 and final_passed)
    return CertificateEligibility(
        eligible=eligible,
        reasons=[] if eligible else reasons,
        progress_percent=progress_percent,
        completed_lessons=completed_lessons,
        total_lessons=total_lessons,
        final_score=final_score,
        passing_score=passing_score,
        enrollment=enrollment,
        certificate=certificate,
    )


def _draw_centered(c: canvas.Canvas, text: str, y: float, font: str, size: int, color=colors.black):
    width, _ = landscape(letter)
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(width / 2, y, text)


def _certificate_pdf_bytes(certificate: Certificate) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    c.setFillColor(colors.HexColor("#F8FAF7"))
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#0F766E"))
    c.setLineWidth(5)
    c.rect(0.45 * inch, 0.45 * inch, width - 0.9 * inch, height - 0.9 * inch, fill=0, stroke=1)
    c.setStrokeColor(colors.HexColor("#F9735B"))
    c.setLineWidth(1.2)
    c.rect(0.65 * inch, 0.65 * inch, width - 1.3 * inch, height - 1.3 * inch, fill=0, stroke=1)

    _draw_centered(c, "LearnCode", height - 1.1 * inch, "Helvetica-Bold", 18, colors.HexColor("#0F766E"))
    _draw_centered(
        c,
        "Certificate of Completion",
        height - 1.8 * inch,
        "Helvetica-Bold",
        30,
        colors.HexColor("#111827"),
    )
    _draw_centered(c, "This certifies that", height - 2.45 * inch, "Helvetica", 13, colors.HexColor("#4B5563"))
    _draw_centered(c, certificate.student_name, height - 3.05 * inch, "Helvetica-Bold", 28, colors.HexColor("#0B3B3C"))
    _draw_centered(c, "successfully completed", height - 3.55 * inch, "Helvetica", 13, colors.HexColor("#4B5563"))
    _draw_centered(c, certificate.course_title, height - 4.05 * inch, "Helvetica-Bold", 22, colors.HexColor("#111827"))

    issue_date = timezone.localtime(certificate.issue_date).date().isoformat()
    instructor = _instructor_name(certificate.course)
    details = [
        f"Completion date: {issue_date}",
        f"Certificate number: {certificate.certificate_number}",
        f"Verification code: {certificate.verification_code}",
    ]
    if instructor:
        details.insert(1, f"Instructor: {instructor}")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#374151"))
    for idx, detail in enumerate(details):
        c.drawString(1.05 * inch, 1.55 * inch - (idx * 0.22 * inch), detail)

    qr_widget = qr.QrCodeWidget(_verification_url(certificate.verification_code))
    bounds = qr_widget.getBounds()
    qr_width = bounds[2] - bounds[0]
    qr_height = bounds[3] - bounds[1]
    size = 1.15 * inch
    drawing = Drawing(size, size, transform=[size / qr_width, 0, 0, size / qr_height, 0, 0])
    drawing.add(qr_widget)
    renderPDF.draw(drawing, c, width - 2.25 * inch, 1.05 * inch)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#4B5563"))
    c.drawCentredString(width - 1.67 * inch, 0.83 * inch, "Scan to verify")

    c.showPage()
    c.save()
    return buffer.getvalue()


def _save_certificate_pdf(certificate: Certificate) -> None:
    pdf_bytes = _certificate_pdf_bytes(certificate)
    filename = f"{certificate.certificate_number}.pdf"
    certificate.file.save(filename, ContentFile(pdf_bytes), save=True)


def generate_or_get_certificate(user, course_id: int) -> tuple[Certificate, bool, CertificateEligibility]:
    with transaction.atomic():
        course = Course.objects.select_related("created_by").filter(pk=course_id).first()
        if course is None:
            raise ValueError("Course not found.")

        enrollment = (
            Enrollment.objects.select_for_update()
            .filter(user=user, course=course)
            .select_related("user", "course")
            .first()
        )
        if enrollment is None:
            raise PermissionError("You are not enrolled in this course.")

        existing = Certificate.objects.filter(enrollment=enrollment).first()
        eligibility = check_certificate_eligibility(user, course)
        if existing:
            return existing, False, eligibility
        if not eligibility.eligible:
            raise ValueError("; ".join(eligibility.reasons) or "Certificate eligibility requirements are not met.")

        now = timezone.now()
        if enrollment.status != Enrollment.Status.COMPLETED or enrollment.completed_at is None:
            enrollment.status = Enrollment.Status.COMPLETED
            enrollment.completed_at = now
            enrollment.save(update_fields=["status", "completed_at"])

        try:
            certificate = Certificate.objects.create(
                certificate_number=_unique_certificate_number(),
                verification_code=_unique_verification_code(),
                student=user,
                course=course,
                enrollment=enrollment,
                student_name=_student_name(user),
                course_title=course.title,
                issue_date=now,
                status=Certificate.Status.ACTIVE,
            )
        except IntegrityError:
            certificate = Certificate.objects.get(enrollment=enrollment)
            return certificate, False, eligibility

        _save_certificate_pdf(certificate)
        logger.info(
            "Generated certificate id=%s enrollment_id=%s course_id=%s student_id=%s",
            certificate.pk,
            enrollment.pk,
            course.pk,
            user.pk,
        )
        return certificate, True, eligibility


def maybe_generate_certificate_for_course(user, course_id: int) -> Certificate | None:
    try:
        eligibility = check_certificate_eligibility(user, Course.objects.get(pk=course_id))
        if not eligibility.eligible or eligibility.certificate:
            return eligibility.certificate
        certificate, _, _ = generate_or_get_certificate(user, course_id)
        return certificate
    except Exception:
        logger.exception("Automatic certificate generation failed for user_id=%s course_id=%s", user.pk, course_id)
        return None


def maybe_generate_certificate_for_lesson(user, lesson_id: int) -> Certificate | None:
    lesson = Lesson.objects.filter(pk=lesson_id).only("id", "course_id").first()
    if lesson is None:
        return None
    return maybe_generate_certificate_for_course(user, lesson.course_id)


def certificate_file_path(certificate: Certificate) -> Path | None:
    if not certificate.file:
        return None
    return Path(certificate.file.path)
