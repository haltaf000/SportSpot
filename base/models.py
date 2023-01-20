from django.db import models
from django.contrib.auth.models import AbstractUser
import time
from django.db import models
import datetime # Create your models here.

class User(AbstractUser):
    name = models.CharField(max_length=200, null=True)
    email = models.EmailField(unique=True, null=True)
    bio = models.TextField(null=True, blank=True)
    cricket_praticipant = models.BooleanField(default=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
class Event(models.Model):
    name = models.CharField(max_length=200, null=True)
    preview = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    format = models.TextField(null=True, blank=True)
    players = models.TextField(null=True, blank=True)
    prizes = models.TextField(null=True, blank=True)
    participants = models.ManyToManyField(User, blank=True, related_name='events')
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    registration_deadline = models.DateTimeField(null=True)
    location = models.TextField(null=True, blank=True)
    draft_date = models.DateField(null=True)
    
    
    def __str__(self): 
        return self.name
    
    class Meta:
        ordering = ['start_date']
        
        
class Submission(models.Model):
    participant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='submissions')
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True)
    details = models.TextField(null=True, blank=True)
    def __str__(self):
        return str(self.event) + ' --- ' + str(self.participant)
    
    
class Team(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    players = models.ManyToManyField(User, related_name='teams')
    captain = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='captain_of')

    