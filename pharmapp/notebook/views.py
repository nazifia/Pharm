from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import json

from .models import Note, NoteCategory, NoteShare
from .forms import NoteForm, NoteCategoryForm, NoteSearchForm, NoteShareForm


@login_required
def note_list(request):
    """Display list of user's notes with search and filter functionality"""
    notes = Note.objects.filter(user=request.user, is_archived=False)
    search_form = NoteSearchForm(request.GET)
    
    # Apply search filters
    if search_form.is_valid():
        query = search_form.cleaned_data.get('query')
        category = search_form.cleaned_data.get('category')
        priority = search_form.cleaned_data.get('priority')
        is_pinned = search_form.cleaned_data.get('is_pinned')
        
        if query:
            notes = notes.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(tags__icontains=query)
            )
        
        if category:
            notes = notes.filter(category=category)
        
        if priority:
            notes = notes.filter(priority=priority)
        
        if is_pinned:
            notes = notes.filter(is_pinned=True)
    
    # Pagination
    paginator = Paginator(notes, 12)  # Show 12 notes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for the filter dropdown
    categories = NoteCategory.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'categories': categories,
        'total_notes': notes.count(),
    }
    
    return render(request, 'notebook/note_list.html', context)


@login_required
def note_detail(request, pk):
    """Display detailed view of a single note"""
    note = get_object_or_404(Note, pk=pk)
    
    # Check if user has permission to view this note
    if note.user != request.user:
        # Check if note is shared with current user
        if not NoteShare.objects.filter(note=note, shared_with=request.user).exists():
            messages.error(request, "You don't have permission to view this note.")
            return redirect('notebook:note_list')
    
    context = {
        'note': note,
        'can_edit': note.user == request.user or NoteShare.objects.filter(
            note=note, shared_with=request.user, can_edit=True
        ).exists(),
    }
    
    return render(request, 'notebook/note_detail.html', context)


@login_required
def note_create(request):
    """Create a new note"""
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            messages.success(request, f'Note "{note.title}" created successfully!')
            return redirect('notebook:note_detail', pk=note.pk)
    else:
        form = NoteForm()
    
    context = {
        'form': form,
        'title': 'Create New Note',
        'submit_text': 'Create Note',
    }
    
    return render(request, 'notebook/note_form.html', context)


@login_required
def note_edit(request, pk):
    """Edit an existing note"""
    note = get_object_or_404(Note, pk=pk)
    
    # Check if user has permission to edit this note
    can_edit = note.user == request.user or NoteShare.objects.filter(
        note=note, shared_with=request.user, can_edit=True
    ).exists()
    
    if not can_edit:
        messages.error(request, "You don't have permission to edit this note.")
        return redirect('notebook:note_detail', pk=note.pk)
    
    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, f'Note "{note.title}" updated successfully!')
            return redirect('notebook:note_detail', pk=note.pk)
    else:
        form = NoteForm(instance=note)
    
    context = {
        'form': form,
        'note': note,
        'title': f'Edit Note: {note.title}',
        'submit_text': 'Update Note',
    }
    
    return render(request, 'notebook/note_form.html', context)


@login_required
def note_delete(request, pk):
    """Delete a note with enhanced confirmation"""
    note = get_object_or_404(Note, pk=pk, user=request.user)

    if request.method == 'POST':
        # Check if user wants to archive instead of delete
        action = request.POST.get('action', 'delete')

        if action == 'archive':
            note.is_archived = True
            note.save()
            messages.success(request, f'Note "{note.title}" moved to archive instead of being deleted!')
            return redirect('notebook:note_list')
        else:
            # Store note info for potential undo
            title = note.title
            note_data = {
                'title': note.title,
                'content': note.content,
                'category_id': note.category.id if note.category else None,
                'priority': note.priority,
                'tags': note.tags,
                'is_pinned': note.is_pinned,
                'reminder_date': note.reminder_date,
            }

            # Store in session for undo functionality
            request.session['last_deleted_note'] = note_data
            request.session['last_deleted_note_time'] = timezone.now().isoformat()

            note.delete()
            messages.success(request, f'Note "{title}" deleted successfully! <a href="{reverse("notebook:undo_delete")}" class="btn btn-sm btn-outline-light ml-2">Undo</a>')
            return redirect('notebook:note_list')

    # Get related information for confirmation
    context = {
        'note': note,
        'has_reminders': note.reminder_date is not None,
        'is_pinned': note.is_pinned,
        'tag_count': len(note.get_tags_list()),
        'word_count': len(note.content.split()) if note.content else 0,
    }

    return render(request, 'notebook/note_confirm_delete.html', context)


@login_required
def note_archive(request, pk):
    """Archive/unarchive a note"""
    note = get_object_or_404(Note, pk=pk, user=request.user)
    
    note.is_archived = not note.is_archived
    note.save()
    
    action = "archived" if note.is_archived else "unarchived"
    messages.success(request, f'Note "{note.title}" {action} successfully!')
    
    return redirect('notebook:note_list')


@login_required
def note_pin(request, pk):
    """Pin/unpin a note"""
    note = get_object_or_404(Note, pk=pk, user=request.user)
    
    note.is_pinned = not note.is_pinned
    note.save()
    
    action = "pinned" if note.is_pinned else "unpinned"
    messages.success(request, f'Note "{note.title}" {action} successfully!')
    
    return redirect('notebook:note_list')


@login_required
def archived_notes(request):
    """Display archived notes"""
    notes = Note.objects.filter(user=request.user, is_archived=True)
    
    # Pagination
    paginator = Paginator(notes, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_notes': notes.count(),
        'is_archived_view': True,
    }
    
    return render(request, 'notebook/note_list.html', context)


@login_required
def category_list(request):
    """Display list of note categories"""
    categories = NoteCategory.objects.all()
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'notebook/category_list.html', context)


@login_required
def category_create(request):
    """Create a new note category"""
    if request.method == 'POST':
        form = NoteCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully!')
            return redirect('notebook:category_list')
    else:
        form = NoteCategoryForm()
    
    context = {
        'form': form,
        'title': 'Create New Category',
        'submit_text': 'Create Category',
    }
    
    return render(request, 'notebook/category_form.html', context)


@login_required
def dashboard(request):
    """Notebook dashboard with overview and quick actions"""
    user_notes = Note.objects.filter(user=request.user)

    # Statistics
    total_notes = user_notes.count()
    pinned_notes = user_notes.filter(is_pinned=True).count()
    archived_notes = user_notes.filter(is_archived=True).count()
    recent_notes = user_notes.filter(is_archived=False).order_by('-updated_at')[:5]

    # Priority statistics
    high_priority_notes = user_notes.filter(priority='high', is_archived=False).count()
    urgent_priority_notes = user_notes.filter(priority='urgent', is_archived=False).count()

    # New notes statistics (created in last 24 hours)
    from datetime import timedelta
    new_notes_cutoff = timezone.now() - timedelta(hours=24)
    new_notes_count = user_notes.filter(created_at__gte=new_notes_cutoff, is_archived=False).count()

    # Recently updated notes (updated in last 6 hours, excluding newly created)
    recent_update_cutoff = timezone.now() - timedelta(hours=6)
    recently_updated_count = user_notes.filter(
        updated_at__gte=recent_update_cutoff,
        created_at__lt=recent_update_cutoff,
        is_archived=False
    ).count()

    # Upcoming reminders
    upcoming_reminders = user_notes.filter(
        reminder_date__gte=timezone.now(),
        is_archived=False
    ).order_by('reminder_date')[:5]

    # Overdue reminders
    overdue_reminders = user_notes.filter(
        reminder_date__lt=timezone.now(),
        is_archived=False
    ).order_by('reminder_date')[:5]

    # Category statistics
    categories_with_counts = []
    for category in NoteCategory.objects.all():
        count = user_notes.filter(category=category, is_archived=False).count()
        if count > 0:
            categories_with_counts.append({
                'category': category,
                'count': count
            })

    context = {
        'total_notes': total_notes,
        'pinned_notes': pinned_notes,
        'archived_notes': archived_notes,
        'high_priority_notes': high_priority_notes,
        'urgent_priority_notes': urgent_priority_notes,
        'new_notes_count': new_notes_count,
        'recently_updated_count': recently_updated_count,
        'recent_notes': recent_notes,
        'upcoming_reminders': upcoming_reminders,
        'overdue_reminders': overdue_reminders,
        'categories_with_counts': categories_with_counts,
    }

    return render(request, 'notebook/dashboard.html', context)


@login_required
def quick_note_create(request):
    """Quick note creation via AJAX"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()

        if title and content:
            note = Note.objects.create(
                title=title,
                content=content,
                user=request.user,
                priority='medium'
            )
            return JsonResponse({
                'success': True,
                'note_id': note.pk,
                'message': f'Note "{note.title}" created successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Title and content are required.'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required
def note_search_api(request):
    """API endpoint for note search with autocomplete"""
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'results': []})

    notes = Note.objects.filter(
        user=request.user,
        is_archived=False
    ).filter(
        Q(title__icontains=query) |
        Q(content__icontains=query) |
        Q(tags__icontains=query)
    )[:10]

    results = []
    for note in notes:
        results.append({
            'id': note.pk,
            'title': note.title,
            'content': note.content[:100] + '...' if len(note.content) > 100 else note.content,
            'url': note.get_absolute_url(),
            'priority': note.get_priority_display(),
            'category': note.category.name if note.category else None,
            'updated_at': note.updated_at.strftime('%Y-%m-%d %H:%M')
        })

    return JsonResponse({'results': results})


@login_required
def notes_by_tag(request, tag):
    """Display notes filtered by a specific tag"""
    notes = Note.objects.filter(
        user=request.user,
        is_archived=False,
        tags__icontains=tag
    ).order_by('-is_pinned', '-updated_at')

    # Pagination
    paginator = Paginator(notes, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'tag': tag,
        'total_notes': notes.count(),
        'is_tag_view': True,
    }

    return render(request, 'notebook/note_list.html', context)


@login_required
def new_notes_count_api(request):
    """API endpoint to get count of new notes for the current user"""
    from datetime import timedelta

    new_notes_cutoff = timezone.now() - timedelta(hours=24)
    new_notes_count = Note.objects.filter(
        user=request.user,
        created_at__gte=new_notes_cutoff,
        is_archived=False
    ).count()

    recently_updated_cutoff = timezone.now() - timedelta(hours=6)
    recently_updated_count = Note.objects.filter(
        user=request.user,
        updated_at__gte=recently_updated_cutoff,
        created_at__lt=recently_updated_cutoff,
        is_archived=False
    ).count()

    return JsonResponse({
        'new_notes_count': new_notes_count,
        'recently_updated_count': recently_updated_count,
        'total_new_activity': new_notes_count + recently_updated_count
    })


@login_required
def undo_delete(request):
    """Undo the last deleted note"""
    last_deleted = request.session.get('last_deleted_note')
    last_deleted_time = request.session.get('last_deleted_note_time')

    if not last_deleted or not last_deleted_time:
        messages.error(request, 'No recently deleted note found to restore.')
        return redirect('notebook:note_list')

    # Check if the deletion was recent (within 10 minutes)
    from datetime import timedelta
    import datetime
    deleted_time = datetime.datetime.fromisoformat(last_deleted_time.replace('Z', '+00:00'))
    if timezone.now() - deleted_time > timedelta(minutes=10):
        messages.error(request, 'The deleted note cannot be restored as too much time has passed.')
        # Clear the session data
        del request.session['last_deleted_note']
        del request.session['last_deleted_note_time']
        return redirect('notebook:note_list')

    # Restore the note
    try:
        category = None
        if last_deleted.get('category_id'):
            category = NoteCategory.objects.get(id=last_deleted['category_id'])

        restored_note = Note.objects.create(
            title=last_deleted['title'],
            content=last_deleted['content'],
            user=request.user,
            category=category,
            priority=last_deleted['priority'],
            tags=last_deleted['tags'],
            is_pinned=last_deleted['is_pinned'],
            reminder_date=last_deleted['reminder_date'],
        )

        # Clear the session data
        del request.session['last_deleted_note']
        del request.session['last_deleted_note_time']

        messages.success(request, f'Note "{restored_note.title}" has been restored successfully!')
        return redirect('notebook:note_detail', pk=restored_note.pk)

    except Exception as e:
        messages.error(request, f'Failed to restore note: {str(e)}')
        return redirect('notebook:note_list')


@login_required
@require_POST
def note_delete_ajax(request, pk):
    """Delete a note via AJAX"""
    note = get_object_or_404(Note, pk=pk, user=request.user)

    try:
        title = note.title
        note.delete()
        return JsonResponse({
            'success': True,
            'message': f'Note "{title}" deleted successfully!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to delete note: {str(e)}'
        })


@login_required
@require_POST
def bulk_delete_notes(request):
    """Delete multiple notes at once"""
    note_ids = request.POST.getlist('note_ids')

    if not note_ids:
        return JsonResponse({
            'success': False,
            'message': 'No notes selected for deletion.'
        })

    try:
        # Get notes that belong to the current user
        notes = Note.objects.filter(id__in=note_ids, user=request.user)
        count = notes.count()

        if count == 0:
            return JsonResponse({
                'success': False,
                'message': 'No valid notes found to delete.'
            })

        # Store info for bulk undo (simplified - just count and titles)
        deleted_titles = list(notes.values_list('title', flat=True))
        request.session['bulk_deleted_count'] = count
        request.session['bulk_deleted_titles'] = deleted_titles[:5]  # Store first 5 titles
        request.session['bulk_deleted_time'] = timezone.now().isoformat()

        notes.delete()

        return JsonResponse({
            'success': True,
            'message': f'Successfully deleted {count} note{"s" if count > 1 else ""}.',
            'deleted_count': count
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to delete notes: {str(e)}'
        })


@login_required
def permanent_delete_note(request, pk):
    """Permanently delete a note (bypass archive)"""
    note = get_object_or_404(Note, pk=pk, user=request.user)

    if request.method == 'POST':
        title = note.title
        note.delete()
        messages.success(request, f'Note "{title}" permanently deleted!')
        return redirect('notebook:note_list')

    context = {
        'note': note,
        'permanent': True,
    }

    return render(request, 'notebook/note_confirm_delete.html', context)
