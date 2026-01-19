from rest_framework import serializers
from book.models import Book, Chapter, ParagraphSubmission


class ParagraphSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParagraphSubmission
        fields = ["id", "paragraph", "status", "user", "chapter", "created_at"]
        read_only_fields = ["id", "user", "chapter", "status", "created_at"]


# --- ADMIN/DEBUG (sa submissions) ---
class ChapterSerializer(serializers.ModelSerializer):
    submissions = ParagraphSubmissionSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ["id", "title", "content", "chapter_number", "submissions"]
        read_only_fields = ["id"]


class BookSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = ["id", "title", "number_of_chapters", "chapters"]
        read_only_fields = ["id"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["chapters"] = sorted(
            representation["chapters"], key=lambda x: x["chapter_number"]
        )
        return representation


# --- READ (bez submissions) ---
class ChapterReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ["id", "title", "chapter_number", "content"]
        read_only_fields = ["id"]


class BookReadSerializer(serializers.ModelSerializer):
    chapters = ChapterReadSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = ["id", "title", "number_of_chapters", "chapters"]
        read_only_fields = ["id"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["chapters"] = sorted(
            representation["chapters"], key=lambda x: x["chapter_number"]
        )
        return representation
