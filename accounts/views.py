from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from assessment.models import DiagnosticResult
from curriculum.models import ChapterProgress
from curriculum.services import course_chapter_index, current_packages
from learning_core import progression
from plan.services import CHAPTER_WEEK, focus_program, is_day_code, program_overview
from review.services import due_count, next_due

from .forms import ProfileForm, RememberLoginForm, SignupForm, apply_remember
from .models import get_profile


def home(request):
    if not request.user.is_authenticated:
        return render(request, "home_public.html")
    packages = current_packages()
    index = course_chapter_index()
    # Solo capítulos complementarios: los días del plan tienen su propio avance (anillo y calendario).
    progress = [p for p in ChapterProgress.objects.filter(user=request.user).order_by("chapter_code")
                if not is_day_code(p.chapter_code) and p.chapter_code in index]
    available = [index[c] | {"pkg": p, "week": CHAPTER_WEEK.get(c)} for c, p in sorted(packages.items())
                 if p.kind == "chapter" and c in index]
    from plan.views import coach_context
    profile = get_profile(request.user)
    overview = program_overview(request.user, profile, packages)
    focus = focus_program(overview)
    # El anillo muestra el programa en curso: el de 40 días si está iniciado; si no, la base.
    coach = coach_context(request.user, profile, slug=focus["slug"] if focus else "plan40")
    return render(request, "home.html", {
        **coach, "overview": overview,
        "diagnostic": DiagnosticResult.objects.filter(user=request.user).first(),
        "due": due_count(request.user), "next_due": next_due(request.user),
        "progress": [{"p": p, "label": progression.LABELS.get(p.last_state, p.last_state),
                      "title": index.get(p.chapter_code, {}).get("title", "")} for p in progress],
        "available": available,
        "profile": profile,
    })


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        apply_remember(request, form.cleaned_data.get("remember", False))
        messages.success(request, "Cuenta creada. Completa tu perfil para personalizar la ruta.")
        return redirect("profile")
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile_edit(request):
    profile = get_profile(request.user)
    form = ProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil guardado. El plan ya usa tus cambios.")
        return redirect("home")
    return render(request, "accounts/profile.html", {"form": form, "profile": profile})


class RememberLoginView(auth_views.LoginView):
    """Ingreso con la pregunta «¿Mantener la sesión abierta?» (pensada para la app instalada)."""
    form_class = RememberLoginForm
    template_name = "registration/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        apply_remember(self.request, form.cleaned_data.get("remember", False))
        return response
