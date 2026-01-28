from django.contrib import admin, messages
from django.db import transaction

from .models import Book, Chapter, ParagraphSubmission


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "number_of_chapters")
    search_fields = ("title",)
    ordering = ("id",)


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("id", "book", "chapter_number", "title")
    list_filter = ("book",)
    search_fields = ("title", "book__title", "content")
    ordering = ("book", "chapter_number")


@admin.register(ParagraphSubmission)
class ParagraphSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "chapter",
        "user",
        "status",
        "short_paragraph",
        "created_at",
        "approved_by",
    )
    list_filter = ("status", "chapter")
    search_fields = ("paragraph", "user__username", "chapter__title")
    ordering = ("-created_at",)

    # da se vidi cijeli pasus u detaljima i da se ne mijenja slučajno
    readonly_fields = ("paragraph", "created_at", "approved_by")

    fieldsets = (
        (
            "Osnovne informacije",
            {"fields": ("chapter", "user", "status", "created_at", "approved_by")},
        ),
        (
            "Sadržaj pasusa",
            {
                "fields": ("paragraph",),
                "description": "Cijeli tekst koji je korisnik poslao.",
            },
        ),
    )

    actions = ("approve_selected", "reject_selected")

    def short_paragraph(self, obj):
        if not obj.paragraph:
            return "-"
        text = obj.paragraph.strip()
        return text[:100] + ("…" if len(text) > 100 else "")

    short_paragraph.short_description = "Paragraph preview"

    @admin.action(description="Approve selected submissions (append to chapter)")
    def approve_selected(self, request, queryset):
        pending = queryset.select_related("chapter").filter(status="pending")

        if not pending.exists():
            self.message_user(
                request,
                "Nema pending submissiona za approve.",
                level=messages.WARNING,
            )
            return

        approved_count = 0

        with transaction.atomic():
            for submission in pending:
                chapter = submission.chapter

                # 1) Append u chapter.content
                existing = (chapter.content or "").strip()
                new_para = (submission.paragraph or "").strip()

                if not new_para:
                    continue

                if existing:
                    chapter.content = existing + "\n\n" + new_para
                else:
                    chapter.content = new_para

                # namjerno bez update_fields radi stabilnosti u admin okruženju
                chapter.save()

                # 2) Mark approved
                submission.status = "approved"
                submission.approved_by = request.user
                submission.save()

                # 3) Obriši ostale pending submissions za isto poglavlje
                ParagraphSubmission.objects.filter(
                    chapter=chapter, status="pending"
                ).exclude(id=submission.id).delete()

                approved_count += 1

        self.message_user(
            request,
            f"Odobreno i dodato u poglavlje: {approved_count} submission(a).",
            level=messages.SUCCESS,
        )

    @admin.action(description="Reject selected submissions")
    def reject_selected(self, request, queryset):
        pending = queryset.filter(status="pending")
        updated = 0

        with transaction.atomic():
            for submission in pending:
                submission.status = "rejected"
                submission.approved_by = request.user
                submission.save()
                updated += 1

        self.message_user(
            request,
            f"Odbijeno: {updated} submission(a).",
            level=messages.SUCCESS,
        )
