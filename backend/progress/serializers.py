from rest_framework import serializers

from progress.models import Certificate


class RecentQuizScoreSerializer(serializers.Serializer):
    score = serializers.IntegerField()
    taken_at = serializers.DateTimeField()
    lesson_title = serializers.CharField(allow_blank=True)


class StudentAnalyticsSummarySerializer(serializers.Serializer):
    enrolled_course_count = serializers.IntegerField()
    total_lessons_in_enrolled_courses = serializers.IntegerField()
    lessons_passed_quiz = serializers.IntegerField()
    lessons_remaining = serializers.IntegerField()
    quiz_attempts_total = serializers.IntegerField()
    avg_quiz_score = serializers.FloatField()
    weak_topics_tracked = serializers.IntegerField()
    active_recommendations_count = serializers.IntegerField()
    learning_level = serializers.CharField(allow_null=True)
    recent_quiz_scores = RecentQuizScoreSerializer(many=True)


class EnrollmentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    level = serializers.CharField()
    lesson_count = serializers.IntegerField()
    lessons_completed = serializers.IntegerField()
    avg_quiz_score = serializers.FloatField()
    progress = serializers.FloatField()


class CertificateSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    qr_code_data_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = (
            "id",
            "certificate_number",
            "verification_code",
            "student_name",
            "course_title",
            "course_id",
            "enrollment_id",
            "issue_date",
            "completion_date",
            "platform_name",
            "platform_website",
            "instructor_name",
            "course_duration",
            "verification_url",
            "ceo_name",
            "ceo_title",
            "file_url",
            "qr_code_data_url",
            "status",
            "revoked_at",
            "created_at",
        )
        read_only_fields = fields

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.file:
            return ""
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

    def get_qr_code_data_url(self, obj):
        from progress.services.certificates import certificate_qr_data_url

        return certificate_qr_data_url(obj)


class CertificateEligibilitySerializer(serializers.Serializer):
    eligible = serializers.BooleanField()
    reasons = serializers.ListField(child=serializers.CharField())
    progress_percent = serializers.FloatField()
    completed_lessons = serializers.IntegerField()
    total_lessons = serializers.IntegerField()
    final_score = serializers.IntegerField(allow_null=True)
    passing_score = serializers.IntegerField()
    certificate = CertificateSerializer(allow_null=True)


class PublicCertificateVerificationSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    verification_status = serializers.CharField()
    student_name = serializers.CharField(allow_blank=True)
    course_title = serializers.CharField(allow_blank=True)
    issue_date = serializers.DateTimeField(allow_null=True)
    completion_date = serializers.DateTimeField(allow_null=True)
    certificate_number = serializers.CharField(allow_blank=True)
    certificate_status = serializers.CharField(allow_blank=True)
    platform_name = serializers.CharField(allow_blank=True)


class WeakTopicCourseContextSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()


class WeakTopicLessonContextSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    course_id = serializers.IntegerField()
    course_title = serializers.CharField()
    score = serializers.IntegerField(required=False, allow_null=True)


class WeakTopicSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    topic = serializers.CharField()
    topic_tag = serializers.CharField()
    level = serializers.CharField(allow_null=True)
    weakness_level = serializers.CharField(allow_null=True)
    attempt_count = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    score = serializers.FloatField()
    accuracy = serializers.FloatField(required=False)
    accuracy_percent = serializers.FloatField(required=False)
    last_updated = serializers.DateTimeField(allow_null=True)
    courses = WeakTopicCourseContextSerializer(many=True, required=False)
    recent_lessons = WeakTopicLessonContextSerializer(many=True, required=False)


class WeakTopicLessonGroupSerializer(serializers.Serializer):
    lesson = serializers.DictField()
    course = serializers.DictField()
    quiz_result_id = serializers.IntegerField(required=False, allow_null=True)
    score = serializers.IntegerField(required=False, allow_null=True)
    weak_topics = serializers.ListField()
    recommended_lessons = serializers.ListField(required=False)


class WeaknessListResponseSerializer(serializers.Serializer):
    topics = WeakTopicSerializer(many=True)
    lesson_groups = WeakTopicLessonGroupSerializer(many=True, required=False)
    courses = WeakTopicCourseContextSerializer(many=True, required=False)


class RecommendationLessonBlockSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    course_id = serializers.IntegerField()
    course_title = serializers.CharField()


class RecommendationRelatedLessonSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()


class RecommendationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    course_id = serializers.IntegerField(allow_null=True)
    course_title = serializers.CharField(allow_blank=True, required=False)
    lesson_id = serializers.IntegerField()
    title = serializers.CharField()
    lesson_title = serializers.CharField()
    reason = serializers.CharField()
    triggered_by = serializers.CharField(allow_blank=True)
    weak_topic_tag = serializers.CharField(allow_blank=True, required=False)
    weakness_level = serializers.CharField(allow_null=True, required=False)
    accuracy_percent = serializers.FloatField(allow_null=True, required=False)
    attempt_count = serializers.IntegerField(allow_null=True, required=False)
    correct_count = serializers.IntegerField(allow_null=True, required=False)
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    source_type = serializers.CharField(allow_blank=True, required=False)
    resource_url = serializers.CharField(allow_blank=True, required=False)
    lesson = RecommendationLessonBlockSerializer(required=False)
    related_lessons_taken = RecommendationRelatedLessonSerializer(many=True, required=False)
    focus_area = serializers.CharField(allow_blank=True, required=False)


class LessonWeaknessSummarySerializer(serializers.Serializer):
    lesson = serializers.DictField()
    course = serializers.DictField()
    quiz_taken = serializers.BooleanField()
    score = serializers.IntegerField(allow_null=True, required=False)
    quiz_result_id = serializers.IntegerField(allow_null=True, required=False)
    weak_topics = serializers.ListField()
    recommended_lessons = serializers.ListField()
    message = serializers.CharField(allow_blank=True, required=False)


class AdminUserListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    enrolled_courses = serializers.IntegerField()
    completed_lessons = serializers.IntegerField(required=False)
    avg_score = serializers.FloatField(allow_null=True)
    last_active = serializers.DateTimeField(allow_null=True)
    top_weakness_topic = serializers.CharField(allow_null=True)
    top_weakness_level = serializers.CharField(allow_null=True)
    weak_topics_count = serializers.IntegerField(required=False)
    learning_level = serializers.CharField(allow_null=True, required=False)
    is_active = serializers.BooleanField(required=False)


class AdminUserProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    enrolled_count = serializers.IntegerField()
    completed_lessons = serializers.IntegerField(required=False)
    avg_score = serializers.FloatField(allow_null=True)
    quiz_attempts = serializers.IntegerField()
    last_active = serializers.DateTimeField(allow_null=True)
    learning_level = serializers.CharField(allow_null=True, required=False)
    weak_topics_count = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField(required=False)
    role = serializers.CharField(required=False)


class AdminStudentUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    experience_level = serializers.ChoiceField(
        choices=["beginner", "intermediate", "advanced"],
        required=False,
        allow_null=True,
    )
    role = serializers.ChoiceField(choices=["student"], required=False)
    is_active = serializers.BooleanField(required=False)


class AdminQuizLogSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    quiz_title = serializers.CharField()
    score = serializers.IntegerField()
    accuracy = serializers.FloatField()
    taken_at = serializers.DateTimeField()


class PracticeWeeklyActivitySerializer(serializers.Serializer):
    label = serializers.CharField()
    date = serializers.CharField()
    attempts = serializers.IntegerField()
    height_pct = serializers.IntegerField()


class PracticeLeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField(required=False, allow_null=True)
    user_id = serializers.IntegerField()
    display_name = serializers.CharField()
    learning_level = serializers.CharField(allow_null=True, required=False)
    practice_xp = serializers.IntegerField()
    quiz_attempts = serializers.IntegerField()
    exercises_passed = serializers.IntegerField()
    lessons_mastered = serializers.IntegerField()
    lessons_completed = serializers.IntegerField()
    avg_score = serializers.FloatField()
    streak_days = serializers.IntegerField()
    tier_title = serializers.CharField()
    tier_icon = serializers.CharField()
    tier_progress_pct = serializers.IntegerField()
    next_tier_title = serializers.CharField(allow_null=True, required=False)
    next_tier_xp = serializers.IntegerField(allow_null=True, required=False)
    weekly_activity = PracticeWeeklyActivitySerializer(many=True, required=False)


class PracticeLeaderboardSerializer(serializers.Serializer):
    leaderboard = PracticeLeaderboardEntrySerializer(many=True)
    total_students = serializers.IntegerField()
    me = PracticeLeaderboardEntrySerializer(allow_null=True)
