from django.db import transaction

from accounts.models import User
from courses.models import Course, Lesson
from progress.models import Enrollment
from quizzes.models import Question, Quiz


def _lesson(title, content, topic_tag, resource_url):
    return {
        "title": title,
        "content": content,
        "topic_tag": topic_tag,
        "source_type": Lesson.SourceType.YOUTUBE,
        "resource_url": resource_url,
        "difficulty": "beginner",
        "estimated_minutes": 20,
        "tags": [topic_tag] if topic_tag else [],
        "learning_objective": f"Understand core ideas behind {topic_tag or title}.",
        "questions": [
            {
                "stem": f"What is the primary focus of '{title}'?",
                "choices": [
                    content.split(".")[0][:80],
                    "Database indexing strategy",
                    "Cloud billing optimization",
                    "UI animation timing",
                ],
                "correct_index": 0,
                "topic_tag": topic_tag,
            },
            {
                "stem": f"Which topic best matches this lesson: {title}?",
                "choices": [topic_tag, "networking", "devops", "design_systems"],
                "correct_index": 0,
                "topic_tag": topic_tag,
            },
        ],
    }


BASIC_COURSE_CATALOG = [
    {
        "title": "Programming Foundations",
        "level": "beginner",
        "lessons": [
            _lesson(
                "How Programs Work",
                "Programs are step-by-step instructions executed by a computer.",
                "program_basics",
                "https://www.youtube.com/watch?v=zOjov-2OZ0E",
            ),
            _lesson(
                "Variables and Data Types",
                "Variables store values such as numbers, text, and booleans.",
                "variables",
                "https://www.youtube.com/watch?v=8DvywoWv6fI",
            ),
            _lesson(
                "Operators and Expressions",
                "Operators combine values into expressions that compute results.",
                "operators",
                "https://www.youtube.com/watch?v=rfscVS0vtbw",
            ),
            _lesson(
                "Debugging Basics",
                "Debugging means tracing behavior and fixing mistakes in logic or syntax.",
                "debugging",
                "https://www.youtube.com/watch?v=aircAruvnKk",
            ),
        ],
    },
]


def create_course_lessons_and_quizzes(course, lessons):
    for lesson_order, lesson in enumerate(lessons):
        tag_list = []
        if lesson.get("topic_tag"):
            tag_list.append(lesson["topic_tag"])
        lesson_obj = Lesson.objects.create(
            course=course,
            title=lesson["title"],
            content=lesson.get("content", ""),
            source_type=lesson.get("source_type", Lesson.SourceType.YOUTUBE),
            resource_url=lesson.get("resource_url", ""),
            difficulty=lesson.get("difficulty", course.level),
            estimated_minutes=lesson.get("estimated_minutes", 20),
            tags=lesson.get("tags", tag_list),
            learning_objective=lesson.get(
                "learning_objective",
                f"Build confidence with {lesson.get('topic_tag') or lesson['title']}.",
            ),
            order=lesson_order,
            topic_tag=lesson.get("topic_tag", ""),
            is_auto_generated=False,
        )
        quiz = Quiz.objects.create(
            lesson=lesson_obj,
            passing_score=60,
            generation_status=Quiz.GenerationStatus.DONE,
        )
        for question_order, question in enumerate(lesson["questions"]):
            Question.objects.create(
                quiz=quiz,
                order=question_order,
                stem=question["stem"],
                choices=question["choices"],
                correct_index=question["correct_index"],
                topic_tag=question["topic_tag"],
            )


def seed_basic_catalog(creator, *, enroll_students=True):
    if creator is None:
        raise ValueError("A catalog creator user is required.")

    created_ids = []
    catalog_titles = [item["title"] for item in BASIC_COURSE_CATALOG]

    with transaction.atomic():
        for item in BASIC_COURSE_CATALOG:
            course, was_created = Course.objects.get_or_create(
                created_by=creator,
                title=item["title"],
                defaults={
                    "level": item["level"],
                    "status": Course.Status.READY,
                },
            )
            if was_created:
                create_course_lessons_and_quizzes(course, item["lessons"])
                created_ids.append(course.id)

        if enroll_students:
            catalog_courses = Course.objects.filter(
                created_by=creator,
                title__in=catalog_titles,
            )
            student_ids = User.objects.filter(role=User.Role.STUDENT).values_list("id", flat=True)
            for course in catalog_courses:
                for student_id in student_ids:
                    Enrollment.objects.get_or_create(user_id=student_id, course=course)

    return {
        "created_count": len(created_ids),
        "created_ids": created_ids,
        "catalog_course_ids": list(
            Course.objects.filter(created_by=creator, title__in=catalog_titles).values_list("id", flat=True)
        ),
    }
