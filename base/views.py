from django.shortcuts import render, redirect
from .models import User, Event, Submission, Team
from .forms import SubmissionForm, CustomUserCreateForm, UserForm, TeamForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone


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
    count = users.count()
    users = users[0:20]
    events = Event.objects.all()
    context = {'users':users, 'events': events, 'count':count}
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

@login_required(login_url='/login')
def edit_account(request):
    form = UserForm(instance=request.user)
    
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('account')
    user = request.user
    context = {'user':user, 'form':form}
    return render(request, 'user_form.html', context)

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
    



def team_list(request):
    teams = Team.objects.all()
    context = {'teams': teams}
    return render(request, 'team_list.html', context)

def team_detail(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    context = {'team': team}
    return render(request, 'team_detail.html', context)


from datetime import  datetime


@login_required
def live_draft(request, event_id):
    event = Event.objects.get(pk=event_id)
    today = timezone.now().date()
    if event.draft_date != today:
        return render(request, 'draft_date.html', {'event': event, 'today':today})
    else:
        available_players = User.objects.filter(cricket_praticipant=True).exclude(id__in=event.teams.values_list('players'))
        teams = Team.objects.filter(event=event)
        if request.method == 'POST':
            if 'create_team' in request.POST:
                form = TeamForm(request.POST)
                if form.is_valid():
                    team = form.save(commit=False)
                    team.event = event
                    team.save()
                    messages.success(request, 'Team was created!')
                    return redirect('team_detail', team_id=team.id)
                else:
                    messages.error(request, 'An error has occurred during team creation')
            elif 'edit_team' in request.POST:
                team_id = request.POST['edit_team']
                team = get_object_or_404(Team, id=team_id)
                form = TeamForm(request.POST, instance=team)
                if form.is_valid():
                    form.save()
                    messages.success(request, 'Team was updated!')
                    return redirect('team_detail', team_id=team_id)
                else:
                    messages.error(request, 'An error has occurred during team update')
            elif 'delete_team' in request.POST:
                team_id = request.POST['delete_team']
                team = get_object_or_404(Team, id=team_id)
                team.delete()
                messages.success(request, 'Team was deleted!')
                return redirect('team_list')
            elif 'player' in request.POST and 'team' in request.POST:
                player = User.objects.get(pk=request.POST['player'])
                team = Team.objects.get(pk=request.POST['team'])
                if request.user == team.captain:
                    team.players.add(player)
                    team.save()
                    available_players = available_players.exclude(pk=player.pk)
                else:
                    messages.error(request, 'You are not the captain of the selected team')

        context = {'available_players': available_players, 'teams': teams, 'today':today}
        return render(request, 'live_draft.html', context)
