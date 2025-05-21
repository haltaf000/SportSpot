from django.shortcuts import render, redirect, get_object_or_404
from .models import User, Event, Submission, Team, Match, PlayerStats, DraftControl
from .forms import SubmissionForm, UserForm, TeamForm, AdminDraftControlForm, EventForm, MatchForm, PlayerStatsForm, PlayerRegistrationForm, CustomAuthenticationForm, CustomUserCreationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q, Prefetch, Count, F
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from datetime import datetime, timedelta
from random import shuffle
import uuid
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from functools import wraps



# Create your views here.


# Cache timeouts
CACHE_TTL = 60 * 15  # 15 minutes
CACHE_TTL_LONG = 60 * 60  # 1 hour
CACHE_TTL_SHORT = 60 * 5  # 5 minutes

def cache_per_user(timeout=CACHE_TTL):
    """
    Cache decorator that includes the user's ID in the cache key.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            cache_key = f'view_cache_{request.user.id}_{request.path}'
            response = cache.get(cache_key)
            
            if response is None:
                response = view_func(request, *args, **kwargs)
                cache.set(cache_key, response, timeout)
            
            return response
        return _wrapped_view
    return decorator

@cache_page(CACHE_TTL)
def about_page(request):
    return render(request, "about.html", {})

@cache_page(CACHE_TTL)
def rule_page(request):
    return render(request, "rules.html", {})

@require_http_methods(["GET", "POST"])
def login_page(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me', False)
            
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if not user.email_verified:
                    messages.error(request, 'Please verify your email address before logging in.')
                    return redirect('login')
                    
                login(request, user)
                
                if remember_me:
                    request.session.set_expiry(30 * 24 * 60 * 60)
                else:
                    request.session.set_expiry(0)
                
                messages.success(request, f'Welcome back, {user.name or user.username}!')
                return redirect('home')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'authentication/login.html', {'form': form})

def register_page(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.email_verification_token = str(uuid.uuid4())
            user.email_verification_sent_at = timezone.now()
            user.save()
            
            # Create player stats
            PlayerStats.objects.create(player=user)
            
            # Send verification email
            verification_url = request.build_absolute_uri(
                reverse('verify-email', args=[user.email_verification_token])
            )
            
            try:
                context = {
                    'user': user,
                    'verification_url': verification_url
                }
                html_message = render_to_string('email/verify_email.html', context)
                plain_message = strip_tags(html_message)
                
                send_mail(
                    'Verify your SportSpot account',
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                messages.success(request, 'Account created successfully! Please check your email to verify your account.')
            except Exception as e:
                messages.warning(request, 'Account created but unable to send verification email. Please contact support.')
            
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'authentication/register.html', {'form': form})

def verify_email(request, token):
    try:
        user = User.objects.get(email_verification_token=token)
        if user.email_verification_sent_at < timezone.now() - timezone.timedelta(days=7):
            messages.error(request, 'Verification link has expired. Please request a new one.')
        else:
            user.email_verified = True
            user.email_verification_token = None
            user.save()
            messages.success(request, 'Email verified successfully! You can now log in.')
    except User.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
    
    return redirect('login')

def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('home')

def home(request):
    search_query = request.GET.get('q', '')
    page = request.GET.get('page', 1)
    
    # Try to get cached data
    cache_key = f'home_data_{search_query}_{page}'
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        # Query optimization with select_related and prefetch_related
        upcoming_events = Event.objects.select_related('organizer').prefetch_related(
            'teams',
            Prefetch('matches', queryset=Match.objects.select_related('team1', 'team2'))
        ).filter(
            start_date__gt=timezone.now()
        ).order_by('start_date')[:5]
        
        ongoing_events = Event.objects.select_related('organizer').prefetch_related(
            'teams'
        ).filter(
            start_date__lte=timezone.now(),
            end_date__gt=timezone.now()
        )
        
        recent_matches = Match.objects.select_related(
            'team1', 'team2', 'winner'
        ).filter(
            status='completed'
        ).order_by('-date')[:5]
        
        if search_query:
            users = User.objects.filter(
                Q(name__icontains=search_query) |
                Q(username__icontains=search_query)
            ).select_related('stats')
            
            events = Event.objects.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            ).select_related('organizer')
        else:
            users = User.objects.filter(
                cricket_participant=True
            ).select_related('stats')[:8]
            events = upcoming_events
        
        # Paginate results
        paginator = Paginator(events, 10)
        events_page = paginator.get_page(page)
        
        context = {
            'users': users,
            'events': events_page,
            'upcoming_events': upcoming_events,
            'ongoing_events': ongoing_events,
            'recent_matches': recent_matches,
            'search_query': search_query
        }
        
        # Cache the data
        cache.set(cache_key, context, CACHE_TTL)
    else:
        context = cached_data
    
    return render(request, 'home.html', context)

def user_page(request, pk):
    cache_key = f'user_page_{pk}'
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        user = get_object_or_404(
            User.objects.select_related('stats'),
            id=pk
        )
        
        stats = PlayerStats.objects.get_or_create(player=user)[0]
        
        participated_events = Event.objects.filter(
            participants=user
        ).select_related('organizer')
        
        upcoming_matches = Match.objects.filter(
            Q(team1__captain=user) | Q(team2__captain=user),
            status='scheduled'
        ).select_related('team1', 'team2')
        
        recent_matches = Match.objects.filter(
            Q(team1__players=user) | Q(team2__players=user),
            status='completed'
        ).select_related(
            'team1', 'team2', 'winner'
        ).order_by('-date')[:5]
        
        context = {
            'profile_user': user,
            'stats': stats,
            'participated_events': participated_events,
            'upcoming_matches': upcoming_matches,
            'recent_matches': recent_matches
        }
        
        cache.set(cache_key, context, CACHE_TTL)
    else:
        context = cached_data
    
    return render(request, 'profile.html', context)

@login_required(login_url='/login')
def account_page(request):
    user = request.user
    stats = PlayerStats.objects.get_or_create(player=user)[0]
    
    # Get events where user is a player in any team
    registered_events = Event.objects.filter(
        teams__players=user
    ).distinct()
    
    # Get teams the user is part of
    teams = Team.objects.filter(players=user)
    
    # Get events where user is the organizer
    organized_events = Event.objects.filter(organizer=user)
    
    context = {
        'user': user,
        'stats': stats,
        'registered_events': registered_events,
        'organized_events': organized_events,
        'teams': teams
    }
    return render(request, 'account.html', context)

@login_required(login_url='/login')
def edit_account(request):
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=request.user)
        stats_form = PlayerStatsForm(request.POST, instance=request.user.stats)
        if form.is_valid() and stats_form.is_valid():
            form.save()
            stats_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('account')
    else:
        form = UserForm(instance=request.user)
        stats_form = PlayerStatsForm(instance=request.user.stats)
    
    context = {
        'form': form,
        'stats_form': stats_form
    }
    return render(request, 'user_form.html', context)

def event(request, pk):
    event = get_object_or_404(Event, id=pk)
    teams = event.teams.all()
    current_time = timezone.now()
    
    user_team = None
    user_in_event = False
    can_register_team = False
    can_register_player = False
    
    if request.user.is_authenticated:
        # Check if user has a team in this event
        user_team = teams.filter(captain=request.user).first()
        
        # Check if user is already in any team in this event
        user_in_event = teams.filter(players=request.user).exists()
        
        # If not in a team, check if user is registered for the draft
        if not user_in_event:
            user_in_event = event.participants.filter(id=request.user.id).exists()
        
        # Check if team registration is still open
        can_register_team = (not event.team_registration_deadline or 
                           current_time <= event.team_registration_deadline)
        
        # Check if player registration is still open
        can_register_player = (not event.player_registration_deadline or 
                             current_time <= event.player_registration_deadline)
    
    context = {
        'event': event,
        'teams': teams,
        'user_team': user_team,
        'user_in_event': user_in_event,
        'can_register_team': can_register_team,
        'can_register_player': can_register_player,
        'current_time': current_time,
    }
    return render(request, 'event.html', context)

@login_required
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, 'Event created successfully!')
            return redirect('event', pk=event.id)
    else:
        form = EventForm()
    
    return render(request, 'event_form.html', {'form': form})

@login_required
def edit_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    if not event.can_edit(request.user):
        messages.error(request, 'You do not have permission to edit this event.')
        return redirect('event', pk=event.id)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('event', pk=event.id)
    else:
        form = EventForm(instance=event)
    
    return render(request, 'event_form.html', {'form': form, 'event': event})

@cache_per_user(CACHE_TTL_SHORT)
def event_detail(request, pk):
    # Get event with all related data in a single query
    event = get_object_or_404(
        Event.objects.select_related('organizer').prefetch_related(
            'teams',
            'teams__captain',
            'teams__players',
            Prefetch(
                'matches',
                queryset=Match.objects.select_related('team1', 'team2', 'winner').order_by('date')
            )
        ),
        id=pk
    )
    
    registered = False
    submitted = False
    is_admin = False
    
    if request.user.is_authenticated:
        # Use cached results for user permissions
        cache_key = f'user_event_perms_{request.user.id}_{event.id}'
        cached_perms = cache.get(cache_key)
        
        if cached_perms is None:
            registered = request.user.teams.filter(event=event).exists()
            submitted = Submission.objects.filter(
                participant=request.user,
                event=event
            ).exists()
            is_admin = request.user.is_staff or request.user == event.organizer
            
            cached_perms = {
                'registered': registered,
                'submitted': submitted,
                'is_admin': is_admin
            }
            cache.set(cache_key, cached_perms, CACHE_TTL)
        else:
            registered = cached_perms['registered']
            submitted = cached_perms['submitted']
            is_admin = cached_perms['is_admin']
    
    context = {
        'event': event,
        'registered': registered,
        'submitted': submitted,
        'is_admin': is_admin,
        'teams': event.teams.all(),
        'matches': event.matches.all(),
        'submissions': Submission.objects.filter(
            event=event,
            status='approved'
        ),
        'can_edit': event.can_edit(request.user),
        'is_registered': request.user.is_authenticated and registered,
    }
    return render(request, 'event.html', context)

@login_required(login_url='/login')
def registration_confirmation(request, pk):
    event = get_object_or_404(Event, id=pk)
    
    if timezone.now() > event.registration_deadline:
        messages.error(request, 'Registration deadline has passed.')
        return redirect('event', pk=event.id)
    
    if event.participants.count() >= event.max_participants:
        messages.error(request, 'Event has reached maximum participants.')
        return redirect('event', pk=event.id)
    
    if request.method == 'POST':
        event.participants.add(request.user)
        messages.success(request, 'Successfully registered for the event!')
        return redirect('event', pk=event.id)
    
    context = {'event': event}
    return render(request, 'confirmation.html', context)

@login_required(login_url='/login')
def create_team(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        print(f"POST request received for team creation in event {event_id}")
        print(f"POST data: {request.POST}")
        print(f"FILES: {request.FILES}")
        
        form = TeamForm(request.POST, request.FILES)
        if form.is_valid():
            print("Form is valid")
            team = form.save(commit=False)
            team.event = event
            team.captain = request.user
            team.save()
            team.players.add(request.user)
            
            # Add the team to the event's teams
            event.teams.add(team)
            event.save()
            
            messages.success(request, 'Team created successfully!')
            return redirect('team-detail', pk=team.id)
        else:
            print(f"Form errors: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        print(f"GET request received for team creation in event {event_id}")
        form = TeamForm()
    
    context = {'form': form, 'event': event}
    return render(request, 'team_form.html', context)

@cache_per_user(CACHE_TTL_SHORT)
def team_list(request):
    search_query = request.GET.get('q', '')
    teams = Team.objects.select_related('event', 'captain').prefetch_related('players')
    
    if search_query:
        teams = teams.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by event if specified
    event_id = request.GET.get('event')
    if event_id:
        teams = teams.filter(event_id=event_id)
    
    # Get all events for filtering - cache this query
    cache_key = 'all_events'
    events = cache.get(cache_key)
    if events is None:
        events = Event.objects.all()
        cache.set(cache_key, events, CACHE_TTL)
    
    # Get available events for team creation
    cache_key = 'available_events'
    available_events = cache.get(cache_key)
    if available_events is None:
        available_events = Event.objects.filter(
            team_registration_deadline__gt=timezone.now()
        ).order_by('team_registration_deadline')
        cache.set(cache_key, available_events, CACHE_TTL_SHORT)
    
    context = {
        'teams': teams,
        'events': events,
        'available_events': available_events,
        'search_query': search_query,
        'selected_event': event_id
    }
    return render(request, 'team_list.html', context)

def team_detail(request, pk):
    team = get_object_or_404(Team, id=pk)
    matches = Match.objects.filter(
        Q(team1=team) | Q(team2=team)
    ).order_by('date')
    
    context = {
        'team': team,
        'matches': matches,
        'is_captain': request.user == team.captain
    }
    return render(request, 'team_detail.html', context)

@login_required
def create_match(request, pk):
    event = get_object_or_404(Event, id=pk)
    if request.user != event.organizer and not request.user.is_staff:
        messages.error(request, 'You do not have permission to create matches.')
        return redirect('event', pk=event.id)
    
    if request.method == 'POST':
        form = MatchForm(request.POST)
        if form.is_valid():
            match = form.save(commit=False)
            match.event = event
            match.save()
            messages.success(request, 'Match created successfully!')
            return redirect('event', pk=event.id)
    else:
        form = MatchForm()
    
    context = {'form': form, 'event': event}
    return render(request, 'match_form.html', context)

@login_required(login_url='/login')
def update_match(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    if request.user != match.event.admin and not request.user.is_staff:
        messages.error(request, 'You do not have permission to update this match.')
        return redirect('event', event_id=match.event.id)
    
    if request.method == 'POST':
        form = MatchForm(request.POST, instance=match)
        if form.is_valid():
            form.save()
            messages.success(request, 'Match updated successfully!')
            return redirect('event', event_id=match.event.id)
    else:
        form = MatchForm(instance=match)
    
    context = {'form': form, 'match': match}
    return render(request, 'match_form.html', context)

@login_required
def start_draft(request, pk):
    event = get_object_or_404(Event, id=pk)
    
    if request.user != event.organizer and not request.user.is_staff:
        messages.error(request, 'You do not have permission to start the draft.')
        return redirect('event', pk=event.id)
    
    if event.draft_in_progress:
        messages.error(request, 'Draft is already in progress.')
        return redirect('live-draft', pk=event.id)
    
    # Initialize draft order with team IDs in random order
    teams = list(event.teams.all().values_list('id', flat=True))
    if not teams:
        messages.error(request, 'No teams available for draft.')
        return redirect('event', pk=event.id)
    
    shuffle(teams)
    event.draft_order = teams
    event.draft_in_progress = True
    event.current_draft_round = 1
    event.draft_start_time = timezone.now()
    event.save()
    
    messages.success(request, 'Draft has started!')
    return redirect('live-draft', pk=event.id)

@login_required
def stop_draft(request, pk):
    event = get_object_or_404(Event, id=pk)
    
    if request.user != event.organizer and not request.user.is_staff:
        messages.error(request, 'You do not have permission to stop the draft.')
        return redirect('event', pk=event.id)
    
    if not event.draft_in_progress:
        messages.error(request, 'No draft is currently in progress.')
        return redirect('event', pk=event.id)
    
    event.draft_in_progress = False
    event.draft_order = None
    event.save()
    
    messages.success(request, 'Draft has been stopped.')
    return redirect('event', pk=event.id)

@login_required
def live_draft(request, pk):
    event = get_object_or_404(Event, id=pk)
    
    if not event.draft_in_progress:
        messages.error(request, 'The draft is not currently in progress.')
        return redirect('event', pk=event.id)

    teams = Team.objects.filter(event=event).prefetch_related('players', 'captain')
    current_team = event.get_current_draft_team()
    is_captain = request.user == current_team.captain if current_team else False
    
    # Get available players (only those who have registered for this event and not already in a team)
    available_players = User.objects.filter(
        cricket_participant=True,
        skill_level__isnull=False,  # Must have set their skill level (completed registration)
        batting_style__isnull=False,  # Must have set their batting style
        bowling_style__isnull=False  # Must have set their bowling style
    ).exclude(
        teams__event=event  # Not already in a team for this event
    ).filter(
        # Only include players who registered before the deadline
        id__in=User.objects.filter(
            cricket_participant=True,
            skill_level__isnull=False,
            batting_style__isnull=False,
            bowling_style__isnull=False,
            # Add any other registration criteria here
        ).values('id')
    ).order_by('-skill_level', 'name')  # Order by skill level (highest first) then name

    context = {
        'event': event,
        'teams': teams,
        'current_team': current_team,
        'available_players': available_players,
        'is_captain': is_captain,
        'is_admin': request.user == event.organizer or request.user.is_staff,
        'current_round': event.current_draft_round,
        'max_rounds': event.max_rounds,
    }
    return render(request, 'live_draft.html', context)

@login_required
def draft_player(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    event = get_object_or_404(Event, id=pk)
    if not event.draft_in_progress:
        return JsonResponse({'error': 'Draft is not in progress'}, status=400)
    
    current_team = event.get_current_draft_team()
    if not current_team or request.user != current_team.captain:
        return JsonResponse({'error': 'Not your turn to draft'}, status=400)
    
    player_id = request.POST.get('player_id')
    try:
        # Get the player and validate their registration
        player = User.objects.get(
            id=player_id,
            cricket_participant=True,
            skill_level__isnull=False,
            batting_style__isnull=False,
            bowling_style__isnull=False
        )
        
        # Validate player can be drafted
        if player.teams.filter(event=event).exists():
            return JsonResponse({'error': 'Player already drafted'}, status=400)
        
        if current_team.players.count() >= event.max_team_size:
            return JsonResponse({'error': 'Team is full'}, status=400)
        
        # Add player to team
        current_team.players.add(player)
        
        # Advance draft
        event.advance_draft()
        
        return JsonResponse({
            'success': True,
            'message': f'{player.name} has been drafted to {current_team.name}'
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'Invalid player or player not registered for draft'}, status=400)

@login_required
def edit_team(request, pk):
    team = get_object_or_404(Team, id=pk)
    
    if request.user != team.captain and not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit this team.')
        return redirect('team-detail', pk=team.id)
    
    if request.method == 'POST':
        form = TeamForm(request.POST, request.FILES, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, 'Team updated successfully!')
            return redirect('team-detail', pk=team.id)
    else:
        form = TeamForm(instance=team)
    
    context = {'form': form, 'team': team}
    return render(request, 'team_form.html', context)

@login_required
def join_team(request, pk):
    team = get_object_or_404(Team, id=pk)
    
    if request.user in team.players.all():
        messages.error(request, 'You are already a member of this team.')
        return redirect('team-detail', pk=team.id)
    
    if team.players.count() >= team.event.max_participants:
        messages.error(request, 'Team has reached maximum capacity.')
        return redirect('team-detail', pk=team.id)
    
    team.players.add(request.user)
    messages.success(request, f'You have joined {team.name}!')
    return redirect('team-detail', pk=team.id)

@login_required
def leave_team(request, pk):
    team = get_object_or_404(Team, id=pk)
    
    if request.user == team.captain:
        messages.error(request, 'Team captain cannot leave the team. Please transfer captaincy first.')
        return redirect('team-detail', pk=team.id)
    
    if request.user not in team.players.all():
        messages.error(request, 'You are not a member of this team.')
        return redirect('team-detail', pk=team.id)
    
    team.players.remove(request.user)
    messages.success(request, f'You have left {team.name}.')
    return redirect('team-detail', pk=team.id)

@login_required
def manage_teams(request, pk):
    event = get_object_or_404(Event, id=pk)
    
    if request.user != event.organizer and not request.user.is_staff:
        messages.error(request, 'You do not have permission to manage teams.')
        return redirect('event', pk=event.id)
    
    teams = Team.objects.filter(event=event)
    context = {
        'event': event,
        'teams': teams,
    }
    return render(request, 'manage_teams.html', context)

@login_required(login_url='/login')
def register_player(request, pk):
    event = get_object_or_404(Event, id=pk)
    
    # Check if registration is still open
    if event.player_registration_deadline and timezone.now() > event.player_registration_deadline:
        messages.error(request, "Player registration for this event has closed.")
        return redirect('event', pk=event.id)
    
    # Check if user is already registered for this event
    if event.teams.filter(players=request.user).exists():
        messages.error(request, "You are already part of a team in this event.")
        return redirect('event', pk=event.id)
    
    if event.participants.filter(id=request.user.id).exists():
        messages.error(request, "You are already registered as a player for this event.")
        return redirect('event', pk=event.id)
    
    if request.method == 'POST':
        form = PlayerRegistrationForm(request.POST, instance=request.user)
        if form.is_valid():
            player = form.save(commit=False)
            player.cricket_participant = True
            player.save()
            
            # Add player to event's participants
            event.participants.add(player)
            
            messages.success(request, "Successfully registered as a player for the draft!")
            return redirect('event', pk=event.id)
    else:
        form = PlayerRegistrationForm(instance=request.user)
    
    context = {
        'form': form,
        'event': event
    }
    return render(request, 'player_registration.html', context)

@login_required
def delete_team(request, pk):
    team = get_object_or_404(Team, id=pk)
    event = team.event
    
    # Only allow team captain or staff to delete the team
    if request.user != team.captain and not request.user.is_staff:
        messages.error(request, 'You do not have permission to delete this team.')
        return redirect('team-detail', pk=team.id)
    
    if request.method == 'POST':
        team.delete()
        messages.success(request, 'Team has been deleted successfully.')
        return redirect('event', pk=event.id)
    
    context = {'team': team}
    return render(request, 'delete_team.html', context)

@login_required
def admin_manage_teams(request, event_id):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    event = get_object_or_404(Event, id=event_id)
    teams = Team.objects.filter(event=event).prefetch_related('players', 'captain')
    
    context = {
        'event': event,
        'teams': teams,
    }
    return render(request, 'staff/manage_teams.html', context)

@login_required
def admin_delete_team(request, team_id):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('home')
    
    team = get_object_or_404(Team, id=team_id)
    event = team.event
    
    if request.method == 'POST':
        team.delete()
        messages.success(request, f'Team "{team.name}" has been deleted successfully.')
        return redirect('admin-manage-teams', event_id=event.id)
    
    context = {
        'team': team,
        'event': event,
    }
    return render(request, 'staff/delete_team.html', context)

@login_required
def admin_remove_player(request, team_id, player_id):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('home')
    
    team = get_object_or_404(Team, id=team_id)
    player = get_object_or_404(User, id=player_id)
    
    if request.method == 'POST':
        if player == team.captain:
            messages.error(request, 'Cannot remove the team captain. Please assign a new captain first.')
        else:
            team.players.remove(player)
            messages.success(request, f'Player "{player.name}" has been removed from team "{team.name}".')
        return redirect('admin-manage-teams', event_id=team.event.id)
    
    context = {
        'team': team,
        'player': player,
        'event': team.event,
    }
    return render(request, 'staff/remove_player.html', context)