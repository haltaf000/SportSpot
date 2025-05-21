from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import Truncator
from django.urls import reverse

class User(AbstractUser):
    name = models.CharField(max_length=200, null=True)
    email = models.EmailField(unique=True, null=True)
    bio = models.TextField(null=True, blank=True)
    cricket_participant = models.BooleanField(default=True, null=True)
    is_staff = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    skill_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Player skill level from 1-5"
    )
    batting_style = models.CharField(max_length=50, null=True, blank=True)
    bowling_style = models.CharField(max_length=50, null=True, blank=True)
    matches_played = models.IntegerField(default=0)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.name or self.username

class Event(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    FORMAT_CHOICES = [
        ('league', 'League'),
        ('knockout', 'Knockout'),
        ('group', 'Group Stage + Knockout'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=200)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='league')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    prize_pool = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rules = models.TextField(blank=True)
    banner = models.ImageField(upload_to='event_banners/', blank=True, null=True)
    
    # Registration deadlines
    team_registration_deadline = models.DateTimeField(null=True, blank=True)
    player_registration_deadline = models.DateTimeField(null=True, blank=True)
    
    # Draft related fields
    draft_in_progress = models.BooleanField(default=False)
    draft_order = models.JSONField(null=True, blank=True)  # Store team order for draft
    current_draft_round = models.IntegerField(default=1)
    max_rounds = models.IntegerField(default=5)  # Maximum number of draft rounds
    max_team_size = models.IntegerField(default=11)  # Maximum players per team
    draft_start_time = models.DateTimeField(null=True, blank=True)
    
    organizer = models.ForeignKey('User', on_delete=models.CASCADE, related_name='organized_events')
    teams = models.ManyToManyField('Team', related_name='events', blank=True)
    participants = models.ManyToManyField('User', related_name='registered_events', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-update status based on dates
        today = timezone.now().date()
        if self.end_date < today:
            self.status = 'completed'
        elif self.start_date <= today <= self.end_date:
            self.status = 'in_progress'
        else:
            self.status = 'upcoming'
        super().save(*args, **kwargs)

    @property
    def preview(self):
        """Return a short preview of the description"""
        return Truncator(self.description).chars(150)

    @property
    def is_registration_open(self):
        """Check if event registration is still open"""
        return self.status == 'upcoming'

    def can_edit(self, user):
        """Check if user can edit this event"""
        return user == self.organizer or user.is_staff

    def get_absolute_url(self):
        """Get the absolute URL for this event"""
        return reverse('event', args=[self.id])

    def get_current_draft_team(self):
        """Get the team that currently has the draft pick"""
        if not self.draft_in_progress or not self.draft_order:
            return None
        teams_count = len(self.draft_order)
        if teams_count == 0:
            return None
        pick_number = (self.current_draft_round - 1) * teams_count
        # Reverse order for even rounds (snake draft)
        if self.current_draft_round % 2 == 0:
            pick_number = pick_number + (teams_count - 1 - (pick_number % teams_count))
        else:
            pick_number = pick_number % teams_count
        return Team.objects.get(id=self.draft_order[pick_number])

    def advance_draft(self):
        """Advance to the next draft pick"""
        if not self.draft_in_progress or not self.draft_order:
            return
        teams_count = len(self.draft_order)
        if teams_count == 0:
            return
        
        # Calculate total picks made
        total_picks = (self.current_draft_round - 1) * teams_count
        # If we've reached the end of the current round
        if total_picks >= teams_count * self.current_draft_round:
            if self.current_draft_round >= self.max_rounds:
                self.draft_in_progress = False
            else:
                self.current_draft_round += 1
        self.save()

class Team(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    players = models.ManyToManyField(User, related_name='teams')
    captain = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='captain_of')
    turn = models.IntegerField(default=0)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    logo = models.ImageField(upload_to='team_logos/', null=True, blank=True)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Match(models.Model):
    MATCH_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='matches')
    team1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    team2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    date = models.DateTimeField()
    venue = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=MATCH_STATUS_CHOICES, default='scheduled')
    team1_score = models.CharField(max_length=50, null=True, blank=True)
    team2_score = models.CharField(max_length=50, null=True, blank=True)
    winner = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches_won')
    match_summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.team1} vs {self.team2} - {self.date.strftime('%Y-%m-%d')}"

class Submission(models.Model):
    participant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='submissions')
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True)
    details = models.TextField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    
    def __str__(self):
        return f"{self.event} - {self.participant}"

class DraftControl(models.Model):
    draft_status = models.BooleanField(default=False)
    current_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    round_number = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Draft Control [status={self.draft_status}, round={self.round_number}]"

class PlayerStats(models.Model):
    player = models.OneToOneField(User, on_delete=models.CASCADE, related_name='stats')
    runs_scored = models.IntegerField(default=0)
    wickets_taken = models.IntegerField(default=0)
    matches_played = models.IntegerField(default=0)
    batting_average = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    bowling_average = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    highest_score = models.IntegerField(default=0)
    best_bowling = models.CharField(max_length=10, default='0/0')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Stats for {self.player.name}"