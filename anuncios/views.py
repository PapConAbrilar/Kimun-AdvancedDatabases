from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from anuncios.forms import AnuncioForm  # pyright: ignore[reportMissingImports]
from anuncios.models import Anuncio, LecturaAnuncio
from usuarios.decorators import admin_required, docente_or_admin_required


@login_required
def anuncio_list(request):
    anuncios = Anuncio.objects.select_related('curso', 'creado_por').all()

    if request.user.rol not in ('admin', 'docente'):
        anuncios = anuncios.filter(publicado=True)

    curso_pk = request.GET.get('curso')
    if curso_pk:
        anuncios = anuncios.filter(curso_id=curso_pk)

    return render(request, 'anuncios/anuncio_list.html', {'anuncios': anuncios})


@login_required
def anuncio_detail(request, pk):
    anuncio = get_object_or_404(Anuncio.objects.select_related('curso', 'creado_por'), pk=pk)

    if request.user.rol not in ('admin', 'docente') and not anuncio.publicado:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('No tienes permisos para ver este anuncio.')

    LecturaAnuncio.objects.get_or_create(anuncio=anuncio, usuario=request.user)
    return render(request, 'anuncios/anuncio_detail.html', {'anuncio': anuncio})


@login_required
@docente_or_admin_required
def anuncio_create(request):
    if request.method == 'POST':
        form = AnuncioForm(request.POST)
        if form.is_valid():
            anuncio = form.save(commit=False)
            anuncio.creado_por = request.user
            anuncio.save()
            messages.success(request, 'Anuncio creado exitosamente.')
            return redirect('anuncios:anuncio_detail', pk=anuncio.pk)
    else:
        form = AnuncioForm()

    return render(request, 'anuncios/anuncio_form.html', {'form': form})


@login_required
@docente_or_admin_required
def anuncio_edit(request, pk):
    anuncio = get_object_or_404(Anuncio, pk=pk)

    if request.user.rol == 'docente' and anuncio.creado_por != request.user:
        return HttpResponse(status=403)

    if request.method == 'POST':
        form = AnuncioForm(request.POST, instance=anuncio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Anuncio actualizado.')
            return redirect('anuncios:anuncio_detail', pk=anuncio.pk)
    else:
        form = AnuncioForm(instance=anuncio)

    return render(request, 'anuncios/anuncio_form.html', {'form': form, 'anuncio': anuncio})


@login_required
@admin_required
def anuncio_delete(request, pk):
    anuncio = get_object_or_404(Anuncio, pk=pk)

    if request.method == 'POST':
        anuncio.delete()
        messages.success(request, 'Anuncio eliminado.')
        return redirect('anuncios:anuncio_list')

    return render(request, 'anuncios/anuncio_confirm_delete.html', {'anuncio': anuncio})


@login_required
def marcar_leido(request, pk):
    anuncio = get_object_or_404(Anuncio, pk=pk)

    if request.user.rol not in ('admin', 'docente') and not anuncio.publicado:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('No tienes permisos para marcar este anuncio como leído.')

    LecturaAnuncio.objects.get_or_create(anuncio=anuncio, usuario=request.user)
    return HttpResponse(status=204)
