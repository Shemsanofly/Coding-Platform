from rest_framework import serializers

from courses.models import Course, CourseSource, Lesson
from progress.services import engagement_met, engagement_threshold_seconds

LESSON_SOURCE_TYPES_REQUIRING_URL = frozenset(
    {
        Lesson.SourceType.YOUTUBE,
        Lesson.SourceType.PDF,
        Lesson.SourceType.WEBPAGE,
        Lesson.SourceType.LINK,
    }
)


class CourseSourceWriteSerializer(serializers.ModelSerializer):
    type = serializers.ChoiceField(
        choices=CourseSource.SourceType.choices,
        write_only=True,
        required=False,
    )

    class Meta:
        model = CourseSource
        fields = ("source_type", "type", "url")

    def validate(self, attrs):
        source_type = attrs.get("source_type") or attrs.get("type")
        if not source_type:
            raise serializers.ValidationError({"source_type": "This field is required."})
        valid_types = {choice for choice, _ in CourseSource.SourceType.choices}
        if source_type not in valid_types:
            raise serializers.ValidationError(
                {"source_type": f"Unsupported source type: {source_type}"}
            )
        attrs["source_type"] = source_type
        attrs.pop("type", None)
        return attrs


class AdminCourseListSerializer(serializers.ModelSerializer):
    lesson_count = serializers.IntegerField(read_only=True)
    enrolled_students = serializers.IntegerField(read_only=True, required=False, default=0)
    pending_approval_count = serializers.IntegerField(read_only=True, required=False, default=0)
    failed_generation_count = serializers.IntegerField(read_only=True, required=False, default=0)
    quiz_lessons_done = serializers.IntegerField(read_only=True, required=False, default=0)
    quiz_lessons_pending = serializers.IntegerField(read_only=True, required=False, default=0)
    last_updated = serializers.CharField(read_only=True, allow_null=True, required=False)

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "level",
            "status",
            "lesson_count",
            "enrolled_students",
            "pending_approval_count",
            "failed_generation_count",
            "quiz_lessons_done",
            "quiz_lessons_pending",
            "last_updated",
            "created_at",
        )
        read_only_fields = fields


class AdminCourseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ("title", "level", "status")


class AdminCourseCreateSerializer(serializers.ModelSerializer):
    sources = CourseSourceWriteSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Course
        fields = ("id", "title", "level", "sources", "status", "created_at")
        read_only_fields = ("id", "status", "created_at")

    def create(self, validated_data):
        sources_data = validated_data.pop("sources", [])
        request = self.context.get("request")
        course = Course.objects.create(
            created_by=request.user,
            status=Course.Status.DRAFT,
            **validated_data,
        )
        source_objects = [
            CourseSource(
                course=course,
                source_type=item["source_type"],
                url=item["url"],
            )
            for item in sources_data
        ]
        CourseSource.objects.bulk_create(source_objects)
        return course


class AdminLessonSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(child=serializers.CharField(max_length=80), required=False)
    video_url = serializers.URLField(source="resource_url", required=False)
    difficulty_level = serializers.CharField(source="difficulty", required=False)
    topic_tags = serializers.ListField(
        source="tags", child=serializers.CharField(max_length=80), required=False
    )
    estimated_time = serializers.IntegerField(source="estimated_minutes", required=False)
    has_pdf_notes = serializers.SerializerMethodField()
    pdf_notes_url = serializers.SerializerMethodField()
    notes_generated_at = serializers.DateTimeField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is None:
            self.fields["order"].read_only = True

    ai_processing_status = serializers.CharField(read_only=True, required=False)
    quiz_generation_status = serializers.CharField(read_only=True, required=False)
    transcript_status = serializers.CharField(read_only=True, required=False)
    generated_question_count = serializers.IntegerField(read_only=True, required=False)
    published_question_count = serializers.IntegerField(read_only=True, required=False)
    approval_status = serializers.CharField(read_only=True, required=False)
    generation_error = serializers.CharField(read_only=True, required=False, allow_blank=True)
    transcript_error = serializers.CharField(read_only=True, required=False, allow_blank=True)

    class Meta:
        model = Lesson
        fields = (
            "id",
            "title",
            "source_type",
            "resource_url",
            "video_url",
            "embedded_url",
            "content",
            "transcript_text",
            "ai_summary",
            "pdf_notes",
            "has_pdf_notes",
            "pdf_notes_url",
            "notes_generated_at",
            "difficulty",
            "difficulty_level",
            "estimated_minutes",
            "estimated_time",
            "tags",
            "topic_tags",
            "learning_objective",
            "order",
            "topic_tag",
            "is_auto_generated",
            "ai_processing_status",
            "quiz_generation_status",
            "transcript_status",
            "generated_question_count",
            "published_question_count",
            "approval_status",
            "generation_error",
            "transcript_error",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "transcript_text",
            "ai_summary",
            "pdf_notes",
            "has_pdf_notes",
            "pdf_notes_url",
            "notes_generated_at",
            "embedded_url",
        )

    def get_has_pdf_notes(self, obj):
        return bool(obj.pdf_notes)

    def get_pdf_notes_url(self, obj):
        request = self.context.get("request")
        if not obj.pdf_notes:
            return ""
        if request:
            return request.build_absolute_uri(obj.pdf_notes.url)
        return obj.pdf_notes.url

    def validate_tags(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list of strings.")
        return [str(item).strip() for item in value if str(item).strip()][:40]

    def validate(self, attrs):
        if "source_type" in attrs:
            source_type = attrs["source_type"]
        elif self.instance:
            source_type = self.instance.source_type
        else:
            source_type = Lesson.SourceType.YOUTUBE

        if "resource_url" in attrs:
            resource_url = (attrs["resource_url"] or "").strip()
        elif self.instance:
            resource_url = (self.instance.resource_url or "").strip()
        else:
            resource_url = ""

        content = attrs.get("content")
        if content is None and self.instance:
            content = self.instance.content or ""
        content = (content or "").strip()

        valid_types = {choice for choice, _ in Lesson.SourceType.choices}
        if source_type not in valid_types:
            raise serializers.ValidationError(
                {"source_type": f"Unsupported source type: {source_type}"}
            )

        if source_type in LESSON_SOURCE_TYPES_REQUIRING_URL and not resource_url:
            raise serializers.ValidationError(
                {"resource_url": "A resource URL is required for this source type."}
            )
        if source_type == Lesson.SourceType.INTERNAL and not resource_url and not content:
            raise serializers.ValidationError(
                {
                    "content": "Provide lesson content or an optional reference URL for platform content."
                }
            )

        course = self.context.get("course")
        if course is None and self.instance is not None:
            course = self.instance.course

        if self.instance is None:
            attrs.pop("order", None)
        elif "order" in attrs and course is not None:
            order = attrs["order"]
            conflict = (
                Lesson.objects.filter(course=course, order=order)
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if conflict:
                raise serializers.ValidationError(
                    {"order": [f"Lesson order {order} is already used in this course."]}
                )

        if course is not None:
            allowed = Lesson.allowed_source_types_for_course_level(course.level)
            if source_type not in allowed:
                raise serializers.ValidationError(
                    {
                        "source_type": (
                            f"Source type '{source_type}' is not permitted for a "
                            f"{course.get_level_display().lower()} course."
                        )
                    }
                )
        return attrs


class StudentCourseCatalogSerializer(serializers.ModelSerializer):
    lesson_count = serializers.IntegerField(read_only=True)
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ("id", "title", "level", "status", "lesson_count", "created_at", "is_enrolled")
        read_only_fields = fields

    def get_is_enrolled(self, obj):
        enroll_map = self.context.get("enroll_map") or {}
        return enroll_map.get(obj.id, False)


class StudentLessonOutlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = (
            "id",
            "title",
            "source_type",
            "resource_url",
            "difficulty",
            "estimated_minutes",
            "tags",
            "learning_objective",
            "order",
            "topic_tag",
        )


class StudentLessonDetailSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(source="course.id", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    seconds_engaged = serializers.SerializerMethodField()
    max_scroll_depth_pct = serializers.SerializerMethodField()
    video_watch_pct = serializers.SerializerMethodField()
    engagement_required_seconds = serializers.SerializerMethodField()
    engagement_satisfied = serializers.SerializerMethodField()
    lesson_officially_completed = serializers.SerializerMethodField()
    youtube_embed_url = serializers.SerializerMethodField()
    quiz_generation_status = serializers.SerializerMethodField()
    ai_processing_status = serializers.SerializerMethodField()
    quiz_generation_error = serializers.SerializerMethodField()
    quiz_available = serializers.SerializerMethodField()
    has_pdf_notes = serializers.SerializerMethodField()
    pdf_notes_url = serializers.SerializerMethodField()
    notes_viewed_at = serializers.SerializerMethodField()
    notes_downloaded_at = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    learning_objectives = serializers.SerializerMethodField()
    key_concepts = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = (
            "id",
            "course_id",
            "course_title",
            "title",
            "source_type",
            "resource_url",
            "content",
            "summary",
            "difficulty",
            "estimated_minutes",
            "tags",
            "learning_objective",
            "learning_objectives",
            "key_concepts",
            "order",
            "topic_tag",
            "seconds_engaged",
            "max_scroll_depth_pct",
            "video_watch_pct",
            "engagement_required_seconds",
            "engagement_satisfied",
            "lesson_officially_completed",
            "youtube_embed_url",
            "quiz_generation_status",
            "ai_processing_status",
            "quiz_generation_error",
            "quiz_available",
            "has_pdf_notes",
            "pdf_notes_url",
            "notes_viewed_at",
            "notes_downloaded_at",
        )

    def _progress_row(self, obj):
        return self.context.get("lesson_progress")

    def _analysis_json(self, obj):
        processing = getattr(obj, "ai_processing", None)
        if processing is None:
            from ai_engine.models import LessonAIProcessing

            processing = LessonAIProcessing.objects.filter(lesson_id=obj.id).first()
        return (processing.analysis_json if processing else None) or {}

    def get_summary(self, obj):
        analysis = self._analysis_json(obj)
        return (analysis.get("summary") or obj.content or "").strip()

    def get_learning_objectives(self, obj):
        analysis = self._analysis_json(obj)
        objectives = analysis.get("learning_objectives")
        if isinstance(objectives, list) and objectives:
            return [str(o).strip() for o in objectives if str(o).strip()]
        text = (obj.learning_objective or "").strip()
        if not text:
            return []
        lines = []
        for line in text.splitlines():
            cleaned = line.strip().lstrip("•").strip()
            if cleaned:
                lines.append(cleaned)
        return lines or [text]

    def get_key_concepts(self, obj):
        analysis = self._analysis_json(obj)
        concepts = analysis.get("key_concepts")
        if isinstance(concepts, list):
            return [str(c).strip() for c in concepts if str(c).strip()]
        return []

    def get_seconds_engaged(self, obj):
        row = self._progress_row(obj)
        return row.seconds_engaged if row else 0

    def get_max_scroll_depth_pct(self, obj):
        row = self._progress_row(obj)
        return row.max_scroll_depth_pct if row else 0

    def get_video_watch_pct(self, obj):
        row = self._progress_row(obj)
        return row.video_watch_pct if row else None

    def get_engagement_required_seconds(self, obj):
        return engagement_threshold_seconds(obj)

    def get_engagement_satisfied(self, obj):
        row = self._progress_row(obj)
        return engagement_met(obj, row)

    def get_lesson_officially_completed(self, obj):
        row = self._progress_row(obj)
        return bool(row and row.completed_at)

    def get_quiz_generation_status(self, obj):
        from quizzes.models import Quiz

        quiz = Quiz.objects.filter(lesson_id=obj.id).only("generation_status").first()
        return quiz.generation_status if quiz else "pending"

    def get_quiz_generation_error(self, obj):
        from quizzes.models import Quiz

        quiz = Quiz.objects.filter(lesson_id=obj.id).only("generation_error").first()
        return (quiz.generation_error or "") if quiz else ""

    def get_ai_processing_status(self, obj):
        from ai_engine.models import LessonAIProcessing

        row = LessonAIProcessing.objects.filter(lesson_id=obj.id).only("status").first()
        return row.status if row else "pending"

    def get_quiz_available(self, obj):
        from django.db.models import Count, Q

        from quizzes.models import Quiz

        quiz = (
            Quiz.objects.filter(lesson_id=obj.id, generation_status=Quiz.GenerationStatus.DONE)
            .annotate(pub=Count("questions", filter=Q(questions__is_published=True)))
            .first()
        )
        return bool(quiz and quiz.pub > 0)

    def get_has_pdf_notes(self, obj):
        return bool(obj.pdf_notes)

    def get_pdf_notes_url(self, obj):
        request = self.context.get("request")
        if not obj.pdf_notes:
            return ""
        if request:
            from django.urls import reverse

            path = reverse("lesson-view-notes", kwargs={"lesson_id": obj.id})
            return request.build_absolute_uri(path)
        return ""

    def get_notes_viewed_at(self, obj):
        row = self._progress_row(obj)
        return row.notes_viewed_at if row else None

    def get_notes_downloaded_at(self, obj):
        row = self._progress_row(obj)
        return row.notes_downloaded_at if row else None

    def get_youtube_embed_url(self, obj):
        if obj.source_type != Lesson.SourceType.YOUTUBE:
            return ""
        raw = (obj.resource_url or "").strip()
        if not raw:
            return ""
        from urllib.parse import parse_qs, quote, urlparse

        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        video_id = ""
        if "youtu.be" in host:
            video_id = (parsed.path or "").strip("/").split("/")[0]
        elif "youtube.com" in host or "youtube-nocookie.com" in host:
            parts = [p for p in (parsed.path or "").split("/") if p]
            if len(parts) >= 2 and parts[0] == "embed":
                video_id = parts[1].split("?")[0]
            elif len(parts) >= 2 and parts[0] == "shorts":
                video_id = parts[1].split("?")[0]
            else:
                video_id = (parse_qs(parsed.query).get("v") or [""])[0]
        if not video_id:
            return ""
        base = f"https://www.youtube.com/embed/{video_id}?enablejsapi=1"
        request = self.context.get("request")
        if request:
            origin = request.build_absolute_uri("/").rstrip("/")
            if origin:
                return f"{base}&origin={quote(origin, safe='')}"
        return base
