from rest_framework import generics, status, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from book.models import Book, Chapter, ParagraphSubmission
from .permissions import IsSuperUser
from .serializers import (
    BookSerializer,
    ParagraphSubmissionSerializer,
    BookReadSerializer,
)
from rest_framework.views import APIView
from rest_framework.response import Response


class BookDetailView(generics.RetrieveAPIView):
    queryset = Book.objects.prefetch_related("chapters__submissions").all()
    serializer_class = BookSerializer
    lookup_field = "id"
    permission_classes = [AllowAny]


class ParagraphSubmissionCreateView(generics.CreateAPIView):
    serializer_class = ParagraphSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        chapter_id = self.kwargs.get("chapter_id")
        user = self.request.user

        try:
            chapter = Chapter.objects.get(id=chapter_id)
        except Chapter.DoesNotExist:
            raise serializers.ValidationError({"detail": "Chapter not found"})

        # Check if user already submitted a paragraph to this chapter
        if ParagraphSubmission.objects.filter(chapter=chapter, user=user).exists():
            raise serializers.ValidationError(
                {"detail": "You have already submitted a paragraph to this chapter."}
            )

        # Save the submission as pending
        serializer.save(chapter=chapter, user=user)


class ApproveParagraphSubmissionView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]

    def post(self, request, submission_id):
        try:
            submission = ParagraphSubmission.objects.select_related("chapter").get(
                id=submission_id
            )
        except ParagraphSubmission.DoesNotExist:
            return Response(
                {"detail": "Submission not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if submission.status == "approved":
            return Response(
                {"detail": "This submission is already approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Approve this submission
        submission.status = "approved"
        submission.approved_by = request.user
        submission.save()

        # Save paragraph into chapter
        chapter = submission.chapter
        chapter.content = submission.paragraph
        chapter.save()

        # Delete all other pending submissions for this chapter
        ParagraphSubmission.objects.filter(chapter=chapter, status="pending").exclude(
            id=submission.id
        ).delete()

        return Response(
            {
                "detail": "Submission approved and added to chapter.",
                "chapter_id": chapter.id,
                "updated_content": chapter.content,
            },
            status=status.HTTP_200_OK,
        )


class PendingSubmissionsListView(generics.ListAPIView):
    serializer_class = ParagraphSubmissionSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]

    def get_queryset(self):
        return ParagraphSubmission.objects.select_related("user", "chapter").filter(
            status="pending"
        )


class BookReadView(generics.RetrieveAPIView):
    queryset = Book.objects.prefetch_related("chapters").all()
    serializer_class = BookReadSerializer
    lookup_field = "id"
    permission_classes = [AllowAny]
