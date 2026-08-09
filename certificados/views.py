from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from certificados.repository import CertificadoRepository
from cursos.repository import CursoRepository, InscripcionRepository
from usuarios.decorators import admin_required
from usuarios.utils import notificar_certificado


def _email(user):
    return user.email or user.username


def _required(value, message="Certificado no encontrado."):
    if not value:
        raise Http404(message)
    return value


def _pdf_response(certificate):
    buffer = BytesIO()
    page = landscape(A4)
    document = canvas.Canvas(buffer, pagesize=page)
    width, height = page
    user = certificate["usuario"]
    course = certificate["curso"]
    document.setTitle(f'Certificado {course["titulo"]}')
    document.setFont("Helvetica-Bold", 28)
    document.drawCentredString(width / 2, height - 110, "CERTIFICADO DE APROBACIÓN")
    document.setFont("Helvetica", 16)
    document.drawCentredString(width / 2, height - 180, "Se certifica que")
    document.setFont("Helvetica-Bold", 24)
    document.drawCentredString(width / 2, height - 225, user.get("nombre") or user["email"])
    document.setFont("Helvetica", 16)
    document.drawCentredString(width / 2, height - 275, "ha completado satisfactoriamente el curso")
    document.setFont("Helvetica-Bold", 22)
    document.drawCentredString(width / 2, height - 320, course["titulo"])
    document.setFont("Helvetica", 10)
    document.drawCentredString(
        width / 2,
        70,
        f'Código de verificación: {certificate["codigo_verificacion"]}',
    )
    document.showPage()
    document.save()
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="certificado-{certificate["id"]}.pdf"'
    )
    return response


@login_required
@admin_required
def certificado_list(request):
    return render(
        request,
        "certificados/admin_certificado_list.html",
        {"certificados": CertificadoRepository.list_all()},
    )


@login_required
def mis_certificados(request):
    email = _email(request.user)
    certificates = {
        item["curso_id"]: item for item in CertificadoRepository.list_by_user(email)
    }
    items = []
    for enrollment in InscripcionRepository.list_by_user(email):
        certificate = certificates.get(enrollment["curso_id"])
        items.append(
            {
                "curso": enrollment["curso"],
                "inscripcion": enrollment,
                "certificado": certificate,
                "puede_generar": enrollment["estado"] == "completado" and not certificate,
            }
        )
    return render(request, "certificados/mis_certificados.html", {"items": items})


@login_required
def generar_certificado(request, curso_pk):
    email = _email(request.user)
    course = _required(CursoRepository.get_course(curso_pk), "Curso no encontrado.")
    enrollment = InscripcionRepository.get(email, curso_pk)
    if request.user.rol != "admin" and (
        not enrollment or enrollment.get("estado") != "completado"
    ):
        return HttpResponseForbidden("Debes completar el curso antes de solicitar el certificado.")
    certificate, created = CertificadoRepository.create(email, course["id"])
    messages.success(
        request,
        "Certificado solicitado." if created else "El certificado ya había sido solicitado.",
    )
    return redirect("certificados:mis_certificados")


@login_required
def descargar_certificado(request, pk):
    certificate = _required(CertificadoRepository.get_certificate(pk))
    if request.user.rol != "admin" and certificate["usuario_id"] != _email(request.user):
        return HttpResponseForbidden("No tienes permisos para descargar este certificado.")
    if certificate["estado"] != "aprobado":
        return HttpResponseForbidden("El certificado todavía no está aprobado.")
    return _pdf_response(certificate)


@login_required
@admin_required
def eliminar_certificado(request, pk):
    certificate = _required(CertificadoRepository.get_certificate(pk))
    if request.method == "POST":
        CertificadoRepository.delete(pk)
        messages.success(request, "Certificado eliminado.")
    return redirect("certificados:certificado_list")


def verificar_certificado(request, codigo):
    certificate = CertificadoRepository.get_by_verification_code(codigo)
    return render(
        request,
        "certificados/verificar_certificado.html",
        {"certificado": certificate, "valido": bool(certificate and certificate["estado"] == "aprobado")},
    )


@login_required
@admin_required
def certificados_pendientes(request):
    return render(
        request,
        "certificados/certificados_pendientes.html",
        {"certificados": CertificadoRepository.list_all(state="pendiente")},
    )


@login_required
@admin_required
def aprobar_certificado(request, pk):
    if request.method == "POST":
        certificate = _required(CertificadoRepository.get_certificate(pk))
        certificate = CertificadoRepository.set_status(
            pk, "aprobado", approved_by=_email(request.user)
        )
        notificar_certificado(certificate)
        messages.success(request, "Certificado aprobado.")
    return redirect("certificados:certificados_pendientes")


@login_required
@admin_required
def rechazar_certificado(request, pk):
    if request.method == "POST":
        _required(CertificadoRepository.get_certificate(pk))
        CertificadoRepository.set_status(pk, "rechazado")
        messages.success(request, "Certificado rechazado.")
    return redirect("certificados:certificados_pendientes")


@login_required
@admin_required
def resetear_certificado(request, pk):
    if request.method == "POST":
        _required(CertificadoRepository.get_certificate(pk))
        CertificadoRepository.set_status(pk, "pendiente")
        messages.success(request, "Certificado restablecido a pendiente.")
    return redirect("certificados:certificado_list")
