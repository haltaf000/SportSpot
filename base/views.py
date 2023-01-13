from django.shortcuts import render, redirect
from .models import User, Event, Submission
from .forms import SubmissionForm, CustomUserCreateForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.http import HttpResponse
# Create your views here.

def about_page(request):
    return render(request, "about.html", {})

def rule_page(request):
    return render(request, "rules.html", {})

def login_page(request):
    page = 'login'
    
    if request.method == 'POST':
        user = authenticate(email=request.POST['email'], password=request.POST['password'])
        if user is not None:
            login(request, user)
            messages.info(request, 'You have successfully logged in.')
            return redirect('home')
        else:
            messages.error(request, 'Email or Password is incorrect')
            return redirect('login')
    
    context = {'page':page}
    return render(request, 'login_register.html', context)

def register_page(request):
    form = CustomUserCreateForm()
    if request.method == 'POST':
        form = CustomUserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            user.save()
            login(request, user)
            messages.success(request, 'User account was created!')
            return redirect('home')
        else:
            messages.error(request, 'An error has occurred during registration')
    
    
    page = 'register'
    context = {'page':page, 'form':form}
    return render(request, 'login_register.html', context)

def logout_user(request):
    logout(request)
    messages.info(request, 'User was logged out!')
    return redirect('home')

def home(request):
    users = User.objects.filter(cricket_praticipant=True)
    events = Event.objects.all()
    context = {'users':users, 'events': events}
    return render(request, 'home.html', context)

def user_page(request, pk):
    user = User.objects.get(id=pk)
    context = {'user':user}
    return render(request, 'profile.html', context)

@login_required(login_url='/login')
def account_page(request):
    user = request.user
    context = {'user':user}
    return render(request, 'account.html', context)

def event_page(request, pk):
    event = Event.objects.get(id=pk)
    
    registered = False
    submitted = False
    
    if request.user.is_authenticated:
        
        registered = request.user.events.filter(id=event.id).exists()
        submitted = Submission.objects.filter(participant=request.user, event=event).exists()
    
    context = {'event':event, 'registered':registered, 'submitted':submitted}
    return render(request, 'event.html', context)

@login_required(login_url='/login')
def registration_conformation(request, pk):
    event = Event.objects.get(id=pk)
    context = {'event':event}
    
    if request.method == 'POST':
        event.participants.add(request.user)
        return redirect('event', pk=event.id)
    
    
    return render(request, 'confirmation.html', context)

@login_required(login_url='/login')
def project_submission(request, pk):
    event = Event.objects.get(id=pk)
    
    form = SubmissionForm()
    if request.method == 'POST':
        form = SubmissionForm(request.POST)
        
        if form.is_valid():
            submission = form.save(commit=False)
            submission.participant = request.user
            submission.event = event 
            submission.save()
            return redirect('account')
    context = {'event':event, 'form':form}
    return render(request, 'submit_form.html', context)
    
@login_required(login_url='/login')
def update_submission(request, pk):
    submission = Submission.objects.get(id=pk)
    
    if request.user != submission.participant:
        return HttpResponse('You Cannot be HERE!')
    
    
    event = submission.event
    form = SubmissionForm(instance=submission)
    
    if request.method == 'POST':
        form = SubmissionForm(request.POST, instance=submission)
        
        if form.is_valid():
            form.save()
            return redirect('account')
    
    
    context = {'form':form, 'event':event}
    return render(request, 'submit_form.html', context)
    