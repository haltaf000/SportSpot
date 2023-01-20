from django.forms import ModelForm
from .models import Submission, User, Event, Team
from django import forms
from django.contrib.auth.forms import UserCreationForm

class TeamForm(forms.ModelForm):
    event = forms.ModelChoiceField(queryset=Event.objects.all())
    class Meta:
        model = Team
        fields = ['name', 'description', 'players','event']
        widgets = {
            'players': forms.CheckboxSelectMultiple()
        }

    def clean(self):
        cleaned_data = super().clean()
        players = cleaned_data.get("players")
        event = cleaned_data.get("event")

        for player in players:
            if not event.participants.filter(id=player.id).exists():
                raise forms.ValidationError("Selected player is not signed up for the event.")


class SubmissionForm(ModelForm):
    class Meta:
        model = Submission
        fields = ['details']
        
        
class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['name', 'email', 'bio']   
        
        widgets = {
            'name':forms.TextInput(attrs={'class':'form-field--input'}),
            'email':forms.EmailInput(attrs={'class':'form-field--input'}),
            'bio':forms.Textarea(attrs={'class':'form-field--input-txarea'})
        }
             
class CustomUserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'name']
        widgets = {
            'username': forms.TextInput(attrs={'class':'form-field--input'}),
            'name': forms.TextInput(attrs={'class':'form-field--input'}),
            'email':forms.EmailInput(attrs={'class':'form-field--input'})
        }