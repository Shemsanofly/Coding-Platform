from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.db.models import Avg, Count, Max, Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from accounts.permissions import STUDENT_ACCESS
from core.pagination import paginate_queryset
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_engine.models import WeakTopic
from courses.models import Course, Lesson
from progress.models import Enrollment, LessonProgress
from progress.models import Certificate
from progress.services import quiz_passed_for_lesson
from progress.services.certificates import (
    certificate_file_path,
    check_certificate_eligibility,
    generate_or_get_certificate,
)
from playground.serializers import PlaygroundLeaderboardSerializer
from playground.services.leaderboard import build_playground_leaderboard
from progress.serializers import (
    AdminQuizLogSerializer,
    AdminStudentUpdateSerializer,
    AdminUserListSerializer,
    AdminUserProfileSerializer,
    CertificateEligibilitySerializer,
    CertificateSerializer,
    EnrollmentSerializer,
    LessonWeaknessSummarySerializer,
    PublicCertificateVerificationSerializer,
    RecommendationSerializer,
    StudentAnalyticsSummarySerializer,
    WeaknessListResponseSerializer,
    WeakTopicSerializer,
)
from quizzes.models import QuizResult

User = get_user_model()


def _parse_course_id(request):
    from progress.services.weakness_context import parse_course_id_param

    return parse_course_id_param(request.query_params.get("course_id"))


class _AdminRoleRequiredMixin:
    permission_classes = [IsAuthenticated]

    def _ensure_admin(self, request):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class EnrollmentListView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        from progress.services.student_dashboard import build_student_enrollments

        payload = build_student_enrollments(request.user)
        return paginate_queryset(
            request,
            payload,
            serializer=EnrollmentSerializer,
            many=True,
        )


class WeaknessListView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        from progress.services.weakness_context import (
            build_lesson_weakness_groups,
            build_topic_context_index,
            ensure_enrolled_in_course,
            enrich_weak_topic_payload,
            list_enrolled_courses_for_filter,
            topic_matches_course,
        )

        course_id = _parse_course_id(request)
        access_error = ensure_enrolled_in_course(request.user, course_id)
        if access_error:
            return Response({"detail": access_error}, status=status.HTTP_403_FORBIDDEN)

        course_ids = None
        if course_id is not None:
            course_ids = [course_id]

        context_index = build_topic_context_index(request.user.id, course_ids=course_ids)
        topics_qs = WeakTopic.objects.filter(user=request.user).order_by("-last_updated", "topic_tag")
        topics_payload = []
        for topic in topics_qs:
            if course_id is not None and not topic_matches_course(topic.topic_tag, course_id, context_index):
                continue
            topics_payload.append(enrich_weak_topic_payload(topic, context_index))

        lesson_groups = build_lesson_weakness_groups(request.user.id, course_ids=course_ids)
        response_payload = {
            "topics": topics_payload,
            "lesson_groups": lesson_groups,
            "courses": list_enrolled_courses_for_filter(request.user.id),
        }
        return Response(WeaknessListResponseSerializer(response_payload).data)


class LessonWeaknessSummaryView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request, lesson_id):
        from progress.services.weakness_context import lesson_weakness_summary

        lesson = Lesson.objects.select_related("course").filter(pk=lesson_id).first()
        if not lesson:
            return Response({"detail": "Lesson not found."}, status=status.HTTP_404_NOT_FOUND)
        if not Enrollment.objects.filter(user=request.user, course_id=lesson.course_id).exists():
            return Response(
                {"detail": "You are not enrolled in this course."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = lesson_weakness_summary(request.user.id, lesson)
        return Response(LessonWeaknessSummarySerializer(payload).data)


def _weak_topic_lookup(user):
    lookup = {}
    for topic in WeakTopic.objects.filter(user=user):
        tag = (topic.topic_tag or "").strip().lower()
        if tag:
            lookup[tag] = topic
    return lookup


def _enrich_recommendation_row(rec_row, weakness_lookup):
    weak_tag = (rec_row.get("weak_topic_tag") or rec_row.get("triggered_by") or "").strip()
    if weak_tag.lower() in ("adaptive_engine", "learning_path", "weakness_overlap", ""):
        weak_tag = rec_row.get("weak_topic_tag") or ""
    if not weak_tag:
        rec_row.setdefault("weak_topic_tag", "")
        rec_row.setdefault("weakness_level", None)
        rec_row.setdefault("accuracy_percent", None)
        rec_row.setdefault("attempt_count", None)
        rec_row.setdefault("correct_count", None)
        return rec_row

    rec_row["weak_topic_tag"] = weak_tag
    wt = weakness_lookup.get(weak_tag.strip().lower())
    if wt:
        accuracy = round((wt.correct_count / wt.attempt_count) * 100, 1) if wt.attempt_count else 0
        rec_row["weakness_level"] = wt.weakness_level
        rec_row["accuracy_percent"] = accuracy
        rec_row["attempt_count"] = wt.attempt_count
        rec_row["correct_count"] = wt.correct_count
    else:
        rec_row.setdefault("weakness_level", None)
        rec_row.setdefault("accuracy_percent", None)
        rec_row.setdefault("attempt_count", None)
        rec_row.setdefault("correct_count", None)
    return rec_row


class RecommendationListView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        from ai_engine.models import Recommendation
        from progress.services.weakness_context import (
            build_topic_context_index,
            ensure_enrolled_in_course,
            enrich_recommendation_payload,
        )

        course_id = _parse_course_id(request)
        access_error = ensure_enrolled_in_course(request.user, course_id)
        if access_error:
            return Response({"detail": access_error}, status=status.HTTP_403_FORBIDDEN)

        weakness_lookup = _weak_topic_lookup(request.user)
        course_ids = [course_id] if course_id is not None else None
        topic_index = build_topic_context_index(request.user.id, course_ids=course_ids)

        payload = []
        rows = (
            Recommendation.objects.filter(user=request.user, status="active")
            .select_related("lesson__course")
            .order_by("-created_at")
        )
        if course_id is not None:
            rows = rows.filter(lesson__course_id=course_id)
        rows = rows[:12]

        for rec in rows:
            course = rec.lesson.course
            payload.append(
                enrich_recommendation_payload(
                    {
                        "id": rec.id,
                        "course_id": course.id,
                        "course_title": course.title,
                        "lesson_id": rec.lesson_id,
                        "title": course.title,
                        "lesson_title": rec.lesson.title,
                        "reason": rec.reason,
                        "triggered_by": rec.weak_topic_tag or "adaptive_engine",
                        "weak_topic_tag": rec.weak_topic_tag or "",
                        "status": rec.status,
                        "created_at": rec.created_at,
                        "source_type": rec.lesson.source_type,
                        "resource_url": rec.lesson.resource_url or "",
                    },
                    weakness_lookup=weakness_lookup,
                    topic_index=topic_index,
                )
            )

        if course_id is None and len(payload) < 3:
            for row in _build_next_course_recommendations(request.user):
                payload.append(
                    enrich_recommendation_payload(
                        row,
                        weakness_lookup=weakness_lookup,
                        topic_index=topic_index,
                    )
                )

        return Response(RecommendationSerializer(payload, many=True).data)


class StudentAnalyticsSummaryView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        from progress.services.student_dashboard import build_student_analytics_summary

        payload = build_student_analytics_summary(request.user)
        return Response(StudentAnalyticsSummarySerializer(payload).data)


class StudentDashboardView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        from progress.services.student_dashboard import build_student_dashboard_payload

        return Response(build_student_dashboard_payload(request.user))


class StudentPracticeLeaderboardView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        payload = build_playground_leaderboard(current_user_id=request.user.id)
        return Response(PlaygroundLeaderboardSerializer(payload).data)


def _certificate_eligibility_payload(result, request):
    return {
        "eligible": result.eligible,
        "reasons": result.reasons,
        "progress_percent": result.progress_percent,
        "completed_lessons": result.completed_lessons,
        "total_lessons": result.total_lessons,
        "final_score": result.final_score,
        "passing_score": result.passing_score,
        "certificate": CertificateSerializer(result.certificate, context={"request": request}).data
        if result.certificate
        else None,
    }


class StudentCourseCertificateEligibilityView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request, course_id):
        course = Course.objects.filter(pk=course_id).first()
        if course is None:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)
        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response(
                {"detail": "You are not enrolled in this course."},
                status=status.HTTP_403_FORBIDDEN,
            )
        result = check_certificate_eligibility(request.user, course)
        data = _certificate_eligibility_payload(result, request)
        return Response(CertificateEligibilitySerializer(data).data)


class StudentCourseCertificateView(APIView):
    permission_classes = STUDENT_ACCESS

    def post(self, request, course_id):
        course = Course.objects.filter(pk=course_id).first()
        if course is None:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            certificate, created, _ = generate_or_get_certificate(request.user, course_id)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            CertificateSerializer(certificate, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MyCertificatesView(APIView):
    permission_classes = STUDENT_ACCESS

    def get(self, request):
        certificates = (
            Certificate.objects.filter(student=request.user)
            .select_related("course", "enrollment")
            .order_by("-issue_date")
        )
        return Response(CertificateSerializer(certificates, many=True, context={"request": request}).data)


class CertificateDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, certificate_id):
        certificate = Certificate.objects.select_related("student").filter(pk=certificate_id).first()
        if certificate is None:
            return Response({"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND)
        is_owner = request.user.pk == certificate.student_id
        is_admin = getattr(request.user, "role", None) == User.Role.ADMIN
        if not is_owner and not is_admin:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        path = certificate_file_path(certificate)
        if path is None or not path.exists():
            return Response({"detail": "Certificate PDF not found."}, status=status.HTTP_404_NOT_FOUND)
        response = FileResponse(open(path, "rb"), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{certificate.certificate_number}.pdf"'
        return response


class PublicCertificateVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, verification_code):
        certificate = Certificate.objects.filter(verification_code=verification_code).first()
        if certificate is None:
            data = {
                "valid": False,
                "student_name": "",
                "course_title": "",
                "issue_date": None,
                "certificate_number": "",
                "certificate_status": "",
            }
        else:
            data = {
                "valid": certificate.status == Certificate.Status.ACTIVE,
                "student_name": certificate.student_name,
                "course_title": certificate.course_title,
                "issue_date": certificate.issue_date,
                "certificate_number": certificate.certificate_number,
                "certificate_status": certificate.status,
            }
        return Response(PublicCertificateVerificationSerializer(data).data)


class AdminCertificateRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, certificate_id):
        if getattr(request.user, "role", None) != User.Role.ADMIN:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        certificate = Certificate.objects.filter(pk=certificate_id).first()
        if certificate is None:
            return Response({"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND)
        certificate.status = Certificate.Status.REVOKED
        certificate.save(update_fields=["status"])
        return Response(CertificateSerializer(certificate, context={"request": request}).data)


class AdminUsersView(_AdminRoleRequiredMixin, APIView):
    def get(self, request):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=403)

        search = (request.query_params.get("search") or "").strip()
        weakness_level = (request.query_params.get("weakness_level") or "").strip().upper()
        ordering = (request.query_params.get("ordering") or "").strip()

        queryset = User.objects.filter(role=User.Role.STUDENT)
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        if weakness_level:
            matching_user_ids = WeakTopic.objects.filter(
                weakness_level=weakness_level,
            ).values_list("user_id", flat=True)
            queryset = queryset.filter(id__in=matching_user_ids)

        if ordering == "avg_score":
            queryset = queryset.annotate(avg_score=Avg("quiz_results__score")).order_by(
                "avg_score", "email"
            )
        elif ordering == "-avg_score":
            queryset = queryset.annotate(avg_score=Avg("quiz_results__score")).order_by(
                "-avg_score", "email"
            )
        else:
            queryset = queryset.order_by("first_name", "last_name", "email")

        from core.pagination import StandardPagination

        paginator = StandardPagination()
        page_users = paginator.paginate_queryset(queryset, request)
        users = page_users if page_users is not None else list(queryset)
        user_ids = [user.id for user in users]

        if not user_ids:
            if page_users is not None:
                return paginator.get_paginated_response([])
            return Response([])

        enroll_counts = {
            row["user_id"]: row["total"]
            for row in Enrollment.objects.filter(user_id__in=user_ids)
            .values("user_id")
            .annotate(total=Count("id"))
        }
        score_map = {
            row["user_id"]: row["avg"]
            for row in QuizResult.objects.filter(user_id__in=user_ids)
            .values("user_id")
            .annotate(avg=Avg("score"))
        }
        last_active_map = {
            row["user_id"]: row["last_taken"]
            for row in QuizResult.objects.filter(user_id__in=user_ids)
            .values("user_id")
            .annotate(last_taken=Max("taken_at"))
        }
        completed_map = {
            row["user_id"]: row["total"]
            for row in LessonProgress.objects.filter(
                user_id__in=user_ids, completed_at__isnull=False
            )
            .values("user_id")
            .annotate(total=Count("id"))
        }
        weak_count_map = {
            row["user_id"]: row["total"]
            for row in WeakTopic.objects.filter(user_id__in=user_ids)
            .values("user_id")
            .annotate(total=Count("id"))
        }
        weak_topics = WeakTopic.objects.filter(user_id__in=user_ids).order_by("user_id", "-last_updated")
        top_weakness_by_user = {}
        for topic in weak_topics:
            if topic.user_id not in top_weakness_by_user:
                top_weakness_by_user[topic.user_id] = topic

        payload = []
        for user in users:
            full_name = f"{user.first_name} {user.last_name}".strip() or user.email.split("@")[0]
            weakness = top_weakness_by_user.get(user.id)
            payload.append(
                {
                    "id": user.id,
                    "name": full_name,
                    "full_name": full_name,
                    "email": user.email,
                    "enrolled_courses": enroll_counts.get(user.id, 0),
                    "completed_lessons": completed_map.get(user.id, 0),
                    "avg_score": score_map.get(user.id),
                    "last_active": last_active_map.get(user.id),
                    "top_weakness_topic": weakness.topic_tag if weakness else None,
                    "top_weakness_level": weakness.weakness_level if weakness else None,
                    "weak_topics_count": weak_count_map.get(user.id, 0),
                    "learning_level": getattr(user, "experience_level", None),
                    "is_active": user.is_active,
                }
            )

        serialized = AdminUserListSerializer(payload, many=True).data
        if page_users is not None:
            return paginator.get_paginated_response(serialized)
        return Response(serialized)


class AdminUserProfileView(_AdminRoleRequiredMixin, APIView):
    def get(self, request, user_id):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=403)

        user = User.objects.filter(id=user_id, role="student").first()
        if not user:
            return Response({"detail": "User not found."}, status=404)

        full_name = f"{user.first_name} {user.last_name}".strip() or user.email.split("@")[0]
        enrolled_count = Enrollment.objects.filter(user_id=user.id).count()
        completed_lessons = LessonProgress.objects.filter(
            user_id=user.id, completed_at__isnull=False
        ).count()
        weak_topics_count = WeakTopic.objects.filter(user_id=user.id).count()
        quiz_rows = QuizResult.objects.filter(user_id=user.id)
        avg_score = quiz_rows.aggregate(value=Avg("score"))["value"]
        last_active = quiz_rows.order_by("-taken_at").values_list("taken_at", flat=True).first()

        data = {
            "id": user.id,
            "name": full_name,
            "full_name": full_name,
            "email": user.email,
            "enrolled_count": enrolled_count,
            "completed_lessons": completed_lessons,
            "avg_score": avg_score,
            "quiz_attempts": quiz_rows.count(),
            "last_active": last_active,
            "learning_level": getattr(user, "experience_level", None),
            "weak_topics_count": weak_topics_count,
            "is_active": user.is_active,
            "role": user.role,
        }
        return Response(AdminUserProfileSerializer(data).data)


def _get_admin_student(user_id):
    return User.objects.filter(id=user_id, role=User.Role.STUDENT).first()


def _student_profile_payload(user):
    full_name = f"{user.first_name} {user.last_name}".strip() or user.email.split("@")[0]
    enrolled_count = Enrollment.objects.filter(user_id=user.id).count()
    completed_lessons = LessonProgress.objects.filter(
        user_id=user.id, completed_at__isnull=False
    ).count()
    weak_topics_count = WeakTopic.objects.filter(user_id=user.id).count()
    quiz_rows = QuizResult.objects.filter(user_id=user.id)
    avg_score = quiz_rows.aggregate(value=Avg("score"))["value"]
    last_active = quiz_rows.order_by("-taken_at").values_list("taken_at", flat=True).first()
    return {
        "id": user.id,
        "name": full_name,
        "full_name": full_name,
        "email": user.email,
        "enrolled_count": enrolled_count,
        "completed_lessons": completed_lessons,
        "avg_score": avg_score,
        "quiz_attempts": quiz_rows.count(),
        "last_active": last_active,
        "learning_level": getattr(user, "experience_level", None),
        "weak_topics_count": weak_topics_count,
        "is_active": user.is_active,
        "role": user.role,
    }


class AdminStudentDetailView(_AdminRoleRequiredMixin, APIView):
    def patch(self, request, user_id):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        if request.user.id == user_id:
            return Response(
                {"detail": "You cannot edit your own account from the student management screen."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = _get_admin_student(user_id)
        if not user:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminStudentUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "email" in data:
            normalized = User.objects.normalize_email(data["email"])
            if User.objects.exclude(pk=user.pk).filter(email=normalized).exists():
                return Response({"email": ["A user with this email already exists."]}, status=400)
            user.email = normalized

        if "experience_level" in data:
            user.experience_level = data["experience_level"]

        if "role" in data and data["role"] != User.Role.STUDENT:
            return Response({"role": ["Only the student role is allowed here."]}, status=400)

        if "is_active" in data:
            user.is_active = data["is_active"]

        user.save()
        return Response(_student_profile_payload(user))

    def delete(self, request, user_id):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        if request.user.id == user_id:
            return Response(
                {"detail": "You cannot deactivate your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = _get_admin_student(user_id)
        if not user:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(
            {"detail": "Student deactivated.", "id": user.id, "is_active": user.is_active},
            status=status.HTTP_200_OK,
        )


class AdminStudentPurgeView(_AdminRoleRequiredMixin, APIView):
    """Permanently remove a deactivated student and related data (CASCADE)."""

    def post(self, request, user_id):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        if request.user.id == user_id:
            return Response(
                {"detail": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = _get_admin_student(user_id)
        if not user:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.is_active:
            return Response(
                {"detail": "Deactivate the student before permanently deleting their account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = user.email
        user_id_deleted = user.id
        user.delete()
        return Response(
            {"detail": "Student permanently deleted.", "id": user_id_deleted, "email": email},
            status=status.HTTP_200_OK,
        )


class AdminUserWeaknessesView(_AdminRoleRequiredMixin, APIView):
    def get(self, request, user_id):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        topics = WeakTopic.objects.filter(user_id=user_id).order_by("-last_updated", "topic_tag")
        payload = [
            {
                "id": topic.id,
                "topic": topic.topic_tag,
                "topic_tag": topic.topic_tag,
                "level": topic.weakness_level,
                "weakness_level": topic.weakness_level,
                "attempt_count": topic.attempt_count,
                "correct_count": topic.correct_count,
                "score": round((topic.correct_count / topic.attempt_count) * 100, 1)
                if topic.attempt_count
                else 0,
                "last_updated": topic.last_updated,
            }
            for topic in topics
        ]
        return Response(WeakTopicSerializer(payload, many=True).data)


class AdminUserRecommendationsView(_AdminRoleRequiredMixin, APIView):
    def get(self, request, user_id):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        user = User.objects.filter(id=user_id, role="student").first()
        if not user:
            return Response({"detail": "User not found."}, status=404)
        from ai_engine.models import Recommendation

        payload = []
        for rec in (
            Recommendation.objects.filter(user_id=user.id, status="active")
            .select_related("lesson__course")
            .order_by("-created_at")[:20]
        ):
            course = rec.lesson.course
            payload.append(
                {
                    "id": rec.id,
                    "course_id": course.id,
                    "course_title": course.title,
                    "lesson_id": rec.lesson_id,
                    "title": course.title,
                    "lesson_title": rec.lesson.title,
                    "reason": rec.reason,
                    "triggered_by": rec.weak_topic_tag or "adaptive_engine",
                    "status": rec.status,
                    "created_at": rec.created_at,
                    "source_type": rec.lesson.source_type,
                    "resource_url": rec.lesson.resource_url or "",
                }
            )
        if len(payload) < 3:
            payload.extend(_build_next_course_recommendations(user))
        return Response(RecommendationSerializer(payload, many=True).data)


class AdminUserQuizLogView(_AdminRoleRequiredMixin, APIView):
    def get(self, request, user_id):
        if not self._ensure_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        rows = (
            QuizResult.objects.filter(user_id=user_id)
            .select_related("quiz__lesson")
            .order_by("-taken_at")
        )
        payload = [
            {
                "id": row.id,
                "quiz_title": f"{row.quiz.lesson.title} quiz",
                "score": row.score,
                "accuracy": row.score,
                "taken_at": row.taken_at,
            }
            for row in rows
        ]
        return Response(AdminQuizLogSerializer(payload, many=True).data)


def _build_next_course_recommendations(user):
    enrolled_ids = set(
        Enrollment.objects.filter(user=user).values_list("course_id", flat=True)
    )
    weakness_topics = list(
        WeakTopic.objects.filter(user=user, weakness_level__in=["HIGH", "MEDIUM"]).values_list(
            "topic_tag",
            flat=True,
        )
    )

    candidate_courses = Course.objects.exclude(id__in=enrolled_ids).order_by("created_at")
    scored = []
    for course in candidate_courses:
        lesson_topics = set(course.lessons.values_list("topic_tag", flat=True))
        overlap = len(lesson_topics.intersection(weakness_topics))
        scored.append((overlap, course))

    scored.sort(key=lambda row: (-row[0], row[1].created_at))
    top = scored[:3]

    payload = []
    for idx, (overlap, course) in enumerate(top, start=1):
        first_lesson = course.lessons.order_by("order").first()
        reason = (
            "Recommended because it targets your weak topics."
            if overlap > 0
            else "Recommended as your next learning step."
        )
        payload.append(
            {
                "id": -(1000 + idx),
                "course_id": course.id,
                "course_title": course.title,
                "lesson_id": first_lesson.id if first_lesson else 0,
                "title": course.title,
                "lesson_title": first_lesson.title if first_lesson else course.title,
                "reason": reason,
                "triggered_by": "weakness_overlap" if overlap > 0 else "learning_path",
                "status": "active",
                "created_at": course.created_at,
                "source_type": first_lesson.source_type if first_lesson else "",
                "resource_url": (first_lesson.resource_url or "") if first_lesson else "",
            }
        )
    return payload
