from django.forms import ModelForm
from .models import Submission, User, Event
from django import forms
from django.contrib.auth.forms import UserCreationForm

class SubmissionForm(ModelForm):
    class Meta:
        model = Submission
        fields = ['details']
        
        
        
class CustomUserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'name']
        widgets = {
            'username': forms.TextInput(attrs={'class':'form-field--input'}),
            'name': forms.TextInput(attrs={'class':'form-field--input'}),
            'email':forms.EmailInput(attrs={'class':'form-field--input'})
        }