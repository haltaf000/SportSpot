from django.forms import ModelForm
from .models import Submission, User, Event, Team, Match, PlayerStats
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import DraftControl
from django.core.exceptions import ValidationError
from django.utils import timezone

class AdminDraftControlForm(forms.ModelForm):
    class Meta:
        model = DraftControl
        fields = ['draft_status']

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'description', 'logo']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('name'):
            raise forms.ValidationError("Team name is required.")
        return cleaned_data

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['details']
        widgets = {
            'details': forms.Textarea(attrs={'rows': 4}),
        }
        
        
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['name', 'username', 'email', 'bio', 'cricket_participant', 
                 'profile_picture', 'phone_number', 'skill_level', 
                 'batting_style', 'bowling_style']
        widgets = {
            'name':forms.TextInput(attrs={'class':'form-field--input'}),
            'email':forms.EmailInput(attrs={'class':'form-field--input'}),
            'bio':forms.Textarea(attrs={'rows': 4}),
            'skill_level': forms.NumberInput(attrs={'min': 1, 'max': 5}),
        }
             
class CustomUserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['name', 'username', 'email', 'password1', 'password2', 'bio', 
                 'cricket_participant', 'profile_picture', 'phone_number', 
                 'skill_level', 'batting_style', 'bowling_style']
        widgets = {
            'username': forms.TextInput(attrs={'class':'form-field--input'}),
            'name': forms.TextInput(attrs={'class':'form-field--input'}),
            'email':forms.EmailInput(attrs={'class':'form-field--input'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-field--input'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-field--input'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
            'skill_level': forms.NumberInput(attrs={'min': 1, 'max': 5}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already exists")
        return email

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'description', 'start_date', 'end_date', 'location', 
                 'format', 'prize_pool', 'entry_fee', 'rules', 'banner',
                 'team_registration_deadline', 'player_registration_deadline',
                 'draft_start_time', 'max_team_size', 'max_rounds']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'team_registration_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'player_registration_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'draft_start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'rules': forms.Textarea(attrs={'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        team_reg_deadline = cleaned_data.get('team_registration_deadline')
        player_reg_deadline = cleaned_data.get('player_registration_deadline')
        draft_start = cleaned_data.get('draft_start_time')

        if start_date and end_date and start_date > end_date:
            raise ValidationError('End date must be after start date.')
            
        if team_reg_deadline and draft_start and team_reg_deadline > draft_start:
            raise ValidationError('Team registration deadline must be before draft start time.')
            
        if player_reg_deadline and draft_start and player_reg_deadline > draft_start:
            raise ValidationError('Player registration deadline must be before draft start time.')
            
        if draft_start and start_date and draft_start.date() > start_date:
            raise ValidationError('Draft must be completed before event start date.')
        
        return cleaned_data

class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['team1', 'team2', 'date', 'venue', 'status']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        team1 = cleaned_data.get('team1')
        team2 = cleaned_data.get('team2')
        
        if team1 and team2 and team1 == team2:
            raise ValidationError("Teams must be different")
        
        return cleaned_data

class PlayerStatsForm(forms.ModelForm):
    class Meta:
        model = PlayerStats
        fields = ['runs_scored', 'wickets_taken', 'matches_played', 
                 'batting_average', 'bowling_average', 'highest_score', 
                 'best_bowling']
        
    def clean(self):
        cleaned_data = super().clean()
        matches = cleaned_data.get('matches_played')
        runs = cleaned_data.get('runs_scored')
        
        if matches and runs:
            if matches < 0:
                raise ValidationError("Matches played cannot be negative")
            if runs < 0:
                raise ValidationError("Runs scored cannot be negative")
        
        return cleaned_data

class PlayerRegistrationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['skill_level', 'batting_style', 'bowling_style']
        widgets = {
            'skill_level': forms.NumberInput(attrs={
                'min': 1, 
                'max': 5,
                'class': 'form-field--input'
            }),
            'batting_style': forms.TextInput(attrs={'class': 'form-field--input'}),
            'bowling_style': forms.TextInput(attrs={'class': 'form-field--input'}),
        }

    def clean_skill_level(self):
        skill_level = self.cleaned_data.get('skill_level')
        if skill_level and (skill_level < 1 or skill_level > 5):
            raise ValidationError("Skill level must be between 1 and 5")
        return skill_level