"""
Internal system models - source of truth for customer data.
"""
from django.db import models
import uuid


class Customer(models.Model):
    """
    Customer model representing the source of truth.
    
    Changes to this model automatically emit versioned events to Kafka
    via post_save signals.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    status = models.CharField(max_length=50, default="active")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.email})"

    class Meta:
        ordering = ["-created_at"]
