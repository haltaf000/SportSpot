from django.shortcuts import render, redirect
from .models import User, Event, Submission, Team
from .forms import SubmissionForm, CustomUserCreateForm, UserForm, TeamForm, AdminDraftControlForm 
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
    users = User.objects.filter(cricket_participant=True)
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

def event_page(request, event_id):
    event = Event.objects.get(id=event_id)
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


@login_required(login_url='/login')
def live_draft(request, event_id):
    event = Event.objects.get(pk=event_id)
    today_local = timezone.now()
    if event.draft_start_date.date() != today_local.date() or event.draft_start_date > today_local:
        messages.error(request, 'The draft is not currently in progress.')
        return redirect('event', event_id=event_id)

    current_team = None
    is_captain = False
    available_players = User.objects.filter(cricket_participant=True)
    teams = Team.objects.filter(event=event)
    if request.user.is_authenticated:
        try:
            current_team = teams.get(captain=request.user)
            is_captain = True
        except Team.DoesNotExist:
            pass

    if request.user.is_staff:
        if request.method == 'POST':
            form = AdminDraftControlForm(request.POST)
            if form.is_valid():
                action = form.cleaned_data['action']
                if action == 'start_draft':
                    event.draft_start_date = timezone.now()
                    event.save()
                elif action == 'end_draft':
                    event.draft_end_date = timezone.now()
                    event.save()
                elif action == 'assign_captain':
                    captain_id = form.cleaned_data['captain']
                    captain = User.objects.get(id=captain_id)
                    team = teams.get(id=form.cleaned_data['team'])
                    team.captain = captain
                    team.save()
                return redirect('live_draft', event_id=event_id)
        else:
            form = AdminDraftControlForm(initial={'event': event})

    context = {
        'event': event,
        'teams': teams,
        'current_team': current_team,
        'is_captain': is_captain,
        'available_players': available_players,
        'form': form if request.user.is_staff else None,
    }
    return render(request, 'live_draft.html', context)



from django.contrib.auth.decorators import user_passes_test

def is_admin(user):
    return user.is_admin

@user_passes_test(is_admin, login_url='/login')
def start_draft(request, event_id):
    event = Event.objects.get(pk=str(event_id))
    event.draft_in_progress = True
    event.save()
    messages.success(request, 'Draft has been started.')
    return redirect('event', event_id=event_id)

@user_passes_test(is_admin, login_url='/login')
def manage_teams(request, event_id):
    event = Event.objects.get(id=event_id)
    teams = Team.objects.filter(event=event)
    if request.method == "POST":
        if request.POST.get("start_draft"):
            event.start_draft()
        elif request.POST.get("end_draft"):
            event.end_draft()
        elif request.POST.get("add_team"):
            team_name = request.POST.get("team_name")
            team = Team.objects.create(event=event, name=team_name)
        elif request.POST.get("delete_team"):
            team_id = request.POST.get("team_id")
            Team.objects.get(id=team_id).delete()
        return redirect("manage_teams", event_id)
    return render(request, "manage_teams.html", {"event": event, "teams": teams})