from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from .models import Book, Chapter, ParagraphSubmission


class SubmissionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.author = user_model.objects.create_user(
            username="author", email="author@example.com"
        )
        cls.other_author = user_model.objects.create_user(
            username="other-author", email="other@example.com"
        )
        cls.reader = user_model.objects.create_user(
            username="reader", email="reader@example.com"
        )
        cls.superuser = user_model.objects.create_superuser(
            username="admin", email="admin@example.com", password="test-password"
        )
        cls.viewer = user_model.objects.create_user(
            username="viewer", email="viewer@example.com", is_staff=True
        )
        cls.moderator = user_model.objects.create_user(
            username="moderator", email="moderator@example.com", is_staff=True
        )
        cls.staff_without_permission = user_model.objects.create_user(
            username="staff", email="staff@example.com", is_staff=True
        )
        cls.viewer.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="book", codename="view_paragraphsubmission"
            )
        )
        cls.moderator.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="book", codename="change_paragraphsubmission"
            )
        )
        cls.book = Book.objects.create(title="WorldBook", number_of_chapters=2)
        cls.chapter = Chapter.objects.create(
            book=cls.book, title="First chapter", chapter_number=1,
            content="Published chapter text.",
        )
        cls.second_chapter = Chapter.objects.create(
            book=cls.book, title="Second chapter", chapter_number=2,
            content="Second published chapter.",
        )
        cls.own_pending = ParagraphSubmission.objects.create(
            chapter=cls.chapter, user=cls.author, paragraph="Author's private pending paragraph."
        )
        cls.own_approved = ParagraphSubmission.objects.create(
            chapter=cls.second_chapter, user=cls.author, status="approved",
            paragraph="Author's approved submission record.",
        )
        cls.own_rejected = ParagraphSubmission.objects.create(
            chapter=cls.second_chapter, user=cls.author, status="rejected",
            paragraph="Author's private rejected paragraph.",
        )
        cls.other_pending = ParagraphSubmission.objects.create(
            chapter=cls.chapter, user=cls.other_author,
            paragraph='<script>alert("test")</script>\nOther author private text.',
        )
        cls.other_rejected = ParagraphSubmission.objects.create(
            chapter=cls.second_chapter, user=cls.other_author, status="rejected",
            paragraph="Other author's rejected submission.",
        )
        cls.detail_url = reverse("book-detail", kwargs={"id": cls.book.id})
        cls.admin_list_url = reverse("admin:book_paragraphsubmission_changelist")


class SubmissionPrivacyTests(SubmissionTestCase):
    def setUp(self):
        self.api = APIClient()

    def authenticate(self, user):
        # Exercise the real JWT authentication path used by the frontend.
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")

    def submission_ids(self, response):
        return {
            submission["id"]
            for chapter in response.data["chapters"]
            for submission in chapter["submissions"]
        }

    def test_anonymous_cannot_read_submission_details(self):
        response = self.api.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("chapters", response.data)

    def test_invalid_token_cannot_read_submission_details(self):
        self.api.credentials(HTTP_AUTHORIZATION="Bearer not-a-valid-token")
        self.assertEqual(self.api.get(self.detail_url).status_code, 401)

    def test_author_sees_only_own_submissions_in_every_status(self):
        self.authenticate(self.author)
        response = self.api.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.submission_ids(response), {
            self.own_pending.id, self.own_approved.id, self.own_rejected.id,
        })
        for chapter in response.data["chapters"]:
            for submission in chapter["submissions"]:
                self.assertEqual(submission["user"], self.author.id)
        self.assertNotIn(self.other_pending.paragraph, str(response.data))
        self.assertNotIn(self.other_rejected.paragraph, str(response.data))

    def test_switching_users_does_not_reuse_another_users_submissions(self):
        self.authenticate(self.superuser)
        self.api.get(self.detail_url)
        self.authenticate(self.other_author)
        response = self.api.get(self.detail_url)
        self.assertEqual(self.submission_ids(response), {
            self.other_pending.id, self.other_rejected.id,
        })

    def test_reader_without_submissions_sees_empty_submission_lists(self):
        self.authenticate(self.reader)
        response = self.api.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.submission_ids(response), set())
        self.assertEqual(response.data["chapters"][0]["content"], self.chapter.content)

    def test_superuser_sees_all_submissions(self):
        self.authenticate(self.superuser)
        response = self.api.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.submission_ids(response),
            set(ParagraphSubmission.objects.values_list("id", flat=True)),
        )

    def test_staff_with_view_or_change_permission_sees_all_submissions(self):
        for user in (self.viewer, self.moderator):
            with self.subTest(user=user.username):
                self.authenticate(user)
                response = self.api.get(self.detail_url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.submission_ids(response), set(
                    ParagraphSubmission.objects.values_list("id", flat=True)
                ))

    def test_staff_without_model_permission_cannot_see_others_submissions(self):
        self.authenticate(self.staff_without_permission)
        response = self.api.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.submission_ids(response), set())

    def test_nonstaff_with_model_permission_still_sees_only_own_submissions(self):
        self.author.user_permissions.add(Permission.objects.get(
            content_type__app_label="book", codename="view_paragraphsubmission"
        ))
        self.authenticate(self.author)
        response = self.api.get(self.detail_url)
        self.assertEqual(self.submission_ids(response), {
            self.own_pending.id, self.own_approved.id, self.own_rejected.id,
        })

    def test_inactive_user_cannot_read_submission_details(self):
        self.authenticate(self.author)
        self.author.is_active = False
        self.author.save(update_fields=["is_active"])
        self.assertEqual(self.api.get(self.detail_url).status_code, 401)

    def test_public_reading_exposes_only_published_chapter_fields(self):
        response = self.api.get(f"/book/books/{self.book.id}/read/")
        self.assertEqual(response.status_code, 200)
        for chapter in response.data["chapters"]:
            self.assertEqual(set(chapter), {"id", "title", "chapter_number", "content"})
        self.assertEqual(response.data["chapters"][0]["content"], self.chapter.content)
        self.assertNotIn(self.own_pending.paragraph, str(response.data))
        self.assertNotIn(self.other_pending.paragraph, str(response.data))

    def test_authors_cannot_fetch_pending_list_or_approve(self):
        self.authenticate(self.author)
        self.assertEqual(self.api.get(reverse("pending-submissions")).status_code, 403)
        response = self.api.post(reverse("paragraph-approve", kwargs={
            "submission_id": self.other_pending.id,
        }))
        self.assertEqual(response.status_code, 403)
        self.other_pending.refresh_from_db()
        self.assertEqual(self.other_pending.status, "pending")

    def test_own_status_endpoint_remains_scoped_to_logged_in_user(self):
        url = reverse("my-submission-status", kwargs={"chapter_id": self.chapter.id})
        self.authenticate(self.author)
        self.assertEqual(self.api.get(url).data, {"status": "pending"})
        self.authenticate(self.reader)
        self.assertEqual(self.api.get(url).data, {"status": "none"})

    def test_submitting_cannot_spoof_author_or_approved_status(self):
        self.authenticate(self.reader)
        response = self.api.post(reverse("chapter-paragraph-submit", kwargs={
            "chapter_id": self.chapter.id,
        }), {
            "paragraph": "New private paragraph.", "user": self.superuser.id,
            "status": "approved", "chapter": self.second_chapter.id,
        }, format="json")
        self.assertEqual(response.status_code, 201)
        submission = ParagraphSubmission.objects.get(id=response.data["id"])
        self.assertEqual(submission.user_id, self.reader.id)
        self.assertEqual(submission.chapter_id, self.chapter.id)
        self.assertEqual(submission.status, "pending")
        self.authenticate(self.author)
        self.assertNotIn(submission.id, self.submission_ids(self.api.get(self.detail_url)))


class SubmissionAdminTests(SubmissionTestCase):
    def test_superuser_overview_has_preview_filters_and_review_shortcuts(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.admin_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WorldBook Administration")
        self.assertContains(response, "Paragraph review")
        self.assertContains(response, "Pending submissions")
        self.assertContains(response, "removes other pending submissions")
        self.assertContains(response, escape(self.own_pending.paragraph))
        self.assertEqual(response.context["cl"].list_per_page, 25)

    def test_pending_filter_keeps_reviewed_submissions_out_of_results(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.admin_list_url, {"status__exact": "pending"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual({obj.id for obj in response.context["cl"].result_list}, {
            self.own_pending.id, self.other_pending.id,
        })

    def test_search_by_author_email_and_book(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.admin_list_url, {"q": "author@example.com"})
        self.assertEqual({obj.id for obj in response.context["cl"].result_list}, {
            self.own_pending.id, self.own_approved.id, self.own_rejected.id,
        })
        response = self.client.get(self.admin_list_url, {"q": "WorldBook"})
        self.assertEqual(len(response.context["cl"].result_list), 5)

    def test_full_paragraph_is_readable_escaped_and_not_editable(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:book_paragraphsubmission_change", args=[
            self.other_pending.id,
        ]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, escape(self.other_pending.paragraph))
        self.assertContains(response, "white-space:pre-wrap")
        self.assertNotContains(response, self.other_pending.paragraph)
        self.assertNotContains(response, 'name="status"')
        self.assertNotContains(response, 'name="paragraph"')
        self.assertNotContains(response, 'name="_save"')

    def test_normal_users_and_unpermitted_staff_cannot_open_admin_submissions(self):
        self.assertEqual(self.client.get(self.admin_list_url).status_code, 302)
        self.client.force_login(self.author)
        self.assertEqual(self.client.get(self.admin_list_url).status_code, 302)
        self.client.force_login(self.staff_without_permission)
        self.assertEqual(self.client.get(self.admin_list_url).status_code, 403)

    def test_view_only_staff_can_read_but_cannot_execute_moderation_actions(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.admin_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["cl"].result_list), 5)
        self.assertNotContains(response, 'value="approve_selected"')
        self.assertNotContains(response, 'value="reject_selected"')
        for action in ("approve_selected", "reject_selected"):
            self.client.post(self.admin_list_url, {
                "action": action, "_selected_action": [self.own_pending.id],
            })
            self.own_pending.refresh_from_db()
            self.assertEqual(self.own_pending.status, "pending")
        response = self.client.get(reverse("admin:book_paragraphsubmission_change", args=[
            self.own_pending.id,
        ]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, escape(self.own_pending.paragraph))

    def test_moderator_can_reject_without_deleting_the_submission(self):
        self.client.force_login(self.moderator)
        response = self.client.post(self.admin_list_url, {
            "action": "reject_selected", "_selected_action": [self.own_pending.id],
        })
        self.assertEqual(response.status_code, 302)
        self.own_pending.refresh_from_db()
        self.assertEqual(self.own_pending.status, "rejected")
        self.assertEqual(self.own_pending.approved_by_id, self.moderator.id)
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.content, "Published chapter text.")

    def test_approval_retains_existing_publication_and_pending_cleanup_rule(self):
        self.client.force_login(self.moderator)
        response = self.client.post(self.admin_list_url, {
            "action": "approve_selected", "_selected_action": [self.own_pending.id],
        })
        self.assertEqual(response.status_code, 302)
        self.own_pending.refresh_from_db()
        self.chapter.refresh_from_db()
        self.assertEqual(self.own_pending.status, "approved")
        self.assertEqual(self.own_pending.approved_by_id, self.moderator.id)
        self.assertEqual(self.chapter.content, "Published chapter text.\n\n" + self.own_pending.paragraph)
        self.assertFalse(ParagraphSubmission.objects.filter(id=self.other_pending.id).exists())
        self.assertTrue(ParagraphSubmission.objects.filter(id=self.other_rejected.id).exists())

    def test_direct_form_post_cannot_reassign_or_change_original_submission(self):
        self.client.force_login(self.superuser)
        self.client.post(reverse("admin:book_paragraphsubmission_change", args=[
            self.own_pending.id,
        ]), {
            "user": self.other_author.id, "chapter": self.second_chapter.id,
            "paragraph": "Changed text", "status": "approved", "_save": "Save",
        })
        self.own_pending.refresh_from_db()
        self.assertEqual(self.own_pending.user_id, self.author.id)
        self.assertEqual(self.own_pending.chapter_id, self.chapter.id)
        self.assertEqual(self.own_pending.paragraph, "Author's private pending paragraph.")
        self.assertEqual(self.own_pending.status, "pending")

    def test_submission_admin_does_not_offer_manual_creation(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:book_paragraphsubmission_add"))
        self.assertEqual(response.status_code, 403)
