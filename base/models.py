from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import Truncator
from django.urls import reverse
from django.core.cache import cache
from django.db.models import Count, F
from django.conf import settings

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        return self.create_user(email, username, password, **extra_fields)

class User(AbstractUser):
    BATTING_STYLES = [
        ('right', 'Right Handed'),
        ('left', 'Left Handed'),
    ]
    
    BOWLING_STYLES = [
        ('fast', 'Fast'),
        ('medium', 'Medium'),
        ('spin', 'Spin'),
    ]
    
    name = models.CharField(max_length=200, null=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=150, unique=True, db_index=True)
    bio = models.TextField(null=True, blank=True)
    cricket_participant = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pics/%Y/%m/', null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    skill_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Player skill level from 1-5",
        db_index=True
    )
    batting_style = models.CharField(max_length=50, null=True, blank=True, choices=BATTING_STYLES)
    bowling_style = models.CharField(max_length=50, null=True, blank=True, choices=BOWLING_STYLES)
    matches_played = models.PositiveIntegerField(default=0, db_index=True)
    
    # Authentication fields with indexes
    email_verified = models.BooleanField(default=False, db_index=True)
    email_verification_token = models.CharField(max_length=100, null=True, blank=True, unique=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    date_joined = models.DateTimeField(default=timezone.now, db_index=True)
    last_login = models.DateTimeField(null=True, blank=True, db_index=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['name', 'email']),
            models.Index(fields=['date_joined', 'is_active']),
            models.Index(fields=['skill_level', 'cricket_participant']),
        ]

    def __str__(self):
        return self.name or self.username

    def get_full_name(self):
        return self.name or self.username

    def get_short_name(self):
        return self.username

    def get_stats(self):
        """Get cached player stats"""
        cache_key = f'player_stats_{self.id}'
        stats = cache.get(cache_key)
        if stats is None:
            stats = PlayerStats.objects.get_or_create(player=self)[0]
            cache.set(cache_key, stats, 3600)  # Cache for 1 hour
        return stats

class Event(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    FORMAT_CHOICES = [
        ('league', 'League'),
        ('knockout', 'Knockout'),
        ('group', 'Group Stage + Knockout'),
    ]

    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    location = models.CharField(max_length=200)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='league', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming', db_index=True)
    prize_pool = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rules = models.TextField(blank=True)
    banner = models.ImageField(upload_to='event_banners/%Y/%m/', blank=True, null=True)
    
    # Registration deadlines
    team_registration_deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    player_registration_deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Draft related fields
    draft_in_progress = models.BooleanField(default=False, db_index=True)
    draft_order = models.JSONField(null=True, blank=True)
    current_draft_round = models.PositiveIntegerField(default=1)
    max_rounds = models.PositiveIntegerField(default=5)
    max_team_size = models.PositiveIntegerField(default=11)
    draft_start_time = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Relationships with indexes
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_events', db_index=True)
    teams = models.ManyToManyField('Team', related_name='events', blank=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='registered_events', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['draft_in_progress', 'draft_start_time']),
            models.Index(fields=['created_at', 'status']),
            models.Index(fields=['organizer', 'status']),
        ]

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
            
        # Clear cache on save
        cache.delete(f'event_team_count_{self.id}')
        cache.delete(f'event_participant_count_{self.id}')
        super().save(*args, **kwargs)

    def get_team_count(self):
        """Get cached team count"""
        cache_key = f'event_team_count_{self.id}'
        count = cache.get(cache_key)
        if count is None:
            count = self.teams.count()
            cache.set(cache_key, count, 3600)  # Cache for 1 hour
        return count

    def get_participant_count(self):
        """Get cached participant count"""
        cache_key = f'event_participant_count_{self.id}'
        count = cache.get(cache_key)
        if count is None:
            count = self.participants.count()
            cache.set(cache_key, count, 3600)  # Cache for 1 hour
        return count

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
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True, null=True)
    players = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='teams')
    captain = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='captain_of', db_index=True)
    turn = models.PositiveIntegerField(default=0)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, db_index=True)
    logo = models.ImageField(upload_to='team_logos/%Y/%m/', null=True, blank=True)
    wins = models.PositiveIntegerField(default=0, db_index=True)
    losses = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['name', 'event']),
            models.Index(fields=['captain', 'created_at']),
            models.Index(fields=['wins', 'losses', 'draws']),
        ]

    def __str__(self):
        return self.name

    def get_player_count(self):
        """Get cached player count"""
        cache_key = f'team_player_count_{self.id}'
        count = cache.get(cache_key)
        if count is None:
            count = self.players.count()
            cache.set(cache_key, count, 3600)  # Cache for 1 hour
        return count

    def get_win_percentage(self):
        """Calculate win percentage"""
        total_matches = self.wins + self.losses + self.draws
        if total_matches == 0:
            return 0
        return (self.wins + (self.draws * 0.5)) / total_matches * 100

class Match(models.Model):
    MATCH_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='matches', db_index=True)
    team1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches', db_index=True)
    team2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches', db_index=True)
    date = models.DateTimeField(db_index=True)
    venue = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=MATCH_STATUS_CHOICES, default='scheduled', db_index=True)
    team1_score = models.CharField(max_length=50, null=True, blank=True)
    team2_score = models.CharField(max_length=50, null=True, blank=True)
    winner = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches_won', db_index=True)
    match_summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['event', 'status']),
            models.Index(fields=['team1', 'team2', 'date']),
        ]
        ordering = ['date']

    def __str__(self):
        return f"{self.team1} vs {self.team2} - {self.date.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        # Update team statistics when match is completed
        if self.status == 'completed' and self.winner:
            if self.winner == self.team1:
                self.team1.wins = F('wins') + 1
                self.team2.losses = F('losses') + 1
            elif self.winner == self.team2:
                self.team2.wins = F('wins') + 1
                self.team1.losses = F('losses') + 1
            else:
                self.team1.draws = F('draws') + 1
                self.team2.draws = F('draws') + 1
            
            self.team1.save()
            self.team2.save()
        
        super().save(*args, **kwargs)

class Submission(models.Model):
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='submissions')
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
    player = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stats')
    runs_scored = models.PositiveIntegerField(default=0, db_index=True)
    wickets_taken = models.PositiveIntegerField(default=0, db_index=True)
    matches_played = models.PositiveIntegerField(default=0, db_index=True)
    batting_average = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    bowling_average = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    highest_score = models.PositiveIntegerField(default=0)
    best_bowling = models.CharField(max_length=10, default='0/0')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['runs_scored', 'wickets_taken']),
            models.Index(fields=['batting_average', 'bowling_average']),
            models.Index(fields=['matches_played', 'highest_score']),
        ]
    
    def __str__(self):
        return f"Stats for {self.player.name}"

    def update_batting_average(self):
        """Update batting average"""
        if self.matches_played > 0:
            self.batting_average = self.runs_scored / self.matches_played
            self.save(update_fields=['batting_average'])

    def update_bowling_average(self):
        """Update bowling average"""
        if self.matches_played > 0:
            self.bowling_average = self.wickets_taken / self.matches_played
            self.save(update_fields=['bowling_average'])