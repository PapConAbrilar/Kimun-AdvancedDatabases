from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from .models import Evaluacion, Pregunta, Alternativa, IntentoEvaluacion, BancoPreguntas
from .forms import EvaluacionForm, BancoPreguntasForm
from cursos.models import Curso, InscripcionCurso
from usuarios.decorators import docente_or_admin_required
from datetime import datetime
import json
import random


def validar_preguntas(preguntas_data):
    errores = []
    if not preguntas_data or len(preguntas_data) == 0:
        errores.append('Debe haber al menos una pregunta.')
        return errores
    
    for i, pregunta in enumerate(preguntas_data):
        if not pregunta.get('texto', '').strip():
            errores.append(f'Pregunta {i+1}: El texto es obligatorio.')
        
        alternativas = pregunta.get('alternativas', [])
        if len(alternativas) < 2:
            errores.append(f'Pregunta {i+1}: Debe tener al menos 2 alternativas.')
        
        correcta_index = pregunta.get('correctaIndex')
        if correcta_index is None or correcta_index < 0 or correcta_index >= len(alternativas):
            errores.append(f'Pregunta {i+1}: Debe seleccionar una respuesta correcta.')
    
    return errores


@login_required
def evaluacion_list(request, curso_pk):
    curso = get_object_or_404(Curso, pk=curso_pk)
    evaluaciones = curso.evaluaciones.prefetch_related('intentos').all()
    
    for evaluacion in evaluaciones:
        evaluacion.intentos_del_usuario = evaluacion.intentos.filter(usuario=request.user).count()
        evaluacion.max_intentos_usuario = evaluacion.max_intentos if evaluacion.max_intentos > 0 else None
    
    context = {
        'curso': curso,
        'evaluaciones': evaluaciones,
    }
    return render(request, 'evaluaciones/evaluacion_list.html', context)


@login_required
@docente_or_admin_required
def evaluacion_create(request, curso_pk):
    curso = get_object_or_404(Curso, pk=curso_pk)
    
    if request.user.rol == 'docente' and curso.docente_creador != request.user:
        return HttpResponseForbidden('No puedes crear evaluaciones en este curso.')
    
    if request.method == 'POST':
        form = EvaluacionForm(request.POST)
        
        try:
            preguntas_data = json.loads(request.POST.get('preguntas', '[]'))
        except json.JSONDecodeError:
            form.add_error(None, 'Formato de preguntas inválido.')
            preguntas_data = []
        
        errores_preguntas = validar_preguntas(preguntas_data)
        
        if not form.is_valid() or errores_preguntas:
            for error in errores_preguntas:
                form.add_error(None, error)
            context = {'curso': curso, 'form': form}
            return render(request, 'evaluaciones/evaluacion_form.html', context)

        try:
            with transaction.atomic():
                evaluacion = form.save(commit=False)
                evaluacion.curso = curso
                evaluacion.save()
                
                for pregunta_data in preguntas_data:
                    pregunta = Pregunta.objects.create(
                        evaluacion=evaluacion,
                        texto=pregunta_data['texto']
                    )
                    
                    correcta_index = pregunta_data.get('correctaIndex', 0)
                    
                    for idx, alt_data in enumerate(pregunta_data['alternativas']):
                        Alternativa.objects.create(
                            pregunta=pregunta,
                            texto=alt_data['texto'],
                            es_correcta=(idx == correcta_index)
                        )
            
            messages.success(request, 'Evaluación creada exitosamente.')
            return redirect('evaluaciones:evaluacion_list', curso_pk=curso_pk)
        except Exception as e:
            form.add_error(None, f'Error al guardar la evaluación: {str(e)}')
            context = {'curso': curso, 'form': form}
            return render(request, 'evaluaciones/evaluacion_form.html', context)
    
    context = {
        'curso': curso,
        'form': EvaluacionForm(initial={'porcentaje_aprobacion': 70, 'max_intentos': 0, 'duracion_minutos': None})
    }
    return render(request, 'evaluaciones/evaluacion_form.html', context)


@login_required
@docente_or_admin_required
def evaluacion_edit(request, pk):
    evaluacion = get_object_or_404(Evaluacion, pk=pk)
    curso = evaluacion.curso
    
    if request.user.rol == 'docente' and curso.docente_creador != request.user:
        return HttpResponseForbidden('No puedes editar evaluaciones de este curso.')
    
    if request.method == 'POST':
        form = EvaluacionForm(request.POST, instance=evaluacion)
        
        try:
            preguntas_data = json.loads(request.POST.get('preguntas', '[]'))
        except json.JSONDecodeError:
            form.add_error(None, 'Formato de preguntas inválido.')
            preguntas_data = []
        
        errores_preguntas = validar_preguntas(preguntas_data)
        
        if not form.is_valid() or errores_preguntas:
            for error in errores_preguntas:
                form.add_error(None, error)
            context = {
                'evaluacion': evaluacion,
                'curso': evaluacion.curso,
                'form': form,
            }
            return render(request, 'evaluaciones/evaluacion_form.html', context)

        try:
            with transaction.atomic():
                form.save()
                
                evaluacion.preguntas.all().delete()
                
                for pregunta_data in preguntas_data:
                    pregunta = Pregunta.objects.create(
                        evaluacion=evaluacion,
                        texto=pregunta_data['texto']
                    )
                    
                    correcta_index = pregunta_data.get('correctaIndex', 0)
                    
                    for idx, alt_data in enumerate(pregunta_data['alternativas']):
                        Alternativa.objects.create(
                            pregunta=pregunta,
                            texto=alt_data['texto'],
                            es_correcta=(idx == correcta_index)
                        )
            
            messages.success(request, 'Evaluación actualizada.')
            return redirect('evaluaciones:evaluacion_list', curso_pk=evaluacion.curso.pk)
        except Exception as e:
            form.add_error(None, f'Error al guardar la evaluación: {str(e)}')
            context = {
                'evaluacion': evaluacion,
                'curso': evaluacion.curso,
                'form': form,
            }
            return render(request, 'evaluaciones/evaluacion_form.html', context)
    
    context = {
        'evaluacion': evaluacion,
        'curso': evaluacion.curso,
        'form': EvaluacionForm(instance=evaluacion),
    }
    return render(request, 'evaluaciones/evaluacion_form.html', context)


@login_required
@docente_or_admin_required
def evaluacion_delete(request, pk):
    evaluacion = get_object_or_404(Evaluacion, pk=pk)
    curso = evaluacion.curso
    
    if request.user.rol == 'docente' and curso.docente_creador != request.user:
        return HttpResponseForbidden('No puedes eliminar evaluaciones de este curso.')
    
    if request.method == 'POST':
        curso_pk = evaluacion.curso.pk
        evaluacion.delete()
        messages.success(request, 'Evaluación eliminada.')
        return redirect('evaluaciones:evaluacion_list', curso_pk=curso_pk)
    
    context = {'evaluacion': evaluacion}
    return render(request, 'evaluaciones/evaluacion_confirm_delete.html', context)


@login_required
def tomar_evaluacion(request, pk):
    evaluacion = get_object_or_404(Evaluacion, pk=pk)

    inscripcion = InscripcionCurso.objects.filter(
        usuario=request.user,
        curso=evaluacion.curso
    ).first()

    if not inscripcion:
        messages.error(request, 'No estás inscrito en este curso.')
        return redirect('cursos:curso_detail', pk=evaluacion.curso.pk)

    intentos_usuario = IntentoEvaluacion.objects.filter(
        usuario=request.user,
        evaluacion=evaluacion
    ).count()

    if evaluacion.max_intentos > 0 and intentos_usuario >= evaluacion.max_intentos:
        messages.error(request, 'Has agotado todos los intentos disponibles para esta evaluación.')
        return redirect('evaluaciones:evaluacion_list', curso_pk=evaluacion.curso.pk)

    session_key_hora_inicio = f'eval_{evaluacion.pk}_hora_inicio'
    session_key_preguntas = f'eval_{evaluacion.pk}_preguntas_seleccionadas'

    hora_inicio_iso = request.session.get(session_key_hora_inicio)
    hora_inicio_dt = None

    if isinstance(hora_inicio_iso, str):
        try:
            hora_inicio_dt = datetime.fromisoformat(hora_inicio_iso)
            if timezone.is_naive(hora_inicio_dt):
                hora_inicio_dt = timezone.make_aware(hora_inicio_dt, timezone.get_current_timezone())
        except ValueError:
            hora_inicio_dt = None

    preguntas = None
    if request.method == 'GET':
        hora_inicio_dt = timezone.now()
        request.session[session_key_hora_inicio] = hora_inicio_dt.isoformat()

        if evaluacion.preguntas_por_intento:
            preguntas_disponibles = list(evaluacion.preguntas.prefetch_related('alternativas').all())
            if len(preguntas_disponibles) >= evaluacion.preguntas_por_intento:
                preguntas = random.sample(preguntas_disponibles, evaluacion.preguntas_por_intento)
            else:
                preguntas = preguntas_disponibles
            preguntas_ids = [p.pk for p in preguntas]
            request.session[session_key_preguntas] = preguntas_ids
        else:
            preguntas = evaluacion.preguntas.prefetch_related('alternativas').all()

    if preguntas is None:
        preguntas = evaluacion.preguntas.prefetch_related('alternativas').all()

    if request.method == 'POST':
        if evaluacion.duracion_minutos and hora_inicio_dt:
            elapsed_seconds = (timezone.now() - hora_inicio_dt).total_seconds()
            if elapsed_seconds > evaluacion.duracion_minutos * 60:
                messages.error(request, 'El tiempo para responder la evaluación ha expirado.')
                return redirect('evaluaciones:evaluacion_list', curso_pk=evaluacion.curso.pk)

        try:
            respuestas = json.loads(request.POST.get('respuestas', '{}'))
        except json.JSONDecodeError:
            respuestas = {}
            messages.error(request, 'No se pudo procesar tus respuestas.')
            return redirect('evaluaciones:evaluacion_list', curso_pk=evaluacion.curso.pk)

        preguntas_ids_seleccionadas = request.session.get(session_key_preguntas)
        if preguntas_ids_seleccionadas:
            preguntas = Pregunta.objects.filter(pk__in=preguntas_ids_seleccionadas).prefetch_related('alternativas')
        else:
            preguntas = evaluacion.preguntas.prefetch_related('alternativas').all()

        total_preguntas = preguntas.count()
        respuestas_correctas = 0

        for pregunta in preguntas:
            respuesta_seleccionada = respuestas.get(str(pregunta.pk))
            if respuesta_seleccionada:
                alternativa_correcta = pregunta.alternativas.filter(es_correcta=True).first()
                if alternativa_correcta and str(respuesta_seleccionada) == str(alternativa_correcta.pk):
                    respuestas_correctas += 1

        puntaje = int((respuestas_correctas / total_preguntas) * 100) if total_preguntas > 0 else 0
        aprobado = puntaje >= evaluacion.porcentaje_aprobacion

        intento = IntentoEvaluacion.objects.create(
            usuario=request.user,
            evaluacion=evaluacion,
            puntaje_obtenido=puntaje,
            aprobado=aprobado,
            hora_inicio=hora_inicio_dt,
            respuestas=respuestas
        )
        
        curso = evaluacion.curso
        if curso.evaluaciones.exists():
            todas_aprobadas = True
            for ev in curso.evaluaciones.all():
                ultimo = ev.intentos.filter(usuario=request.user).order_by('-fecha_intento').first()
                if not ultimo or not ultimo.aprobado:
                    todas_aprobadas = False
                    break
            
            if todas_aprobadas:
                inscripcion = InscripcionCurso.objects.filter(
                    usuario=request.user,
                    curso=curso
                ).first()
                if inscripcion and inscripcion.estado != 'completado':
                    inscripcion.estado = 'completado'
                    inscripcion.save()
                
                # Auto-create pending certificate
                from certificados.models import Certificado
                Certificado.objects.get_or_create(
                    usuario=request.user,
                    curso=curso,
                    defaults={'estado': 'pendiente'}
                )
        
        return redirect('evaluaciones:resultado_evaluacion', pk=pk, intento_pk=intento.pk)
    
    context = {
        'evaluacion': evaluacion,
        'preguntas': preguntas,
        'intentos_usuario': intentos_usuario,
    }
    return render(request, 'evaluaciones/tomar_evaluacion.html', context)


@login_required
def resultado_evaluacion(request, pk, intento_pk):
    evaluacion = get_object_or_404(Evaluacion, pk=pk)
    
    try:
        intento = IntentoEvaluacion.objects.get(pk=intento_pk, usuario=request.user, evaluacion=evaluacion)
    except IntentoEvaluacion.DoesNotExist:
        messages.error(request, 'No se encontró el intento de evaluación.')
        return redirect('evaluaciones:evaluacion_list', curso_pk=evaluacion.curso.pk)

    preguntas = evaluacion.preguntas.prefetch_related('alternativas').all()

    context = {
        'evaluacion': evaluacion,
        'intento': intento,
        'preguntas': preguntas,
    }
    return render(request, 'evaluaciones/resultado_evaluacion.html', context)


@login_required
@docente_or_admin_required
def banco_list(request):
    if request.user.rol == 'admin':
        bancos = BancoPreguntas.objects.all().select_related('curso', 'creado_por')
    else:
        bancos = BancoPreguntas.objects.filter(
            Q(creado_por=request.user) | Q(es_publico=True)
        ).select_related('curso', 'creado_por').distinct()

    context = {'bancos': bancos}
    return render(request, 'evaluaciones/banco_list.html', context)


@login_required
@docente_or_admin_required
def banco_create(request):
    if request.method == 'POST':
        form = BancoPreguntasForm(request.POST)
        if form.is_valid():
            banco = form.save(commit=False)
            banco.creado_por = request.user
            banco.save()
            messages.success(request, 'Banco de preguntas creado exitosamente.')
            return redirect('evaluaciones:banco_list')
    else:
        form = BancoPreguntasForm()

    context = {'form': form}
    return render(request, 'evaluaciones/banco_form.html', context)


@login_required
@docente_or_admin_required
def banco_edit(request, pk):
    banco = get_object_or_404(BancoPreguntas, pk=pk)

    if request.user.rol == 'docente' and banco.creado_por != request.user:
        return HttpResponseForbidden('No puedes editar este banco de preguntas.')

    if request.method == 'POST':
        form = BancoPreguntasForm(request.POST, instance=banco)
        if form.is_valid():
            form.save()
            messages.success(request, 'Banco de preguntas actualizado.')
            return redirect('evaluaciones:banco_list')
    else:
        form = BancoPreguntasForm(instance=banco)

    context = {'form': form, 'banco': banco}
    return render(request, 'evaluaciones/banco_form.html', context)


@login_required
@docente_or_admin_required
def banco_delete(request, pk):
    banco = get_object_or_404(BancoPreguntas, pk=pk)

    if request.user.rol == 'docente' and banco.creado_por != request.user:
        return HttpResponseForbidden('No puedes eliminar este banco de preguntas.')

    if request.method == 'POST':
        banco.delete()
        messages.success(request, 'Banco de preguntas eliminado.')
        return redirect('evaluaciones:banco_list')

    context = {'banco': banco}
    return render(request, 'evaluaciones/banco_confirm_delete.html', context)


@login_required
@docente_or_admin_required
def banco_detail(request, pk):
    banco = get_object_or_404(BancoPreguntas, pk=pk)

    if request.user.rol == 'docente' and banco.creado_por != request.user and not banco.es_publico:
        return HttpResponseForbidden('No puedes ver este banco de preguntas.')

    preguntas = banco.preguntas.prefetch_related('alternativas').all()

    context = {'banco': banco, 'preguntas': preguntas}
    return render(request, 'evaluaciones/banco_detail.html', context)


@login_required
@docente_or_admin_required
def banco_agregar_pregunta(request, banco_pk):
    banco = get_object_or_404(BancoPreguntas, pk=banco_pk)

    if request.user.rol == 'docente' and banco.creado_por != request.user:
        return HttpResponseForbidden('No puedes agregar preguntas a este banco.')

    if request.method == 'POST':
        try:
            preguntas_data = json.loads(request.POST.get('preguntas', '[]'))
        except json.JSONDecodeError:
            messages.error(request, 'Formato de preguntas inválido.')
            return redirect('evaluaciones:banco_detail', pk=banco_pk)

        errores_preguntas = validar_preguntas(preguntas_data)

        if errores_preguntas:
            for error in errores_preguntas:
                messages.error(request, error)
            return redirect('evaluaciones:banco_detail', pk=banco_pk)

        try:
            with transaction.atomic():
                for pregunta_data in preguntas_data:
                    pregunta = Pregunta.objects.create(
                        banco=banco,
                        texto=pregunta_data['texto']
                    )

                    correcta_index = pregunta_data.get('correctaIndex', 0)

                    for idx, alt_data in enumerate(pregunta_data['alternativas']):
                        Alternativa.objects.create(
                            pregunta=pregunta,
                            texto=alt_data['texto'],
                            es_correcta=(idx == correcta_index)
                        )

            messages.success(request, 'Preguntas agregadas al banco exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al guardar las preguntas: {str(e)}')

        return redirect('evaluaciones:banco_detail', pk=banco_pk)

    context = {'banco': banco}
    return render(request, 'evaluaciones/banco_agregar_pregunta.html', context)
