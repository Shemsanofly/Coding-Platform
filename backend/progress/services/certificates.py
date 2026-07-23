from __future__ import annotations

import logging
import re
import secrets
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Q
from django.utils import timezone
from reportlab.graphics import renderPDF
from reportlab.graphics import renderSVG
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from accounts.serializers import build_full_name
from courses.models import Course, Lesson
from progress.models import Certificate, Enrollment, LessonProgress
from quizzes.models import Quiz, QuizResult

logger = logging.getLogger(__name__)


DEFAULT_PASSING_SCORE = 50
NAVY = colors.HexColor("#102C3D")
OCEAN = colors.HexColor("#15608D")
GOLD = colors.HexColor("#D9A441")
INK = colors.HexColor("#10212F")
MUTED = colors.HexColor("#5D6B78")
CREAM = colors.HexColor("#FFFDF9")
LIGHT_GOLD = colors.HexColor("#F7EFE6")
PALE_GOLD = colors.HexColor("#EFE3C8")


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


def _title_case_name(value: str) -> str:
    words = []
    for part in _clean_text(value).split():
        if "-" in part:
            words.append("-".join(piece.capitalize() for piece in part.split("-") if piece))
        else:
            words.append(part.capitalize())
    return " ".join(words)


def official_person_name(user, fallback: str = "Certificate Recipient") -> str:
    raw_parts = [getattr(user, "first_name", ""), getattr(user, "last_name", "")]
    name = _title_case_name(" ".join(part for part in raw_parts if _clean_text(part)))
    return name or fallback


def _student_name(user) -> str:
    return official_person_name(user)


def _instructor_name(course: Course) -> str:
    creator = getattr(course, "created_by", None)
    if not creator:
        return ""
    return official_person_name(creator, fallback="")


def _verification_url(verification_code: str) -> str:
    base_url = getattr(settings, "CERTIFICATE_VERIFY_BASE_URL", "") or "http://localhost:5173/verify-certificate"
    return f"{base_url.rstrip('/')}/{verification_code}"


def _unique_certificate_number() -> str:
    today = timezone.now()
    while True:
        value = f"LC-{today.strftime('%Y-%m%d')}-{secrets.token_hex(4).upper()}"
        if not Certificate.objects.filter(certificate_number=value).exists():
            return value


def _unique_verification_code() -> str:
    while True:
        value = secrets.token_hex(16).upper()
        if not Certificate.objects.filter(verification_code=value).exists():
            return value


def _clean_text(value, fallback: str = "") -> str:
    text = str(value or fallback or "")
    text = "".join(ch if ch.isprintable() else " " for ch in text)
    return re.sub(r"\s+", " ", text).strip()


def format_certificate_date(value) -> str:
    if value is None:
        return "Not specified"
    local_value = timezone.localtime(value) if hasattr(value, "tzinfo") else value
    return f"{local_value.day} {local_value.strftime('%B %Y')}"


def _course_duration(course: Course) -> str:
    minutes = sum(course.lessons.values_list("estimated_minutes", flat=True))
    if minutes <= 0:
        return ""
    if minutes == 1:
        return "1 minute"
    if minutes < 60:
        return f"{minutes} minutes"
    hours = minutes / 60
    if hours.is_integer():
        return f"{int(hours)} hour" if hours == 1 else f"{int(hours)} hours"
    return f"{hours:.1f} hours"


def _platform_name() -> str:
    return _clean_text(getattr(settings, "CERTIFICATE_PLATFORM_NAME", "LearnCode"), "LearnCode")


def _platform_website() -> str:
    return _clean_text(getattr(settings, "CERTIFICATE_PLATFORM_WEBSITE", "http://localhost:5173"))


def _ceo_name() -> str:
    return _clean_text(getattr(settings, "CERTIFICATE_CEO_NAME", "Shemsa Amin"), "Shemsa Amin")


def _ceo_title() -> str:
    return _clean_text(
        getattr(settings, "CERTIFICATE_CEO_TITLE", "Chief Executive Officer"),
        "Chief Executive Officer",
    )


def _asset_path(setting_name: str) -> Path | None:
    raw = getattr(settings, setting_name, "")
    if not raw:
        return None
    try:
        path = Path(raw)
        return path if path.exists() and path.is_file() else None
    except (OSError, ValueError):
        return None


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


def _fit_font_size(text: str, font: str, starting_size: int, max_width: float, minimum_size: int) -> int:
    size = starting_size
    text = _clean_text(text)
    while size > minimum_size and canvas.Canvas(BytesIO()).stringWidth(text, font, size) > max_width:
        size -= 1
    return size


def _qr_drawing(data: str, size: float) -> Drawing:
    qr_widget = qr.QrCodeWidget(data)
    bounds = qr_widget.getBounds()
    qr_width = bounds[2] - bounds[0]
    qr_height = bounds[3] - bounds[1]
    drawing = Drawing(size, size, transform=[size / qr_width, 0, 0, size / qr_height, 0, 0])
    drawing.add(qr_widget)
    return drawing


def certificate_qr_svg(certificate: Certificate, size: int = 160) -> str:
    data = certificate.verification_url or _verification_url(certificate.verification_code)
    svg = renderSVG.drawToString(_qr_drawing(data, size))
    if isinstance(svg, bytes):
        svg = svg.decode("utf-8")
    return re.sub(r"(<svg[^>]*>)", rf"\1<metadata>{data}</metadata>", svg, count=1)


def certificate_qr_data_url(certificate: Certificate) -> str:
    return f"data:image/svg+xml;utf8,{quote(certificate_qr_svg(certificate), safe='/:;,%#?&=+-_.')}"


def _draw_centered(c: canvas.Canvas, text: str, y: float, font: str, size: int, color=colors.black):
    width, _ = landscape(A4)
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(width / 2, y, _clean_text(text))


def _wrap_for_width(text: str, font: str, size: int, max_width: float) -> list[str]:
    words = _clean_text(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or canvas.Canvas(BytesIO()).stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _draw_wrapped_centered(
    c: canvas.Canvas,
    text: str,
    y: float,
    font: str,
    size: int,
    max_width: float,
    leading: float,
    color=colors.black,
) -> float:
    c.setFont(font, size)
    c.setFillColor(color)
    width, _ = landscape(A4)
    for idx, line in enumerate(_wrap_for_width(text, font, size, max_width)):
        c.drawCentredString(width / 2, y - idx * leading, line)
    return y - (len(_wrap_for_width(text, font, size, max_width)) * leading)


def _draw_image_preserved(c: canvas.Canvas, path: Path, x: float, y: float, max_width: float, max_height: float) -> bool:
    try:
        image = ImageReader(str(path))
        original_width, original_height = image.getSize()
        scale = min(max_width / original_width, max_height / original_height)
        draw_width = original_width * scale
        draw_height = original_height * scale
        c.drawImage(
            image,
            x + (max_width - draw_width) / 2,
            y + (max_height - draw_height) / 2,
            width=draw_width,
            height=draw_height,
            mask="auto",
            preserveAspectRatio=True,
            anchor="c",
        )
        return True
    except Exception:
        logger.exception("Could not render certificate asset at %s", path)
        return False


def _draw_logo(c: canvas.Canvas, x: float, y: float, size: float, platform_name: str) -> None:
    path = _asset_path("CERTIFICATE_LOGO_PATH")
    if path and _draw_image_preserved(c, path, x, y, size, size):
        return
    c.setFillColor(LIGHT_GOLD)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.4)
    c.roundRect(x, y, size, size, 8, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 15)
    initials = "".join(part[0] for part in platform_name.split()[:2]).upper() or "LC"
    c.drawCentredString(x + size / 2, y + size / 2 - 5, initials)


def _draw_corner_ornament(c: canvas.Canvas, x: float, y: float, sx: int, sy: int) -> None:
    c.saveState()
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(x, y, x + sx * 42, y)
    c.line(x, y, x, y + sy * 42)
    c.setLineWidth(0.6)
    c.arc(x + sx * 10 - (20 if sx < 0 else 0), y + sy * 10 - (20 if sy < 0 else 0), x + sx * 52, y + sy * 52, 0, 90)
    c.restoreState()


def _draw_watermark(c: canvas.Canvas, platform_name: str, width: float, height: float) -> None:
    c.saveState()
    c.setFillColor(colors.Color(16 / 255, 44 / 255, 61 / 255, alpha=0.035))
    c.setFont("Helvetica-Bold", 86)
    initials = "".join(part[0] for part in platform_name.split()[:2]).upper() or "LC"
    c.drawCentredString(width / 2, height / 2 - 28, initials)
    c.setStrokeColor(colors.Color(217 / 255, 164 / 255, 65 / 255, alpha=0.08))
    c.setLineWidth(2)
    c.circle(width / 2, height / 2, 94, fill=0, stroke=1)
    c.restoreState()


def _draw_official_seal(c: canvas.Canvas, center_x: float, center_y: float, year: str, platform_name: str) -> None:
    c.saveState()
    c.setStrokeColor(GOLD)
    c.setFillColor(colors.Color(1, 1, 1, alpha=0))
    c.setLineWidth(2)
    c.circle(center_x, center_y, 52, fill=0, stroke=1)
    c.setLineWidth(0.8)
    c.circle(center_x, center_y, 43, fill=0, stroke=1)
    c.setStrokeColor(PALE_GOLD)
    for offset in (-32, 32):
        c.line(center_x + offset - 9, center_y - 5, center_x + offset + 9, center_y + 10)
        c.line(center_x + offset - 9, center_y + 10, center_x + offset + 9, center_y - 5)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(center_x - 28, center_y + 26, "*")
    c.drawCentredString(center_x + 28, center_y + 26, "*")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(center_x, center_y + 15, "OFFICIAL CERTIFICATE")
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(center_x, center_y - 2, "VERIFIED")
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(center_x, center_y - 20, year)
    c.restoreState()


def _draw_signature(c: canvas.Canvas, x: float, y: float, width: float, certificate: Certificate) -> None:
    line_y = y + 34
    signature_path = _asset_path("CERTIFICATE_CEO_SIGNATURE_PATH")
    if signature_path:
        _draw_image_preserved(c, signature_path, x + 18, line_y + 6, width - 36, 48)
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.line(x, line_y, x + width, line_y)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(x + width / 2, line_y - 15, certificate.ceo_name)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawCentredString(x + width / 2, line_y - 28, certificate.ceo_title)


def _draw_qr(c: canvas.Canvas, certificate: Certificate, x: float, y: float) -> None:
    qr_size = 112
    quiet = 10
    c.setFillColor(colors.white)
    c.rect(x - quiet, y - quiet, qr_size + quiet * 2, qr_size + quiet * 2, fill=1, stroke=0)
    renderPDF.draw(_qr_drawing(certificate.verification_url or _verification_url(certificate.verification_code), qr_size), c, x, y)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x + qr_size / 2, y - 18, "Scan to verify certificate")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 6.8)
    c.drawCentredString(x + qr_size / 2, y - 31, certificate.verification_code)


def _certificate_pdf_bytes(certificate: Certificate) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4), pageCompression=0)
    width, height = landscape(A4)
    margin = 34

    c.setFillColor(CREAM)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    platform_name = _clean_text(certificate.platform_name, "LearnCode")
    _draw_watermark(c, platform_name, width, height)
    c.setStrokeColor(NAVY)
    c.setLineWidth(3.2)
    c.rect(margin, margin, width - margin * 2, height - margin * 2, fill=0, stroke=1)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.1)
    c.rect(margin + 10, margin + 10, width - (margin + 10) * 2, height - (margin + 10) * 2, fill=0, stroke=1)
    _draw_corner_ornament(c, margin + 20, height - margin - 20, 1, -1)
    _draw_corner_ornament(c, width - margin - 20, height - margin - 20, -1, -1)
    _draw_corner_ornament(c, margin + 20, margin + 20, 1, 1)
    _draw_corner_ornament(c, width - margin - 20, margin + 20, -1, 1)

    _draw_logo(c, 60, height - 86, 38, platform_name)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(106, height - 66, platform_name)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawString(106, height - 79, "Official Learning Registry")

    _draw_logo(c, width / 2 - 24, height - 88, 48, platform_name)
    _draw_centered(c, platform_name.upper(), height - 106, "Helvetica-Bold", 12, NAVY)
    _draw_centered(c, "Certificate Registry", height - 119, "Helvetica", 8, MUTED)
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawRightString(width - 58, height - 68, "CERTIFICATE NUMBER")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 58, height - 83, certificate.certificate_number)

    _draw_centered(c, "CERTIFICATE", height - 155, "Times-Bold", 42, NAVY)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(width / 2 - 118, height - 168, width / 2 + 118, height - 168)
    _draw_centered(c, "OF COMPLETION", height - 190, "Helvetica-Bold", 15, GOLD)
    _draw_centered(c, "THIS IS TO CERTIFY THAT", height - 220, "Helvetica", 10.5, MUTED)

    name_size = _fit_font_size(certificate.student_name, "Times-BoldItalic", 34, width - 180, 22)
    _draw_centered(c, certificate.student_name, height - 257, "Times-BoldItalic", name_size, INK)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.line(width / 2 - 210, height - 268, width / 2 + 210, height - 268)

    _draw_centered(
        c,
        "has successfully completed all the prescribed requirements for the course",
        height - 296,
        "Helvetica",
        10.5,
        MUTED,
    )
    course_size = _fit_font_size(certificate.course_title, "Times-Bold", 25, width - 210, 16)
    next_y = _draw_wrapped_centered(
        c,
        certificate.course_title,
        height - 331,
        "Times-Bold",
        course_size,
        width - 210,
        course_size + 4,
        NAVY,
    )
    _draw_wrapped_centered(
        c,
        (
            "and is hereby awarded this Certificate of Completion in recognition of dedication, "
            "achievement, and successful completion of the programme."
        ),
        min(next_y - 8, height - 368),
        "Helvetica",
        10,
        width - 275,
        14,
        MUTED,
    )

    issue_date = format_certificate_date(certificate.issue_date)
    completion_date = format_certificate_date(certificate.completion_date or certificate.issue_date)
    details = [
        ("Date issued", issue_date),
        ("Completion date", completion_date),
        ("Instructor", certificate.instructor_name or "Not specified"),
        ("Duration", certificate.course_duration or "Not specified"),
    ]
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    x_positions = [216, 334, 470, 608]
    y = 101
    for idx, (label, value) in enumerate(details):
        x = x_positions[idx]
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", 6.8)
        c.drawString(x, y + 10, label.upper())
        c.setFillColor(INK)
        c.setFont("Helvetica", 8)
        c.drawString(x, y - 2, _clean_text(value))

    _draw_qr(c, certificate, 72, 127)
    _draw_official_seal(c, width / 2, 146, timezone.localtime(certificate.issue_date).strftime("%Y"), platform_name)
    _draw_signature(c, width - 245, 110, 165, certificate)

    authenticity = (
        f"This certificate is issued electronically by {platform_name}. Its authenticity may be verified "
        "by scanning the QR code or entering the verification code on the official verification page."
    )
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.4)
    c.drawCentredString(width / 2, 58, _clean_text(authenticity))
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(width / 2, 46, _clean_text(certificate.platform_website or _platform_website()))

    c.showPage()
    c.save()
    return buffer.getvalue()


def _save_certificate_pdf(certificate: Certificate) -> None:
    pdf_bytes = _certificate_pdf_bytes(certificate)
    filename = f"{certificate.certificate_number}.pdf"
    certificate.file.save(filename, ContentFile(pdf_bytes), save=True)


def _filename_component(value: str, max_length: int = 60) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9-]+", "_", _clean_text(value)).strip("_")
    return (cleaned or "Certificate")[:max_length].strip("_")


def certificate_download_filename(certificate: Certificate) -> str:
    student = _filename_component(certificate.student_name)
    course = _filename_component(certificate.course_title)
    number = _filename_component(certificate.certificate_number, max_length=40)
    return f"Certificate_{student}_{course}_{number}.pdf"


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
            updates = []
            official_name = _student_name(user)
            if existing.student_name != official_name:
                existing.student_name = official_name
                updates.append("student_name")
            if not existing.verification_url:
                existing.verification_url = _verification_url(existing.verification_code)
                updates.append("verification_url")
            if updates:
                existing.save(update_fields=updates)
            return existing, False, eligibility
        if not eligibility.eligible:
            raise ValueError("; ".join(eligibility.reasons) or "Certificate eligibility requirements are not met.")

        now = timezone.now()
        if enrollment.status != Enrollment.Status.COMPLETED or enrollment.completed_at is None:
            enrollment.status = Enrollment.Status.COMPLETED
            enrollment.completed_at = now
            enrollment.save(update_fields=["status", "completed_at"])
        completion_date = enrollment.completed_at or now
        verification_code = _unique_verification_code()

        try:
            certificate = Certificate.objects.create(
                certificate_number=_unique_certificate_number(),
                verification_code=verification_code,
                student=user,
                course=course,
                enrollment=enrollment,
                student_name=_clean_text(_student_name(user), user.email),
                course_title=_clean_text(course.title),
                issue_date=now,
                completion_date=completion_date,
                platform_name=_platform_name(),
                platform_website=_platform_website(),
                instructor_name=_clean_text(_instructor_name(course)),
                course_duration=_course_duration(course),
                verification_url=_verification_url(verification_code),
                ceo_name=_ceo_name(),
                ceo_title=_ceo_title(),
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
    path = Path(certificate.file.path).resolve()
    media_root = Path(settings.MEDIA_ROOT).resolve()
    try:
        path.relative_to(media_root)
    except ValueError:
        logger.warning("Blocked certificate file outside MEDIA_ROOT certificate_id=%s path=%s", certificate.pk, path)
        return None
    return path
