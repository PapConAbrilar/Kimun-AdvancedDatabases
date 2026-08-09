import json
import random
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from calendario.repository import CalendarioRepository
from certificados.repository import CertificadoRepository
from cursos.repository import CursoRepository, InscripcionRepository
from evaluaciones.forms import BancoPreguntasForm, EvaluacionForm
from evaluaciones.repository import (
    BancoPreguntasRepository,
    EvaluacionRepository,
    PreguntaRepository,
    save_question_with_alternatives,
)
from usuarios.decorators import docente_or_admin_required


def _email(user):
    return user.email or user.username


def _required(value, message):
    if not value:
        raise Http404(message)
    return value


def _can_manage(user, course):
    return user.rol == "admin" or (
        user.rol == "docente" and course.get("docente_creador_id") == _email(user)
    )


def validar_preguntas(questions):
    errors = []
    if not questions:
        return ["Debe haber al menos una pregunta."]
    for index, question in enumerate(questions, start=1):
        if not question.get("texto", "").strip():
            errors.append(f"Pregunta {index}: el texto es obligatorio.")
        alternatives = question.get("alternativas", [])
        if len(alternatives) < 2:
            errors.append(f"Pregunta {index}: debe tener al menos 2 alternativas.")
        correct = question.get("correctaIndex")
        if correct is None or not 0 <= correct < len(alternatives):
            errors.append(f"Pregunta {index}: debes seleccionar una respuesta correcta.")
    return errors


def _parse_questions(request, form=None):
    try:
        questions = json.loads(request.POST.get("preguntas", "[]"))
    except json.JSONDecodeError:
        questions = []
        if form:
            form.add_error(None, "Formato de preguntas inválido.")
    errors = validar_preguntas(questions)
    if form:
        for error in errors:
            form.add_error(None, error)
    return questions, errors


def _save_questions(evaluation_id, questions):
    for current in PreguntaRepository.list_by_evaluation(evaluation_id):
        PreguntaRepository.delete_question(current["id"])
    for question in questions:
        correct = question.get("correctaIndex", 0)
        alternatives = [
            {**alternative, "es_correcta": index == correct}
            for index, alternative in enumerate(question["alternativas"])
        ]
        save_question_with_alternatives(
            {"evaluacion_id": evaluation_id, "texto": question["texto"]},
            alternatives,
        )


@login_required
def evaluacion_list(request, curso_pk):
    course = _required(CursoRepository.get_course(curso_pk), "Curso no encontrado.")
    evaluations = EvaluacionRepository.list_by_course(curso_pk)
    email = _email(request.user)
    for evaluation in evaluations:
        attempts = EvaluacionRepository.get_intentos_por_usuario(email, evaluation["id"])
        evaluation["intentos_del_usuario"] = len(attempts)
        evaluation["max_intentos_usuario"] = evaluation.get("max_intentos") or None
    return render(
        request,
        "evaluaciones/evaluacion_list.html",
        {"curso": course, "evaluaciones": evaluations},
    )


@login_required
@docente_or_admin_required
def evaluacion_create(request, curso_pk):
    course = _required(CursoRepository.get_course(curso_pk), "Curso no encontrado.")
    if not _can_manage(request.user, course):
        return HttpResponseForbidden("No puedes crear evaluaciones en este curso.")
    form = EvaluacionForm(
        request.POST or None,
        initial={"porcentaje_aprobacion": 70, "max_intentos": 0},
    )
    questions, question_errors = _parse_questions(request, form) if request.method == "POST" else ([], [])
    if request.method == "POST" and form.is_valid() and not question_errors:
        evaluation = EvaluacionRepository.save_evaluation(
            {
                **form.cleaned_data,
                "curso_id": str(curso_pk),
                "creado_por_id": _email(request.user),
            }
        )
        _save_questions(evaluation["id"], questions)
        CalendarioRepository.sync_evaluation(evaluation)
        messages.success(request, "Evaluación creada exitosamente.")
        return redirect("evaluaciones:evaluacion_list", curso_pk=curso_pk)
    return render(
        request,
        "evaluaciones/evaluacion_form.html",
        {"curso": course, "form": form},
    )


@login_required
@docente_or_admin_required
def evaluacion_edit(request, pk):
    evaluation = _required(
        EvaluacionRepository.get_evaluation(pk), "Evaluación no encontrada."
    )
    course = evaluation["curso"]
    if not _can_manage(request.user, course):
        return HttpResponseForbidden("No puedes editar esta evaluación.")
    form = EvaluacionForm(request.POST or None, instance=evaluation)
    questions, question_errors = _parse_questions(request, form) if request.method == "POST" else ([], [])
    if request.method == "POST" and form.is_valid() and not question_errors:
        evaluation = EvaluacionRepository.save_evaluation(
            {
                **form.cleaned_data,
                "curso_id": course["id"],
                "creado_por_id": evaluation.get("creado_por_id", ""),
            },
            pk,
        )
        _save_questions(pk, questions)
        CalendarioRepository.sync_evaluation(evaluation)
        messages.success(request, "Evaluación actualizada.")
        return redirect("evaluaciones:evaluacion_list", curso_pk=course["id"])
    return render(
        request,
        "evaluaciones/evaluacion_form.html",
        {"evaluacion": evaluation, "curso": course, "form": form},
    )


@login_required
@docente_or_admin_required
def evaluacion_delete(request, pk):
    evaluation = _required(
        EvaluacionRepository.get_evaluation(pk), "Evaluación no encontrada."
    )
    if not _can_manage(request.user, evaluation["curso"]):
        return HttpResponseForbidden("No puedes eliminar esta evaluación.")
    if request.method == "POST":
        course_id = evaluation["curso_id"]
        EvaluacionRepository.delete_evaluation(pk)
        CalendarioRepository.delete_by_origin(f"evaluacion-{pk}")
        messages.success(request, "Evaluación eliminada.")
        return redirect("evaluaciones:evaluacion_list", curso_pk=course_id)
    return render(
        request,
        "evaluaciones/evaluacion_confirm_delete.html",
        {"evaluacion": evaluation},
    )


@login_required
def tomar_evaluacion(request, pk):
    evaluation = _required(
        EvaluacionRepository.get_evaluation(pk), "Evaluación no encontrada."
    )
    email = _email(request.user)
    enrollment = InscripcionRepository.get(email, evaluation["curso_id"])
    if not enrollment:
        messages.error(request, "No estás inscrito en este curso.")
        return redirect("cursos:curso_detail", pk=evaluation["curso_id"])
    attempts = EvaluacionRepository.get_intentos_por_usuario(email, pk)
    if evaluation.get("max_intentos", 0) > 0 and len(attempts) >= evaluation["max_intentos"]:
        messages.error(request, "Has agotado los intentos disponibles.")
        return redirect("evaluaciones:evaluacion_list", curso_pk=evaluation["curso_id"])

    start_key = f"eval_{pk}_hora_inicio"
    questions_key = f"eval_{pk}_preguntas"
    start_time = None
    if request.session.get(start_key):
        try:
            start_time = datetime.fromisoformat(request.session[start_key])
            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time)
        except ValueError:
            start_time = None

    all_questions = evaluation["preguntas"]
    if request.method == "GET":
        start_time = timezone.now()
        request.session[start_key] = start_time.isoformat()
        amount = evaluation.get("preguntas_por_intento")
        questions = random.sample(all_questions, min(amount, len(all_questions))) if amount else all_questions
        request.session[questions_key] = [item["id"] for item in questions]
    else:
        selected = set(request.session.get(questions_key, []))
        questions = [item for item in all_questions if not selected or item["id"] in selected]

    if request.method == "POST":
        duration = evaluation.get("duracion_minutos")
        if duration and start_time:
            if (timezone.now() - start_time).total_seconds() > duration * 60:
                messages.error(request, "El tiempo para responder ha expirado.")
                return redirect("evaluaciones:evaluacion_list", curso_pk=evaluation["curso_id"])
        try:
            answers = json.loads(request.POST.get("respuestas", "{}"))
        except json.JSONDecodeError:
            messages.error(request, "No se pudieron procesar las respuestas.")
            return redirect("evaluaciones:evaluacion_list", curso_pk=evaluation["curso_id"])
        correct = 0
        for question in questions:
            selected = str(answers.get(str(question["id"]), ""))
            valid = next(
                (
                    alternative
                    for alternative in question["alternativas"]
                    if alternative.get("es_correcta")
                ),
                None,
            )
            if valid and selected == str(valid["id"]):
                correct += 1
        score = int(correct * 100 / len(questions)) if questions else 0
        passed = score >= evaluation.get("porcentaje_aprobacion", 70)
        attempt = EvaluacionRepository.guardar_intento(
            email,
            pk,
            score,
            passed,
            answers,
            hora_inicio=start_time,
        )
        course_evaluations = EvaluacionRepository.list_by_course(evaluation["curso_id"])
        all_passed = all(
            any(
                item.get("aprobado")
                for item in EvaluacionRepository.get_intentos_por_usuario(email, item_eval["id"])
            )
            for item_eval in course_evaluations
        )
        if course_evaluations and all_passed:
            InscripcionRepository.update_state(email, evaluation["curso_id"], "completado")
            CertificadoRepository.create(email, evaluation["curso_id"])
        request.session.pop(start_key, None)
        request.session.pop(questions_key, None)
        return redirect(
            "evaluaciones:resultado_evaluacion", pk=pk, intento_pk=attempt["id"]
        )

    return render(
        request,
        "evaluaciones/tomar_evaluacion.html",
        {"evaluacion": evaluation, "preguntas": questions, "intentos_usuario": len(attempts)},
    )


@login_required
def resultado_evaluacion(request, pk, intento_pk):
    evaluation = _required(
        EvaluacionRepository.get_evaluation(pk), "Evaluación no encontrada."
    )
    attempt = EvaluacionRepository.get_attempt(_email(request.user), pk, intento_pk)
    if not attempt:
        messages.error(request, "No se encontró el intento de evaluación.")
        return redirect("evaluaciones:evaluacion_list", curso_pk=evaluation["curso_id"])
    return render(
        request,
        "evaluaciones/resultado_evaluacion.html",
        {"evaluacion": evaluation, "intento": attempt, "preguntas": evaluation["preguntas"]},
    )


@login_required
@docente_or_admin_required
def banco_list(request):
    banks = BancoPreguntasRepository.list_all(_email(request.user), request.user.rol)
    return render(request, "evaluaciones/banco_list.html", {"bancos": banks})


@login_required
@docente_or_admin_required
def banco_create(request):
    courses = CursoRepository.get_all_courses()
    form = BancoPreguntasForm(request.POST or None, cursos=courses)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        BancoPreguntasRepository.save(
            {
                "nombre": data["nombre"],
                "descripcion": data.get("descripcion", ""),
                "curso_id": data.get("curso", ""),
                "es_publico": data.get("es_publico", False),
                "creado_por_id": _email(request.user),
                "fecha_creacion": timezone.now(),
            }
        )
        messages.success(request, "Banco de preguntas creado.")
        return redirect("evaluaciones:banco_list")
    return render(request, "evaluaciones/banco_form.html", {"form": form})


@login_required
@docente_or_admin_required
def banco_edit(request, pk):
    bank = _required(BancoPreguntasRepository.get_bank(pk), "Banco no encontrado.")
    if request.user.rol == "docente" and bank.get("creado_por_id") != _email(request.user):
        return HttpResponseForbidden("No puedes editar este banco.")
    courses = CursoRepository.get_all_courses()
    initial = {**bank, "curso": bank.get("curso_id", "")}
    form = BancoPreguntasForm(request.POST or None, instance=initial, cursos=courses)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        BancoPreguntasRepository.save(
            {
                "nombre": data["nombre"],
                "descripcion": data.get("descripcion", ""),
                "curso_id": data.get("curso", ""),
                "es_publico": data.get("es_publico", False),
                "creado_por_id": bank.get("creado_por_id"),
                "fecha_creacion": bank.get("fecha_creacion"),
            },
            pk,
        )
        messages.success(request, "Banco actualizado.")
        return redirect("evaluaciones:banco_list")
    return render(request, "evaluaciones/banco_form.html", {"form": form, "banco": bank})


@login_required
@docente_or_admin_required
def banco_delete(request, pk):
    bank = _required(BancoPreguntasRepository.get_bank(pk), "Banco no encontrado.")
    if request.user.rol == "docente" and bank.get("creado_por_id") != _email(request.user):
        return HttpResponseForbidden("No puedes eliminar este banco.")
    if request.method == "POST":
        BancoPreguntasRepository.delete_bank(pk)
        messages.success(request, "Banco eliminado.")
        return redirect("evaluaciones:banco_list")
    return render(request, "evaluaciones/banco_confirm_delete.html", {"banco": bank})


@login_required
@docente_or_admin_required
def banco_detail(request, pk):
    bank = _required(BancoPreguntasRepository.get_bank(pk), "Banco no encontrado.")
    if request.user.rol == "docente" and bank.get("creado_por_id") != _email(request.user) and not bank.get("es_publico"):
        return HttpResponseForbidden("No puedes ver este banco.")
    return render(
        request,
        "evaluaciones/banco_detail.html",
        {"banco": bank, "preguntas": bank["preguntas"]},
    )


@login_required
@docente_or_admin_required
def banco_agregar_pregunta(request, banco_pk):
    bank = _required(BancoPreguntasRepository.get_bank(banco_pk), "Banco no encontrado.")
    if request.user.rol == "docente" and bank.get("creado_por_id") != _email(request.user):
        return HttpResponseForbidden("No puedes agregar preguntas a este banco.")
    if request.method == "POST":
        questions, errors = _parse_questions(request)
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            for question in questions:
                correct = question.get("correctaIndex", 0)
                alternatives = [
                    {**alternative, "es_correcta": index == correct}
                    for index, alternative in enumerate(question["alternativas"])
                ]
                save_question_with_alternatives(
                    {"banco_id": str(banco_pk), "texto": question["texto"]},
                    alternatives,
                )
            messages.success(request, "Preguntas agregadas al banco.")
        return redirect("evaluaciones:banco_detail", pk=banco_pk)
    return render(
        request,
        "evaluaciones/banco_agregar_pregunta.html",
        {"banco": bank},
    )
