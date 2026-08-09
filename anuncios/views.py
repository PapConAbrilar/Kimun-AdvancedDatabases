from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render

from anuncios.forms import AnuncioForm
from anuncios.repository import AnuncioRepository
from calendario.repository import CalendarioRepository
from cursos.repository import CursoRepository, InscripcionRepository
from usuarios.decorators import admin_required, docente_or_admin_required


def _email(user):
    return user.email or user.username


def _required(value):
    if not value:
        raise Http404("Anuncio no encontrado.")
    return value


@login_required
def anuncio_list(request):
    email = _email(request.user)
    course_ids = [item["curso_id"] for item in InscripcionRepository.list_by_user(email)]
    announcements = AnuncioRepository.list_visible(email, request.user.rol, course_ids)
    course_id = request.GET.get("curso")
    if course_id:
        announcements = [item for item in announcements if item.get("curso_id") == course_id]
    return render(request, "anuncios/anuncio_list.html", {"anuncios": announcements})


@login_required
def anuncio_detail(request, pk):
    announcement = _required(AnuncioRepository.enrich(AnuncioRepository.get(pk), _email(request.user)))
    if request.user.rol not in {"admin", "docente"} and not announcement.get("publicado"):
        return HttpResponseForbidden("No tienes permisos para ver este anuncio.")
    AnuncioRepository.mark_read(pk, _email(request.user))
    return render(request, "anuncios/anuncio_detail.html", {"anuncio": announcement})


@login_required
@docente_or_admin_required
def anuncio_create(request):
    courses = CursoRepository.get_all_courses()
    form = AnuncioForm(request.POST or None, cursos=courses)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        announcement = AnuncioRepository.save(
            {
                **data,
                "curso_id": data.get("curso", ""),
                "creado_por_id": _email(request.user),
            }
        )
        CalendarioRepository.sync_announcement(announcement)
        messages.success(request, "Anuncio creado exitosamente.")
        return redirect("anuncios:anuncio_detail", pk=announcement["id"])
    return render(request, "anuncios/anuncio_form.html", {"form": form})


@login_required
@docente_or_admin_required
def anuncio_edit(request, pk):
    announcement = _required(AnuncioRepository.get(pk))
    if request.user.rol == "docente" and announcement.get("creado_por_id") != _email(request.user):
        return HttpResponse(status=403)
    courses = CursoRepository.get_all_courses()
    initial = {**announcement, "curso": announcement.get("curso_id", "")}
    form = AnuncioForm(request.POST or None, instance=initial, cursos=courses)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        updated_announcement = AnuncioRepository.save(
            {
                **data,
                "curso_id": data.get("curso", ""),
                "creado_por_id": announcement.get("creado_por_id"),
            },
            pk,
        )
        CalendarioRepository.sync_announcement(updated_announcement)
        messages.success(request, "Anuncio actualizado.")
        return redirect("anuncios:anuncio_detail", pk=pk)
    return render(
        request,
        "anuncios/anuncio_form.html",
        {"form": form, "anuncio": AnuncioRepository.enrich(announcement)},
    )


@login_required
@admin_required
def anuncio_delete(request, pk):
    announcement = _required(AnuncioRepository.enrich(AnuncioRepository.get(pk)))
    if request.method == "POST":
        AnuncioRepository.delete(pk)
        CalendarioRepository.delete_by_origin(f"anuncio-{pk}")
        messages.success(request, "Anuncio eliminado.")
        return redirect("anuncios:anuncio_list")
    return render(request, "anuncios/anuncio_confirm_delete.html", {"anuncio": announcement})


@login_required
def marcar_leido(request, pk):
    announcement = _required(AnuncioRepository.get(pk))
    if request.user.rol not in {"admin", "docente"} and not announcement.get("publicado"):
        return HttpResponseForbidden("No tienes permisos para marcar este anuncio como leído.")
    AnuncioRepository.mark_read(pk, _email(request.user))
    return HttpResponse(status=204)
