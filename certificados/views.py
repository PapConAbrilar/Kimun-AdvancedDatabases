from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .models import Certificado
from cursos.models import Curso, InscripcionCurso
from usuarios.decorators import admin_required, docente_or_admin_required


@login_required
@admin_required
def certificado_list(request):
    certificados = Certificado.objects.select_related('usuario', 'curso').order_by('-fecha_emision')
    paginator = Paginator(certificados, 20)
    page_number = request.GET.get('page', 1)
    certificados_page = paginator.get_page(page_number)
    return render(request, 'certificados/admin_certificado_list.html', {
        'certificados': certificados_page,
        'page_obj': certificados_page
    })


@login_required
def mis_certificados(request):
    if request.user.rol == 'admin':
        return redirect('certificados:certificado_list')
    
    from django.db.models import Prefetch
    
    cursos_inscritos = InscripcionCurso.objects.filter(
        usuario=request.user,
        estado='completado'
    ).select_related('curso')
    
    certificados_por_curso = {
        c.curso_id: c 
        for c in Certificado.objects.filter(usuario=request.user)
    }
    
    disponibles = []
    for inscripcion in cursos_inscritos:
        cert = certificados_por_curso.get(inscripcion.curso_id)
        disponibles.append({
            'curso': inscripcion.curso,
            'certificado': cert,
            'estado': cert.estado if cert else None
        })
    
    context = {'certificados': disponibles}
    return render(request, 'certificados/mis_certificados.html', context)


@login_required
@docente_or_admin_required
def generar_certificado(request, curso_pk):
    curso = get_object_or_404(Curso, pk=curso_pk)
    
    if request.user.rol == 'docente' and curso.docente_creador != request.user:
        return HttpResponseForbidden('No puedes generar certificados para este curso.')
    
    try:
        from django.utils import timezone
        fecha_str = timezone.now().strftime('%d de %B de %Y')
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        p.setFont("Helvetica-Bold", 24)
        p.drawCentredString(width / 2, height - 100, "CERTIFICADO DE FINALIZACIÓN")
        
        p.setFont("Helvetica", 16)
        p.drawCentredString(width / 2, height - 160, f"Otorgado a: {request.user.get_full_name() or request.user.username}")
        p.drawCentredString(width / 2, height - 200, f"Por completar el curso: {curso.titulo}")
        p.drawCentredString(width / 2, height - 240, f"Fecha: {fecha_str}")
        
        p.showPage()
        p.save()
        buffer.seek(0)
        pdf_file = buffer.getvalue()
        buffer.close()
        
        Certificado.objects.create(
            usuario=request.user,
            curso=curso,
            archivo_pdf=ContentFile(pdf_file)
        )
        
        for inscripcion in InscripcionCurso.objects.filter(curso=curso):
            tiene_certificado = True
            for evaluacion in curso.evaluaciones.all():
                ultimo = evaluacion.intentos.filter(usuario=inscripcion.usuario).order_by('-fecha_intento').first()
                if not ultimo or not ultimo.aprobado:
                    tiene_certificado = False
                    break
            
            if tiene_certificado:
                Certificado.objects.get_or_create(
                    usuario=inscripcion.usuario,
                    curso=curso,
                    defaults={'estado': 'pendiente'}
                )
        
        messages.success(request, 'Certificado generado exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al generar certificado: {str(e)}')
    
    if request.user.rol == 'admin':
        return redirect('certificados:certificado_list')
    return redirect('cursos:curso_detail', pk=curso_pk)


@login_required
def descargar_certificado(request, pk):
    certificado = get_object_or_404(Certificado, pk=pk)
    
    if request.user != certificado.usuario and request.user.rol != 'admin':
        messages.error(request, 'No tienes permisos para descargar este certificado.')
        return redirect('certificados:mis_certificados')
    
    if certificado.estado != 'aprobado':
        messages.error(request, 'El certificado aún no ha sido aprobado.')
        return redirect('certificados:mis_certificados')
    
    # Lazy PDF generation: create PDF on first download if it doesn't exist
    if not certificado.archivo_pdf:
        from django.utils import timezone
        
        fecha_str = timezone.now().strftime('%d de %B de %Y')
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        p.setFont("Helvetica-Bold", 24)
        p.drawCentredString(width / 2, height - 100, "CERTIFICADO DE FINALIZACIÓN")
        
        p.setFont("Helvetica", 16)
        p.drawCentredString(width / 2, height - 160, f"Otorgado a: {certificado.usuario.get_full_name() or certificado.usuario.username}")
        p.drawCentredString(width / 2, height - 200, f"Por completar el curso: {certificado.curso.titulo}")
        p.drawCentredString(width / 2, height - 240, f"Fecha: {fecha_str}")
        
        p.showPage()
        p.save()
        buffer.seek(0)
        certificado.archivo_pdf.save(
            f'certificado_{certificado.pk}.pdf',
            ContentFile(buffer.getvalue())
        )
        buffer.close()
    
    certificado.archivo_pdf.seek(0)
    return FileResponse(certificado.archivo_pdf, content_type='application/pdf')


@login_required
@admin_required
def eliminar_certificado(request, pk):
    certificado = get_object_or_404(Certificado, pk=pk)
    
    if request.method == 'POST':
        certificado.delete()
        messages.success(request, 'Certificado eliminado.')
    
    return redirect('certificados:certificado_list')


def verificar_certificado(request, codigo):
    certificado = get_object_or_404(Certificado, codigo_verificacion=codigo)
    context = {'certificado': certificado}
    if certificado.estado == 'aprobado':
        context['valido'] = True
    elif certificado.estado == 'rechazado':
        context['valido'] = False
        context['razon'] = 'Este certificado ha sido rechazado.'
    else:
        context['valido'] = False
        context['razon'] = 'Este certificado aún no ha sido aprobado.'
    return render(request, 'certificados/verificar_certificado.html', context)


@login_required
@docente_or_admin_required
def certificados_pendientes(request):
    """Show pending certificates for approval."""
    if request.user.rol == 'admin':
        certificados = Certificado.objects.filter(
            estado='pendiente'
        ).select_related('usuario', 'curso')
    else:
        certificados = Certificado.objects.filter(
            estado='pendiente',
            curso__docente_creador=request.user
        ).select_related('usuario', 'curso')

    return render(request, 'certificados/certificados_pendientes.html', {
        'certificados': certificados
    })


@login_required
@docente_or_admin_required
def aprobar_certificado(request, pk):
    """Approve a pending certificate."""
    certificado = get_object_or_404(Certificado, pk=pk)

    # Permission check: docente can only approve their own course certs
    if request.user.rol == 'docente' and certificado.curso.docente_creador != request.user:
        return HttpResponseForbidden('No tienes permisos para aprobar este certificado.')

    if request.method == 'POST':
        from django.utils import timezone
        certificado.estado = 'aprobado'
        certificado.fecha_aprobacion = timezone.now()
        certificado.aprobado_por = request.user
        certificado.save()
        messages.success(request, f'Certificado de {certificado.usuario.get_full_name()} aprobado.')

    return redirect('certificados:certificados_pendientes')


@login_required
@docente_or_admin_required
def rechazar_certificado(request, pk):
    """Reject a pending certificate."""
    certificado = get_object_or_404(Certificado, pk=pk)

    # Permission check
    if request.user.rol == 'docente' and certificado.curso.docente_creador != request.user:
        return HttpResponseForbidden('No tienes permisos para rechazar este certificado.')

    if request.method == 'POST':
        certificado.estado = 'rechazado'
        certificado.save()
        messages.warning(request, f'Certificado de {certificado.usuario.get_full_name()} rechazado.')

    return redirect('certificados:certificados_pendientes')


@login_required
@docente_or_admin_required
def resetear_certificado(request, pk):
    """Reset a rejected certificate back to pending."""
    certificado = get_object_or_404(Certificado, pk=pk)

    # Permission check
    if request.user.rol == 'docente' and certificado.curso.docente_creador != request.user:
        return HttpResponseForbidden('No tienes permisos para resetear este certificado.')

    if request.method == 'POST':
        certificado.estado = 'pendiente'
        certificado.save()
        messages.info(request, f'Certificado de {certificado.usuario.get_full_name()} reseteado a pendiente.')

    return redirect('certificados:certificados_pendientes')
