"""PDF report endpoints for admin and student users."""

from __future__ import annotations

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import STUDENT_ACCESS
from progress.services.report_generator import (
    ReportDataError,
    build_admin_ai_generation_report,
    build_admin_courses_report,
    build_admin_students_report,
    build_admin_summary_report,
    build_admin_weaknesses_report,
    build_student_learning_path_report,
    build_student_progress_report,
    build_student_quiz_performance_report,
    build_student_weaknesses_report,
)


def _pdf_http_response(pdf_bytes: bytes, filename: str) -> HttpResponse:
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


class _AdminReportMixin:
    permission_classes = [IsAuthenticated]

    def _ensure_admin(self, request):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class AdminSummaryReportView(_AdminReportMixin, APIView):
    def get(self, request):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        try:
            pdf_bytes = build_admin_summary_report(
                request.user,
                from_date=request.query_params.get("from"),
                to_date=request.query_params.get("to"),
            )
        except ReportDataError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return _pdf_http_response(pdf_bytes, "admin-platform-summary.pdf")


class AdminCoursesReportView(_AdminReportMixin, APIView):
    def get(self, request):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        course_id = request.query_params.get("course_id")
        try:
            pdf_bytes = build_admin_courses_report(
                request.user,
                course_id=int(course_id) if course_id else None,
                from_date=request.query_params.get("from"),
                to_date=request.query_params.get("to"),
            )
        except ValueError:
            return Response({"detail": "Invalid course id."}, status=400)
        except ReportDataError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        filename = f"course-report-{course_id}.pdf" if course_id else "course-performance-report.pdf"
        return _pdf_http_response(pdf_bytes, filename)


class AdminStudentsReportView(_AdminReportMixin, APIView):
    def get(self, request):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        student_id = request.query_params.get("student_id")
        try:
            pdf_bytes = build_admin_students_report(
                request.user,
                student_id=int(student_id) if student_id else None,
                from_date=request.query_params.get("from"),
                to_date=request.query_params.get("to"),
            )
        except ValueError:
            return Response({"detail": "Invalid student id."}, status=400)
        except ReportDataError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        filename = f"student-report-{student_id}.pdf" if student_id else "student-performance-report.pdf"
        return _pdf_http_response(pdf_bytes, filename)


class AdminWeaknessesReportView(_AdminReportMixin, APIView):
    def get(self, request):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        try:
            pdf_bytes = build_admin_weaknesses_report(
                request.user,
                from_date=request.query_params.get("from"),
                to_date=request.query_params.get("to"),
            )
        except ReportDataError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return _pdf_http_response(pdf_bytes, "weak-topic-summary.pdf")


class AdminAIGenerationReportView(_AdminReportMixin, APIView):
    def get(self, request):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        try:
            pdf_bytes = build_admin_ai_generation_report(request.user)
        except ReportDataError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return _pdf_http_response(pdf_bytes, "ai-quiz-generation-status.pdf")


class StudentProgressReportView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        try:
            pdf_bytes = build_student_progress_report(request.user)
        except ReportDataError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return _pdf_http_response(pdf_bytes, "my-learning-progress.pdf")


class StudentQuizPerformanceReportView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        try:
            pdf_bytes = build_student_quiz_performance_report(
                request.user,
                from_date=request.query_params.get("from"),
                to_date=request.query_params.get("to"),
            )
        except ReportDataError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return _pdf_http_response(pdf_bytes, "my-quiz-performance.pdf")


class StudentWeaknessesReportView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        try:
            pdf_bytes = build_student_weaknesses_report(request.user)
        except ReportDataError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return _pdf_http_response(pdf_bytes, "my-weak-topics.pdf")


class StudentLearningPathReportView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        try:
            pdf_bytes = build_student_learning_path_report(request.user)
        except ReportDataError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)
        return _pdf_http_response(pdf_bytes, "my-learning-path.pdf")
