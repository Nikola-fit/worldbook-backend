from django.urls import path
from .views import (
    BookDetailView,
    ParagraphSubmissionCreateView,
    ApproveParagraphSubmissionView,
    PendingSubmissionsListView,
    BookReadView,
)

urlpatterns = [
    path("books/<int:id>/read/", BookReadView.as_view()),
    path("books/<int:id>/", BookDetailView.as_view(), name="book-detail"),
    path(
        "chapters/<int:chapter_id>/submit/",
        ParagraphSubmissionCreateView.as_view(),
        name="chapter-paragraph-submit",
    ),
    path(
        "submissions/<int:submission_id>/approve/",
        ApproveParagraphSubmissionView.as_view(),
        name="paragraph-approve",
    ),
    path(
        "submissions/pending/",
        PendingSubmissionsListView.as_view(),
        name="pending-submissions",
    ),
]
