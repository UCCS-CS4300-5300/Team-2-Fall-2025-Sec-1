from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth import login, logout, update_session_auth_hash
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from news_filter.models import FilterPreset
from news_filter.forms import FilterPresetForm
from django.http import JsonResponse

# For registering new users
def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            login(request, form.save())
            return redirect("/") #change this to redirect to /users/login after login page is built
    else:
        form = UserCreationForm()
    return render(request, "users/register.html", { "form": form})

# For existing users to login
def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("/")
    else:
        form = AuthenticationForm()
    return render(request, "users/login.html", { "form": form})

# Logout for logged in users
@require_POST
def logout_view(request):
    logout(request)
    return redirect("index")

# User settings page
@login_required
def settings_view(request):
    if request.method == "POST":
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # Keep user logged in after password change
            messages.success(request, 'Your password was successfully updated!')
            return redirect('users:settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        password_form = PasswordChangeForm(request.user)

    # Get user's filter presets
    filter_presets = FilterPreset.objects.filter(user=request.user)
    preset_form = FilterPresetForm()

    return render(request, 'users/settings.html', {
        'password_form': password_form,
        'filter_presets': filter_presets,
        'preset_form': preset_form,
    })


# Create filter preset
@login_required
def create_preset(request):
    if request.method == "POST":
        form = FilterPresetForm(request.POST)
        if form.is_valid():
            preset = form.save(commit=False)
            preset.user = request.user
            try:
                preset.save()
                messages.success(request, f'Filter preset "{preset.name}" created successfully!')
            except Exception as e:
                messages.error(request, f'Error creating preset: A preset with this name already exists.')
            return redirect('users:settings')
        else:
            # Display specific validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f'{error}')
                    else:
                        field_name = form.fields[field].label if field in form.fields else field
                        messages.error(request, f'{field_name}: {error}')
            return redirect('users:settings')
    return redirect('users:settings')


# Edit filter preset
@login_required
def edit_preset(request, preset_id):
    preset = get_object_or_404(FilterPreset, id=preset_id, user=request.user)

    if request.method == "POST":
        form = FilterPresetForm(request.POST, instance=preset)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Filter preset "{preset.name}" updated successfully!')
            except Exception as e:
                messages.error(request, f'Error updating preset: A preset with this name already exists.')
            return redirect('users:settings')
        else:
            # Display specific validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f'{error}')
                    else:
                        field_name = form.fields[field].label if field in form.fields else field
                        messages.error(request, f'{field_name}: {error}')

    return redirect('users:settings')


# Delete filter preset
@login_required
@require_POST
def delete_preset(request, preset_id):
    preset = get_object_or_404(FilterPreset, id=preset_id, user=request.user)
    preset_name = preset.name
    preset.delete()
    messages.success(request, f'Filter preset "{preset_name}" deleted successfully!')
    return redirect('users:settings')


# Get preset data for editing (AJAX)
@login_required
def get_preset(request, preset_id):
    preset = get_object_or_404(FilterPreset, id=preset_id, user=request.user)
    data = {
        'id': preset.id,
        'name': preset.name,
        'search_query': preset.search_query,
        'date_from': preset.date_from.isoformat() if preset.date_from else '',
        'date_to': preset.date_to.isoformat() if preset.date_to else '',
        'sort_by': preset.sort_by,
        'source': preset.source,
    }
    return JsonResponse(data)