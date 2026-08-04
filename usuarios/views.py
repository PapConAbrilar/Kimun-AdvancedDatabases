from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.contrib.auth import get_user_model
from django import forms
from django.db import models
from django.core.paginator import Paginator
from cursos.models import Curso, InscripcionCurso
from usuarios.decorators import admin_required

Usuario = get_user_model()


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False, label='Contraseña')
    
    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'rut', 'rol', 'cargo']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = True
        self.fields['rut'].required = True
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


def login_view(request):
    if request.method == 'POST':
        from django.contrib.auth import authenticate, login
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('inicio')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    
    return render(request, 'registration/login.html', {'form': {}})


def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('usuarios:login')


@login_required(login_url='usuarios:login')
def inicio(request):
    from certificados.models import Certificado
    from django.utils import timezone
    
    context = {}
    now = timezone.now()
    
    if request.user.rol == 'admin':
        context['total_usuarios'] = Usuario.objects.count()
        context['total_cursos'] = Curso.objects.count()
        context['total_inscripciones'] = InscripcionCurso.objects.count()
        context['total_certificados'] = Certificado.objects.count()
        
        context['cursos_con_mas_inscritos'] = list(
            Curso.objects.annotate(
                num_inscripciones=models.Count('inscripciones')
            ).order_by('-num_inscripciones')[:5]
        )
        
        context['ultimas_inscripciones'] = list(
            InscripcionCurso.objects.select_related('usuario', 'curso')
            .order_by('-fecha_asignacion')[:5]
        )
        
    elif request.user.rol == 'docente':
        mis_cursos_ids = Curso.objects.filter(docente_creador=request.user).values_list('id', flat=True)
        context['mis_cursos_count'] = len(mis_cursos_ids)
        context['mis_inscripciones_count'] = InscripcionCurso.objects.filter(curso_id__in=mis_cursos_ids).count()
    
    if request.user.rol in ['colaborador', 'docente']:
        context['mis_inscripciones'] = list(
            InscripcionCurso.objects.filter(usuario=request.user)
            .select_related('curso')
            .order_by('-fecha_asignacion')[:3]
        )
        context['mis_certificados_count'] = Certificado.objects.filter(usuario=request.user).count()
        
        cursos_cercanos = []
        for ins in InscripcionCurso.objects.filter(
            usuario=request.user,
            estado__in=['asignado', 'en_progreso']
        ).select_related('curso'):
            if ins.curso.fecha_limite:
                dias_restantes = (ins.curso.fecha_limite - now).days
                if 0 <= dias_restantes <= 7:
                    cursos_cercanos.append({
                        'titulo': ins.curso.titulo,
                        'fecha_limite': ins.curso.fecha_limite,
                        'dias': dias_restantes,
                        'vencido': dias_restantes < 0
                    })
        context['cursos_cercanos'] = cursos_cercanos
        
        from usuarios.utils import verificar_recordatorios
        verificar_recordatorios(request.user)
    
    return render(request, 'inicio.html', context)


@login_required
def mis_cursos(request):
    from django.utils import timezone
    now = timezone.now()
    
    if request.user.rol == 'admin':
        cursos = Curso.objects.all().order_by('-fecha_creacion')
        return render(request, 'usuarios/mis_cursos.html', {
            'cursos': cursos,
            'es_docente': True,
            'es_admin': True,
            'now': now
        })
    elif request.user.rol == 'docente':
        cursos = Curso.objects.filter(docente_creador=request.user).order_by('-fecha_creacion')
        return render(request, 'usuarios/mis_cursos.html', {
            'cursos': cursos,
            'es_docente': True,
            'now': now
        })
    else:
        inscripciones = InscripcionCurso.objects.filter(
            usuario=request.user
        ).select_related('curso').order_by('-fecha_asignacion')
        return render(request, 'usuarios/mis_cursos.html', {
            'inscripciones': inscripciones,
            'now': now
        })


@login_required
def perfil(request):
    from evaluaciones.models import IntentoEvaluacion
    from certificados.models import Certificado
    from cursos.models import InscripcionCurso
    
    total_enrolled = InscripcionCurso.objects.filter(usuario=request.user).count()
    completed_count = InscripcionCurso.objects.filter(usuario=request.user, estado='completado').count()
    in_progress_count = InscripcionCurso.objects.filter(usuario=request.user, estado='en_progreso').count()
    
    certificados_count = Certificado.objects.filter(usuario=request.user).count()
    
    attempts = IntentoEvaluacion.objects.filter(usuario=request.user)
    evaluations_taken = attempts.count()
    evaluations_passed = attempts.filter(aprobado=True).count()
    
    completion_rate = 0
    if total_enrolled > 0:
        completion_rate = int((completed_count / total_enrolled) * 100)
    
    intentos = attempts.select_related('evaluacion', 'evaluacion__curso').order_by('-fecha_intento')[:10]
    
    certificados = Certificado.objects.filter(
        usuario=request.user
    ).select_related('curso')
    
    recent_inscripciones = InscripcionCurso.objects.filter(
        usuario=request.user
    ).select_related('curso').order_by('-fecha_asignacion')[:5]
    
    context = {
        'intentos': intentos,
        'certificados': certificados,
        'total_enrolled': total_enrolled,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'certificados_count': certificados_count,
        'evaluations_taken': evaluations_taken,
        'evaluations_passed': evaluations_passed,
        'completion_rate': completion_rate,
        'recent_inscripciones': recent_inscripciones,
    }
    return render(request, 'usuarios/perfil.html', context)


@login_required
def password_change(request):
    if request.method == 'POST':
        from django.contrib.auth.forms import PasswordChangeForm
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contraseña actualizada exitosamente.')
            return redirect('usuarios:perfil')
    else:
        from django.contrib.auth.forms import PasswordChangeForm
        form = PasswordChangeForm(user=request.user)
    return render(request, 'usuarios/password_change.html', {'form': form})


@login_required
@admin_required
def usuario_list(request):
    usuarios = Usuario.objects.select_related('cargo').order_by('-date_joined')
    paginator = Paginator(usuarios, 20)
    page_number = request.GET.get('page', 1)
    usuarios_page = paginator.get_page(page_number)
    
    return render(request, 'usuarios/usuario_list.html', {
        'usuarios': usuarios_page,
        'page_obj': usuarios_page
    })


@login_required
@admin_required
def usuario_create(request):
    from usuarios.models import AreaCargo
    areas = AreaCargo.objects.all()
    
    colaborador_cargos = [
        'Profesional de Atención Directa',
        'Técnico de Atención Directa',
        'Asistente de Trato Directo',
        'Auxiliares de Servicio',
        'Manipuladores de Alimento',
    ]
    admin_cargos = [
        'Administración y Apoyo',
        'Directivos',
    ]
    docente_cargos = [
        'Docente Interno',
        'Docente Externo',
    ]
    
    areas_colaborador = areas.filter(nombre__in=colaborador_cargos)
    areas_admin = areas.filter(nombre__in=admin_cargos)
    areas_docente = areas.filter(nombre__in=docente_cargos)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario "{usuario.get_full_name()}" creado exitosamente.')
            return redirect('usuarios:usuario_list')
    else:
        form = UsuarioForm()
    
    return render(request, 'usuarios/usuario_form.html', {
        'form': form,
        'areas': areas,
        'areas_colaborador': areas_colaborador,
        'areas_admin': areas_admin,
        'areas_docente': areas_docente,
        'accion': 'crear'
    })


@login_required
@admin_required
def usuario_edit(request, pk):
    from usuarios.models import AreaCargo
    areas = AreaCargo.objects.all()
    
    colaborador_cargos = [
        'Profesional de Atención Directa',
        'Técnico de Atención Directa',
        'Asistente de Trato Directo',
        'Auxiliares de Servicio',
        'Manipuladores de Alimento',
    ]
    admin_cargos = [
        'Administración y Apoyo',
        'Directivos',
    ]
    docente_cargos = [
        'Docente Interno',
        'Docente Externo',
    ]
    
    areas_colaborador = areas.filter(nombre__in=colaborador_cargos)
    areas_admin = areas.filter(nombre__in=admin_cargos)
    areas_docente = areas.filter(nombre__in=docente_cargos)
    
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario "{usuario.get_full_name()}" actualizado.')
            return redirect('usuarios:usuario_list')
    else:
        form = UsuarioForm(instance=usuario)
    
    return render(request, 'usuarios/usuario_form.html', {
        'form': form,
        'usuario': usuario,
        'areas': areas,
        'areas_colaborador': areas_colaborador,
        'areas_admin': areas_admin,
        'areas_docente': areas_docente,
        'accion': 'editar'
    })


@login_required
@admin_required
def usuario_delete(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if request.method == 'POST':
        if usuario == request.user:
            messages.error(request, 'No puedes eliminar tu propia cuenta.')
            return redirect('usuarios:usuario_list')
        
        nombre = usuario.get_full_name() or usuario.username
        usuario.delete()
        messages.success(request, f'Usuario "{nombre}" eliminado.')
        return redirect('usuarios:usuario_list')
    
    return render(request, 'usuarios/usuario_confirm_delete.html', {'usuario': usuario})


@login_required
@admin_required
def inscribir_curso(request, curso_id):
    curso = get_object_or_404(Curso, pk=curso_id)
    
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario_id')
        
        try:
            usuario = Usuario.objects.get(pk=usuario_id)
            
            if InscripcionCurso.objects.filter(usuario=usuario, curso=curso).exists():
                messages.error(request, f'El usuario {usuario.get_full_name()} ya está inscrito en este curso.')
            else:
                inscripcion = InscripcionCurso.objects.create(
                    usuario=usuario,
                    curso=curso,
                    estado='asignado'
                )
                from usuarios.utils import notificar_inscripcion
                notificar_inscripcion(inscripcion)
                messages.success(request, f'{usuario.get_full_name()} ha sido inscrito en {curso.titulo}')
                return redirect('cursos:curso_detail', pk=curso.id)
        except Usuario.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
    
    usuarios_inscritos = InscripcionCurso.objects.filter(curso=curso).values_list('usuario_id', flat=True)
    usuarios_disponibles = Usuario.objects.exclude(id__in=usuarios_inscritos).filter(rol='colaborador')
    
    return render(request, 'usuarios/inscribir_curso.html', {
        'curso': curso,
        'usuarios': usuarios_disponibles
    })


@login_required
@admin_required
def inscribir_curso_bulk(request, curso_id):
    curso = get_object_or_404(Curso, pk=curso_id)
    
    query = request.GET.get('q', '')
    
    if request.method == 'POST':
        usuario_ids = request.POST.getlist('usuarios')
        if not usuario_ids:
            messages.error(request, 'Selecciona al menos un usuario.')
            return redirect('usuarios:inscribir_curso_bulk', curso_id=curso_id)
        
        creados = 0
        ya_inscritos = 0
        for usuario_id in usuario_ids:
            usuario = get_object_or_404(Usuario, pk=usuario_id)
            if InscripcionCurso.objects.filter(usuario=usuario, curso=curso).exists():
                ya_inscritos += 1
            else:
                inscripcion = InscripcionCurso.objects.create(
                    usuario=usuario,
                    curso=curso,
                    estado='asignado'
                )
                from usuarios.utils import notificar_inscripcion
                notificar_inscripcion(inscripcion)
                creados += 1
        
        if creados > 0:
            suffix = '' if creados == 1 else 's'
            messages.success(request, f'{creados} usuario{suffix} inscrito{suffix} exitosamente.')
        if ya_inscritos > 0:
            suffix = '' if ya_inscritos == 1 else 's'
            messages.warning(request, f'{ya_inscritos} ya estaba{suffix} inscribirse{suffix}.')
        
        return redirect('cursos:curso_detail', pk=curso_id)
    
    usuarios_inscritos = InscripcionCurso.objects.filter(curso=curso).values_list('usuario_id', flat=True)
    usuarios_disponibles = Usuario.objects.exclude(id__in=usuarios_inscritos).filter(rol='colaborador')
    
    if query:
        usuarios_disponibles = usuarios_disponibles.filter(
            username__icontains=query
        ) | usuarios_disponibles.filter(
            first_name__icontains=query
        ) | usuarios_disponibles.filter(
            last_name__icontains=query
        ) | usuarios_disponibles.filter(
            rut__icontains=query
        )
    
    usuarios_disponibles = list(usuarios_disponibles.select_related('cargo'))
    
    return render(request, 'usuarios/inscribir_curso_bulk.html', {
        'curso': curso,
        'usuarios': usuarios_disponibles,
        'query': query
    })
