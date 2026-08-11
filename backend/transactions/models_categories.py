from django.db import models

class BillerCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, help_text="Icon identifier for the UI")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
