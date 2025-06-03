from django.db import models
from django.utils import timezone
# Create your models here.


class GHLAuthCredentials(models.Model):
    user_id = models.CharField(max_length=255, unique=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.IntegerField()
    scope = models.TextField(null=True, blank=True)
    user_type = models.CharField(max_length=50, null=True, blank=True)
    company_id = models.CharField(max_length=255, null=True, blank=True)
    location_id = models.CharField(max_length=255, null=True, blank=True)

class RCToken(models.Model):
    owner_id = models.CharField(max_length=20)
    access_token = models.TextField()
    token_type = models.CharField(max_length=100)
    expires_in = models.IntegerField()
    refresh_token = models.TextField()
    refresh_token_expires_in = models.IntegerField()
    scope = models.TextField(null=True, blank=True)
    ghl_location_id = models.CharField(max_length=255, null=True, blank=True)
    rc_phone_no = models.CharField(max_length=20)
    jwt_code = models.TextField()
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)

class GHLContactCache(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)
    contact_id = models.CharField(max_length=100, null=True, blank=True)
    conversation_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CeleryIntegrationToggle(models.Model):
    enabled = models.BooleanField(default=True)