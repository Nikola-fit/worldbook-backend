from django.contrib import admin, messages
from django.db import transaction
from django.utils.html import format_html
from django.utils.formats import date_format
from django.utils.timezone import localtime

from .models import Book, Chapter, ParagraphSubmission


admin.site.site_header = "WorldBook Administration"
admin.site.site_title = "WorldBook Admin"
admin.site.index_title = "Books and paragraph review"


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
    change_list_template = "admin/book/paragraphsubmission/change_list.html"
    list_display = (
        "short_paragraph",
        "status_badge",
        "author",
        "chapter_summary",
        "submitted_on",
    )
    list_display_links = ("short_paragraph",)
    list_select_related = ("user", "chapter__book", "approved_by")
    list_filter = ("status", "chapter__book", "chapter", "created_at")
    search_fields = (
        "paragraph", "user__username", "user__email", "chapter__title",
        "chapter__book__title",
    )
    search_help_text = "Search paragraph text, author, email, book or chapter title."
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25

    # Review the original submission; moderation is performed through actions.
    readonly_fields = (
        "paragraph_text", "chapter", "user", "status_badge", "created_at",
        "approved_by",
    )

    fieldsets = (
        (
            "Submitted paragraph",
            {
                "fields": ("paragraph_text",),
                "description": "The author's original text. Return to the list to approve or reject pending submissions.",
            },
        ),
        (
            "Submission details",
            {
                "fields": ("status_badge", "user", "chapter", "created_at", "approved_by"),
            },
        ),
    )

    actions = ("approve_selected", "reject_selected")

    def has_add_permission(self, request):
        # Submissions are created by their authors through the application.
        return False

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "can_moderate_submissions": self.has_change_permission(request),
            "title": "Submitted paragraphs",
        }
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "show_save": False,
            "show_save_and_continue": False,
            "show_save_and_add_another": False,
            "title": "Review submitted paragraph",
        }
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.display(description="Paragraph preview")
    def short_paragraph(self, obj):
        if not obj.paragraph:
            return "-"
        text = obj.paragraph.strip()
        return text[:160] + ("…" if len(text) > 160 else "")

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        colors = {
            "pending": ("#fff3cd", "#664d03"),
            "approved": ("#d1e7dd", "#0f5132"),
            "rejected": ("#f8d7da", "#842029"),
        }
        background, color = colors.get(obj.status, ("#e9ecef", "#343a40"))
        return format_html(
            '<span style="background:{};color:{};padding:4px 9px;'
            'border-radius:12px;font-weight:600;white-space:nowrap">{}</span>',
            background, color, obj.get_status_display(),
        )

    @admin.display(description="Author", ordering="user__username")
    def author(self, obj):
        return obj.user.username

    @admin.display(description="Book / chapter", ordering="chapter__chapter_number")
    def chapter_summary(self, obj):
        return format_html(
            '<strong>{}</strong><br>Chapter {}: {}',
            obj.chapter.book.title, obj.chapter.chapter_number, obj.chapter.title,
        )

    @admin.display(description="Submitted", ordering="created_at")
    def submitted_on(self, obj):
        return date_format(localtime(obj.created_at), "d M Y")

    @admin.display(description="Full paragraph")
    def paragraph_text(self, obj):
        return format_html(
            '<div style="white-space:pre-wrap;overflow-wrap:anywhere;'
            'max-width:900px;font-size:16px;line-height:1.7">{}</div>',
            obj.paragraph or "-",
        )

    @admin.action(
        description="Approve selected submissions (publish to chapter)",
        permissions=["change"],
    )
    def approve_selected(self, request, queryset):
        pending = queryset.select_related("chapter").filter(status="pending")

        if not pending.exists():
            self.message_user(
                request,
                "No pending submissions were selected.",
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
            f"Published {approved_count} submission(s) to their chapters.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Reject selected submissions", permissions=["change"])
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
            f"Rejected {updated} submission(s).",
            level=messages.SUCCESS,
        )
