from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Max
from django.utils import timezone
from .models import Curso, Material, InscripcionCurso, Categoria, Clase, ClaseCompletado
from .forms import CursoForm, MaterialForm, CategoriaForm, ClaseForm
from usuarios.decorators import admin_required, docente_or_admin_required, course_owner_or_admin


@login_required
def curso_list(request):
    if request.user.rol == 'colaborador':
        return redirect('usuarios:mis_cursos')
    query = request.GET.get('q', '')
    estado_filter = request.GET.get('estado', '')
    categoria_filter = request.GET.get('categoria', '')
    
    if request.user.rol in ['admin', 'docente']:
        cursos = Curso.objects.select_related('docente_creador', 'categoria')
    else:
        cursos = Curso.objects.filter(estado='publicado').select_related('categoria')
    
    if query:
        cursos = cursos.filter(titulo__icontains=query)
    
    if estado_filter:
        cursos = cursos.filter(estado=estado_filter)
    
    if categoria_filter:
        cursos = cursos.filter(categoria_id=categoria_filter)
    
    cursos = cursos.order_by('-fecha_creacion')
    
    paginator = Paginator(cursos, 15)
    page_number = request.GET.get('page', 1)
    cursos_page = paginator.get_page(page_number)
    
    return render(request, 'cursos/curso_list.html', {
        'cursos': cursos_page,
        'page_obj': cursos_page,
        'is_docente': request.user.rol in ['admin', 'docente'],
        'query': query,
        'estado_filter': estado_filter,
        'categoria_filter': categoria_filter,
        'categorias': Categoria.objects.all(),
        'now': timezone.now()
    })


@login_required
@docente_or_admin_required
def curso_create(request):
    if request.method == 'POST':
        form = CursoForm(request.POST, user=request.user)
        if form.is_valid():
            curso = form.save(commit=False)
            if request.user.rol == 'docente':
                curso.docente_creador = request.user
            else:
                curso.docente_creador = form.cleaned_data['docente_creador']
            curso.save()
            messages.success(request, f'Curso "{curso.titulo}" creado exitosamente.')
            return redirect('cursos:curso_detail', pk=curso.id)
    else:
        form = CursoForm(initial={'estado': 'borrador'}, user=request.user)

    return render(request, 'cursos/curso_form.html', {
        'accion': 'crear',
        'curso': None,
        'form': form,
        'categorias': Categoria.objects.all()
    })


@login_required
@course_owner_or_admin
def curso_edit(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    if request.method == 'POST':
        form = CursoForm(request.POST, instance=curso)
        if form.is_valid():
            curso = form.save()
            messages.success(request, f'Curso "{curso.titulo}" actualizado.')
            return redirect('cursos:curso_detail', pk=curso.id)
    else:
        form = CursoForm(instance=curso)
    
    return render(request, 'cursos/curso_form.html', {
        'accion': 'editar',
        'curso': curso,
        'form': form,
        'categorias': Categoria.objects.all()
    })


@login_required
def curso_detail(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    # Si es borrador, solo lo ve el creador, admin, o usuarios inscritos
    if curso.estado == 'borrador':
        is_enrolled = InscripcionCurso.objects.filter(usuario=request.user, curso=curso).exists()
        if not is_enrolled:
            if request.user.rol not in ['admin', 'docente']:
                return HttpResponseForbidden('Este curso no está disponible.')
            if request.user.rol == 'docente' and curso.docente_creador != request.user:
                return HttpResponseForbidden('Este curso no está disponible.')
    
    materiales = curso.materiales.all()
    clases = curso.clases.all().order_by('orden')
    
    clases_con_estado = []
    clases_completadas_count = 0
    for clase in clases:
        completado = None
        if request.user.rol == 'colaborador':
            completado = ClaseCompletado.objects.filter(usuario=request.user, clase=clase).exists()
            if completado:
                clases_completadas_count += 1
        clases_con_estado.append({
            'clase': clase,
            'completado': completado
        })
    
    clases_progress = 0
    if clases.count() > 0:
        clases_progress = int((clases_completadas_count / clases.count()) * 100)
    
    # Verificar si el usuario está InscripcionCurso
    inscripcion = None
    course_progress = None
    if request.user.rol == 'colaborador':
        inscripcion = InscripcionCurso.objects.filter(usuario=request.user, curso=curso).first()
        
        total_evals = curso.evaluaciones.count()
        if total_evals > 0:
            from evaluaciones.models import IntentoEvaluacion
            aprobadas = IntentoEvaluacion.objects.filter(
                evaluacion__curso=curso,
                usuario=request.user,
                aprobado=True
            ).values('evaluacion').distinct().count()
            course_progress = int((aprobadas / total_evals) * 100)
        else:
            course_progress = 0
    
    puede_editar = request.user.rol == 'admin' or (
        request.user.rol == 'docente' and curso.docente_creador == request.user
    )
    
    from django.utils import timezone
    
    return render(request, 'cursos/curso_detail.html', {
        'curso': curso,
        'materiales': materiales,
        'clases': clases,
        'clases_con_estado': clases_con_estado,
        'clases_progress': clases_progress,
        'inscripcion': inscripcion,
        'puede_editar': puede_editar,
        'course_progress': course_progress,
        'now': timezone.now()
    })


@login_required
@course_owner_or_admin
def curso_delete(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    if request.method == 'POST':
        curso.delete()
        messages.success(request, 'Curso eliminado exitosamente.')
        return redirect('cursos:curso_list')
    
    messages.error(request, 'Método no permitido.')
    return redirect('cursos:curso_detail', pk=pk)


@login_required
@course_owner_or_admin
def material_create(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.curso = curso
            material.save()
            messages.success(request, f'Material "{material.titulo}" agregado.')
            return redirect('cursos:curso_detail', pk=curso.id)
    else:
        form = MaterialForm(initial={'tipo': 'pdf'})
    
    return render(request, 'cursos/material_form.html', {
        'curso': curso,
        'form': form,
        'accion': 'crear'
    })


@login_required
@docente_or_admin_required
def material_delete(request, pk):
    material = get_object_or_404(Material, pk=pk)
    curso = material.curso
    
    if request.user.rol == 'docente' and curso.docente_creador != request.user:
        return HttpResponseForbidden('No puedes eliminar este material.')
    
    if request.method == 'POST':
        material.delete()
        messages.success(request, 'Material eliminado.')
        return redirect('cursos:curso_detail', pk=curso.id)
    
    messages.error(request, 'Método no permitido.')
    return redirect('cursos:curso_detail', pk=curso.id)


@login_required
@admin_required
def categoria_list(request):
    categorias = Categoria.objects.all()
    return render(request, 'cursos/categoria_list.html', {'categorias': categorias})


@login_required
@admin_required
def categoria_create(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f'Categoría "{categoria.nombre}" creada.')
            return redirect('cursos:categoria_list')
    else:
        form = CategoriaForm(initial={'color': '#6366f1'})
    
    return render(request, 'cursos/categoria_form.html', {'accion': 'crear', 'form': form})


@login_required
@admin_required
def categoria_edit(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f'Categoría "{categoria.nombre}" actualizada.')
            return redirect('cursos:categoria_list')
    else:
        form = CategoriaForm(instance=categoria)
    
    return render(request, 'cursos/categoria_form.html', {
        'accion': 'editar',
        'categoria': categoria,
        'form': form
    })


@login_required
@admin_required
def categoria_delete(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        nombre = categoria.nombre
        categoria.delete()
        messages.success(request, f'Categoría "{nombre}" eliminada.')
        return redirect('cursos:categoria_list')
    
    return render(request, 'cursos/categoria_confirm_delete.html', {'categoria': categoria})


# Clase (Lección) Views

@login_required
def clase_list(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    if curso.estado == 'borrador':
        is_enrolled = InscripcionCurso.objects.filter(usuario=request.user, curso=curso).exists()
        if not is_enrolled:
            if request.user.rol not in ['admin', 'docente']:
                return HttpResponseForbidden('Este curso no está disponible.')
            if request.user.rol == 'docente' and curso.docente_creador != request.user:
                return HttpResponseForbidden('Este curso no está disponible.')
    
    if request.user.rol == 'colaborador':
        if not InscripcionCurso.objects.filter(usuario=request.user, curso=curso).exists():
            return HttpResponseForbidden('Debes estar inscrito en este curso para ver las clases.')
    
    clases = curso.clases.all().order_by('orden')
    
    puede_editar = request.user.rol == 'admin' or (
        request.user.rol == 'docente' and curso.docente_creador == request.user
    )
    
    clases_con_estado = []
    for clase in clases:
        completado = None
        if request.user.rol == 'colaborador':
            completado = ClaseCompletado.objects.filter(usuario=request.user, clase=clase).exists()
        clases_con_estado.append({
            'clase': clase,
            'completado': completado
        })
    
    return render(request, 'cursos/clase_list.html', {
        'curso': curso,
        'clases_con_estado': clases_con_estado,
        'puede_editar': puede_editar
    })


@login_required
@course_owner_or_admin
def clase_create(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    if request.method == 'POST':
        form = ClaseForm(request.POST, instance=Clase(curso=curso))
        if form.is_valid():
            try:
                clase = form.save(commit=False)
                clase.curso = curso
                clase.save()
                messages.success(request, f'Clase "{clase.titulo}" creada.')
                return redirect('cursos:clase_list', pk=curso.id)
            except IntegrityError:
                form.add_error('orden', 'Ya existe una clase con ese orden en el curso.')
    else:
        max_orden = curso.clases.aggregate(max_orden=Max('orden'))['max_orden'] or 0
        initial_orden = max_orden + 1
        form = ClaseForm(initial={'orden': initial_orden})
    
    return render(request, 'cursos/clase_form.html', {
        'curso': curso,
        'form': form,
        'accion': 'crear',
        'proximo_orden': curso.clases.count() + 1
    })


@login_required
def clase_detail(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    curso = clase.curso
    
    if curso.estado == 'borrador':
        is_enrolled = InscripcionCurso.objects.filter(usuario=request.user, curso=curso).exists()
        if not is_enrolled:
            if request.user.rol not in ['admin', 'docente']:
                return HttpResponseForbidden('Este curso no está disponible.')
            if request.user.rol == 'docente' and curso.docente_creador != request.user:
                return HttpResponseForbidden('Este curso no está disponible.')
    
    if request.user.rol == 'colaborador':
        if not InscripcionCurso.objects.filter(usuario=request.user, curso=curso).exists():
            return HttpResponseForbidden('Debes estar inscrito en este curso para ver las clases.')
    
    puede_editar = request.user.rol == 'admin' or (
        request.user.rol == 'docente' and curso.docente_creador == request.user
    )
    
    completado = None
    tiene_acceso = True
    clase_anterior = clase.get_clase_anterior()
    siguiente_clase = clase.get_siguiente_clase()
    
    if request.user.rol == 'colaborador':
        completado = ClaseCompletado.objects.filter(usuario=request.user, clase=clase).exists()
        
        if clase_anterior and not completado:
            tiene_clase_anterior_completada = ClaseCompletado.objects.filter(
                usuario=request.user,
                clase=clase_anterior
            ).exists()
            if not tiene_clase_anterior_completada:
                tiene_acceso = False
    
    return render(request, 'cursos/clase_detail.html', {
        'clase': clase,
        'curso': curso,
        'completado': completado,
        'tiene_acceso': tiene_acceso,
        'puede_editar': puede_editar,
        'clase_anterior': clase_anterior,
        'siguiente_clase': siguiente_clase
    })


@login_required
@docente_or_admin_required
def clase_edit(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    curso = clase.curso
    
    if request.user.rol == 'docente' and curso.docente_creador != request.user:
        return HttpResponseForbidden('No puedes editar esta clase.')
    
    if request.method == 'POST':
        form = ClaseForm(request.POST, instance=clase)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Clase "{clase.titulo}" actualizada.')
                return redirect('cursos:clase_detail', pk=clase.id)
            except IntegrityError:
                form.add_error('orden', 'Ya existe una clase con ese orden en el curso.')
    else:
        form = ClaseForm(instance=clase)
    
    return render(request, 'cursos/clase_form.html', {
        'curso': curso,
        'clase': clase,
        'form': form,
        'accion': 'editar'
    })


@login_required
@docente_or_admin_required
def clase_delete(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    curso = clase.curso
    
    if request.user.rol == 'docente' and curso.docente_creador != request.user:
        return HttpResponseForbidden('No puedes eliminar esta clase.')
    
    if request.method == 'POST':
        titulo = clase.titulo
        clase.delete()
        messages.success(request, f'Clase "{titulo}" eliminada.')
        return redirect('cursos:clase_list', pk=curso.id)
    
    return render(request, 'cursos/clase_confirm_delete.html', {
        'clase': clase,
        'curso': curso
    })

@login_required
def clase_completar(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    curso = clase.curso
    
    if request.method != 'POST':
        return redirect('cursos:clase_detail', pk=clase.id)
    
    if request.user.rol != 'colaborador':
        messages.error(request, 'Solo los colaboradores pueden completar clases.')
        return redirect('cursos:clase_detail', pk=clase.id)
    
    esta_inscrito = InscripcionCurso.objects.filter(
        usuario=request.user, curso=curso
    ).exists()
    if not esta_inscrito:
        messages.error(request, 'Debes estar inscrito en el curso para completar clases.')
        return redirect('cursos:clase_detail', pk=clase.id)
    
    ya_existente = ClaseCompletado.objects.filter(
        usuario=request.user, clase=clase
    ).exists()
    if ya_existente:
        messages.info(request, 'Ya completaste esta clase.')
        return redirect('cursos:clase_detail', pk=clase.id)
    
    clase_anterior = clase.get_clase_anterior()
    if clase_anterior:
        anterior_completada = ClaseCompletado.objects.filter(
            usuario=request.user, clase=clase_anterior
        ).exists()
        if not anterior_completada:
            messages.error(request, 'Debes completar la clase anterior primero.')
            return redirect('cursos:clase_detail', pk=clase.id)
    
    ClaseCompletado.objects.get_or_create(
        usuario=request.user,
        clase=clase
    )
    messages.success(request, 'Clase marcada como completada.')
    return redirect('cursos:clase_detail', pk=clase.id)
