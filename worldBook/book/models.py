from django.db import models


from user.models import User

# Create your models here.


class Book(models.Model):
    id = models.AutoField(
        primary_key=True
    )  # Equivalent to INT AUTO_INCREMENT PRIMARY KEY
    title = models.CharField(max_length=255)  # Equivalent to VARCHAR(255) NOT NULL
    number_of_chapters = models.PositiveIntegerField(
        default=0
    )  # Field for number of chapters, default is 0

    def __str__(self):
        return self.title


class Chapter(models.Model):
    id = models.AutoField(
        primary_key=True
    )  # Equivalent to INT AUTO_INCREMENT PRIMARY KEY
    book = models.ForeignKey(
        "Book",  # Reference the Book model
        on_delete=models.CASCADE,
        related_name="chapters",  # Allows reverse access: book.chapters.all()
    )  # Equivalent to book_id INT NOT NULL with a foreign key constraint
    title = models.CharField(max_length=255)  # Equivalent to VARCHAR(255) NOT NULL
    content = models.TextField(blank=True, null=True)  # Equivalent to TEXT, optional
    chapter_number = models.PositiveIntegerField()  # Stores chapter order

    def __str__(self):
        return f"Chapter {self.chapter_number}: {self.title}"


# class Word(models.Model):
#     word_id = models.AutoField(primary_key=True)
#     chapter = models.ForeignKey(
#         "Chapter",
#         on_delete=models.CASCADE,
#         related_name="words",
#     )
#     user = models.ForeignKey(  # Rename this to 'user'
#         User,
#         on_delete=models.CASCADE,
#         related_name="words",
#     )
#     word = models.CharField(max_length=255)

#     def __str__(self):
#         return self.word


class ParagraphSubmission(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    id = models.AutoField(primary_key=True)
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name="submissions"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    paragraph = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_paragraphs",
    )

    def __str__(self):
        return f"{self.user.username} - {self.chapter.title} ({self.status})"
