from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import STUDENT_ACCESS
from core.pagination import paginate_queryset
from courses.admin_services import (
    admin_analytics_overview,
    admin_dashboard_summary,
    course_stats_by_id,
    lesson_ai_fields_by_id,
)
from courses.catalog_seed import seed_basic_catalog
from courses.models import Course, CourseSource, Lesson
from courses.permissions import IsRoleAdmin
from courses.serializers import (
    AdminCourseCreateSerializer,
    AdminCourseListSerializer,
    AdminCourseUpdateSerializer,
    AdminLessonSerializer,
    StudentCourseCatalogSerializer,
    StudentLessonDetailSerializer,
    StudentLessonOutlineSerializer,
)
from courses.services import lesson_gates_for_user, lesson_unlocked
from progress.models import Enrollment, LessonProgress
from progress.serializers import CertificateSerializer
from progress.services import apply_engagement_update
from progress.services.certificates import (
    check_certificate_eligibility,
    maybe_generate_certificate_for_lesson,
)
from quizzes.models import Quiz


class AdminCourseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsRoleAdmin]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            Course.objects.filter(created_by=self.request.user)
            .annotate(lesson_count=Count("lessons", distinct=True))
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return AdminCourseCreateSerializer
        if self.action in ("partial_update", "update"):
            return AdminCourseUpdateSerializer
        return AdminCourseListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()
        output = self._course_payload(course)
        return Response(output, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        course_ids = list(queryset.values_list("pk", flat=True))
        stats_map = course_stats_by_id(course_ids)
        payload = []
        for course in queryset:
            row = dict(self._course_payload(course))
            row.update(stats_map.get(course.pk, {}))
            payload.append(row)
        return Response(payload)

    def retrieve(self, request, *args, **kwargs):
        course = self.get_object()
        stats_map = course_stats_by_id([course.pk])
        row = dict(self._course_payload(course))
        row.update(stats_map.get(course.pk, {}))
        return Response(row)

    def partial_update(self, request, *args, **kwargs):
        course = self.get_object()
        serializer = self.get_serializer(course, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        stats_map = course_stats_by_id([course.pk])
        row = dict(self._course_payload(course))
        row.update(stats_map.get(course.pk, {}))
        return Response(row)

    def _course_payload(self, course):
        return AdminCourseListSerializer(
            course,
            context=self.get_serializer_context(),
        ).data

    @action(detail=False, methods=["get"], url_path="dashboard-summary")
    def dashboard_summary(self, request):
        return Response(admin_dashboard_summary(request.user))

    @action(detail=False, methods=["get"], url_path="analytics-overview")
    def analytics_overview(self, request):
        return Response(admin_analytics_overview(request.user))

    @action(detail=False, methods=["post"], url_path="bootstrap-catalog")
    def bootstrap_catalog(self, request):
        result = seed_basic_catalog(request.user, enroll_students=True)
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="pipeline-status")
    def pipeline_status(self, request, pk=None):
        course = self.get_object()
        sources = list(course.sources.all())
        lessons = list(course.lessons.all())
        lesson_ids = [lesson.pk for lesson in lessons]

        source_statuses = [source.fetch_status for source in sources]
        quiz_statuses = list(
            Quiz.objects.filter(lesson_id__in=lesson_ids).values_list(
                "generation_status", flat=True
            )
        )

        steps = {
            "fetching_sources": self._status_from_values(source_statuses),
            "processing_text": self._processing_status(lessons, source_statuses),
            "generating_quizzes": self._status_from_values(quiz_statuses),
            "ready": (
                "done"
                if course.status in (Course.Status.READY, Course.Status.PUBLISHED)
                else "pending"
            ),
        }
        return Response({"course_id": course.pk, "steps": steps})

    def _status_from_values(self, values):
        if not values:
            return "pending"
        if any(value == "failed" for value in values):
            return "failed"
        if all(value == "done" for value in values):
            return "done"
        return "running"

    def _processing_status(self, lessons, source_statuses):
        if any(value == CourseSource.FetchStatus.FAILED for value in source_statuses):
            return "failed"
        if not source_statuses:
            return "pending"
        if all(value == CourseSource.FetchStatus.DONE for value in source_statuses):
            return "done" if lessons else "running"
        return "running"


class AdminLessonViewSet(viewsets.ModelViewSet):
    permission_classes = [IsRoleAdmin]
    serializer_class = AdminLessonSerializer
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        course_pk = self.kwargs.get("course_pk")
        if course_pk is not None:
            ctx["course"] = get_object_or_404(Course, pk=course_pk, created_by=self.request.user)
        return ctx

    def get_queryset(self):
        course = get_object_or_404(
            Course,
            pk=self.kwargs["course_pk"],
            created_by=self.request.user,
        )
        return Lesson.objects.filter(course=course).select_related("course").order_by("order", "id")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        lesson_ids = list(queryset.values_list("pk", flat=True))
        ai_map = lesson_ai_fields_by_id(lesson_ids)
        payload = []
        for lesson in queryset:
            row = dict(self.get_serializer(lesson).data)
            row.update(ai_map.get(lesson.pk, {}))
            payload.append(row)
        return Response(payload)

    def perform_create(self, serializer):
        course = get_object_or_404(
            Course,
            pk=self.kwargs["course_pk"],
            created_by=self.request.user,
        )
        max_order = (
            Lesson.objects.filter(course=course).aggregate(max_order=Max("order")).get("max_order")
        )
        next_order = (max_order or 0) + 1
        lesson = serializer.save(
            course=course,
            order=next_order,
            is_auto_generated=False,
        )
        self._maybe_start_youtube_pipeline(lesson)

    def perform_update(self, serializer):
        previous_url = ""
        if serializer.instance:
            previous_url = (serializer.instance.resource_url or "").strip()
        lesson = serializer.save()
        new_url = (lesson.resource_url or "").strip()
        if lesson.source_type == Lesson.SourceType.YOUTUBE and new_url and new_url != previous_url:
            self._maybe_start_youtube_pipeline(lesson)

    def _maybe_start_youtube_pipeline(self, lesson):
        from ai_engine.services.youtube_pipeline import (
            bootstrap_youtube_processing,
            is_youtube_lesson,
            maybe_auto_enqueue_youtube_quiz,
        )

        if not is_youtube_lesson(lesson):
            return
        bootstrap_youtube_processing(lesson)
        maybe_auto_enqueue_youtube_quiz(lesson.pk)


class StudentCourseCatalogView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        visible = Course.objects.filter(
            status__in=[Course.Status.READY, Course.Status.PUBLISHED]
        ).annotate(lesson_count=Count("lessons", distinct=True))
        enrolled_ids = list(
            Enrollment.objects.filter(user=request.user).values_list("course_id", flat=True)
        )
        level_param = (request.query_params.get("level") or "").strip().lower()
        valid_levels = {choice for choice, _ in Course.Level.choices}

        if level_param == "all":
            level_filter = None
        elif level_param in valid_levels:
            level_filter = level_param
        else:
            level_filter = getattr(request.user, "experience_level", None)

        if level_filter:
            visible = visible.filter(Q(level=level_filter) | Q(id__in=enrolled_ids))

        enroll_map = {course_id: True for course_id in enrolled_ids}
        queryset = visible.order_by("-created_at")
        context = {"request": request, "enroll_map": enroll_map}
        return paginate_queryset(
            request,
            queryset,
            serializer=StudentCourseCatalogSerializer,
            many=True,
            context=context,
        )


class StudentEnrollmentView(APIView):
    permission_classes = STUDENT_ACCESS

    def post(self, request):
        raw = request.data.get("course_id")
        try:
            course_id = int(raw)
        except (TypeError, ValueError):
            return Response(
                {"detail": "course_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        course = Course.objects.filter(
            pk=course_id,
            status__in=[Course.Status.READY, Course.Status.PUBLISHED],
        ).first()
        if not course:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)
        Enrollment.objects.get_or_create(user=request.user, course=course)
        return Response(
            {"detail": "Enrolled.", "course_id": course.id}, status=status.HTTP_201_CREATED
        )


class StudentCourseDetailView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request, course_id):
        course = get_object_or_404(
            Course.objects.filter(status__in=[Course.Status.READY, Course.Status.PUBLISHED]),
            pk=course_id,
        )
        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response(
                {"detail": "Enroll in this course to view lessons and track progress."},
                status=status.HTTP_403_FORBIDDEN,
            )
        gates = lesson_gates_for_user(course, request.user)
        gate_map = {g.lesson_id: g for g in gates}
        lessons = course.lessons.order_by("order", "pk")
        lesson_ids = [lesson.id for lesson in lessons]
        quiz_rows = {
            quiz.lesson_id: quiz
            for quiz in Quiz.objects.filter(lesson_id__in=lesson_ids).annotate(
                published_count=Count("questions", filter=Q(questions__is_published=True))
            )
        }
        progress_rows = {
            row.lesson_id: row
            for row in LessonProgress.objects.filter(user=request.user, lesson__course=course)
        }
        payload = []
        for lesson in lessons:
            g = gate_map[lesson.id]
            ser = StudentLessonOutlineSerializer(lesson)
            data = dict(ser.data)
            data["unlocked"] = g.unlocked
            data["quiz_passed"] = g.quiz_passed
            data["quiz_ready"] = g.quiz_ready
            quiz = quiz_rows.get(lesson.id)
            data["quiz_generation_status"] = quiz.generation_status if quiz else "pending"
            data["quiz_generation_error"] = (quiz.generation_error or "") if quiz else ""
            data["quiz_available"] = bool(
                quiz
                and quiz.generation_status == Quiz.GenerationStatus.DONE
                and quiz.published_count > 0
            )
            data["lesson_officially_completed"] = bool(
                progress_rows.get(lesson.id) and progress_rows[lesson.id].completed_at
            )
            payload.append(data)
        certificate_result = check_certificate_eligibility(request.user, course)
        certificate_payload = (
            CertificateSerializer(certificate_result.certificate, context={"request": request}).data
            if certificate_result.certificate
            else None
        )
        return Response(
            {
                "id": course.id,
                "title": course.title,
                "level": course.level,
                "status": course.status,
                "progress_percent": certificate_result.progress_percent,
                "completed_lessons": certificate_result.completed_lessons,
                "total_lessons": certificate_result.total_lessons,
                "certificate_eligible": certificate_result.eligible,
                "certificate_reasons": certificate_result.reasons,
                "certificate": certificate_payload,
                "lessons": payload,
            }
        )


class StudentLessonDetailView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request, lesson_id):
        lesson = get_object_or_404(
            Lesson.objects.select_related("course").prefetch_related("ai_processing"),
            pk=lesson_id,
        )
        course = lesson.course
        if course.status not in (Course.Status.READY, Course.Status.PUBLISHED):
            return Response({"detail": "Course not available."}, status=status.HTTP_404_NOT_FOUND)
        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response(
                {"detail": "Enroll in this course to access lessons."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not lesson_unlocked(course, request.user, lesson):
            return Response(
                {"detail": "Complete prior lessons and quizzes to unlock this lesson."},
                status=status.HTTP_403_FORBIDDEN,
            )
        gate_map = {g.lesson_id: g for g in lesson_gates_for_user(course, request.user)}
        g = gate_map[lesson.id]
        progress_row = LessonProgress.objects.filter(user=request.user, lesson=lesson).first()
        serializer = StudentLessonDetailSerializer(
            lesson,
            context={
                "request": request,
                "lesson_progress": progress_row,
            },
        )
        data = dict(serializer.data)
        data["unlocked"] = g.unlocked
        data["quiz_passed"] = g.quiz_passed
        data["quiz_ready"] = g.quiz_ready
        return Response(data)


class StudentLessonProgressView(APIView):
    permission_classes = STUDENT_ACCESS

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson.objects.select_related("course"), pk=lesson_id)
        course = lesson.course
        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response({"detail": "Not enrolled."}, status=status.HTTP_403_FORBIDDEN)
        if not lesson_unlocked(course, request.user, lesson):
            return Response({"detail": "Lesson locked."}, status=status.HTTP_403_FORBIDDEN)

        raw_delta = request.data.get("delta_seconds", 0)
        try:
            delta_seconds = int(raw_delta)
        except (TypeError, ValueError):
            delta_seconds = 0

        scroll_raw = request.data.get("scroll_depth_pct")
        scroll_depth_pct = None
        if scroll_raw is not None:
            try:
                scroll_depth_pct = int(scroll_raw)
            except (TypeError, ValueError):
                scroll_depth_pct = None

        video_raw = request.data.get("video_watch_pct")
        video_watch_pct = None
        if video_raw is not None:
            try:
                video_watch_pct = int(video_raw)
            except (TypeError, ValueError):
                video_watch_pct = None

        progress = apply_engagement_update(
            user_id=request.user.pk,
            lesson_id=lesson.id,
            delta_seconds=delta_seconds,
            scroll_depth_pct=scroll_depth_pct,
            video_watch_pct=video_watch_pct,
        )
        maybe_generate_certificate_for_lesson(request.user, lesson.id)
        progress.refresh_from_db()

        return Response(
            {
                "lesson_id": lesson.id,
                "seconds_engaged": progress.seconds_engaged,
                "max_scroll_depth_pct": progress.max_scroll_depth_pct,
                "video_watch_pct": progress.video_watch_pct,
                "completed_at": progress.completed_at,
            },
            status=status.HTTP_200_OK,
        )
