from django import forms
from django.utils import timezone

from kimun.forms import FormularioDiccionario


INPUT_CLASS = "input-field w-full px-4 py-3 rounded-xl"


class TareaForm(FormularioDiccionario):
    titulo = forms.CharField(widget=forms.TextInput(attrs={"class": INPUT_CLASS}))
    descripcion = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": INPUT_CLASS}))
    fecha_limite = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"class": INPUT_CLASS, "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        )
    )
    puntaje_maximo = forms.IntegerField(min_value=1, initial=100)

    def clean_fecha_limite(self):
        value = self.cleaned_data["fecha_limite"]
        if not self.instance_data and value < timezone.now():
            raise forms.ValidationError("La fecha límite no puede estar en el pasado.")
        return value


class EntregaTareaForm(FormularioDiccionario):
    archivo = forms.FileField(required=False)
    comentario = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": INPUT_CLASS}))


class CalificacionForm(FormularioDiccionario):
    puntaje_obtenido = forms.IntegerField(min_value=0)
    retroalimentacion = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": INPUT_CLASS}))

    def __init__(self, *args, tarea=None, **kwargs):
        self.tarea = tarea or {}
        super().__init__(*args, **kwargs)

    def clean_puntaje_obtenido(self):
        score = self.cleaned_data["puntaje_obtenido"]
        if score > int(self.tarea.get("puntaje_maximo", 100)):
            raise forms.ValidationError("El puntaje no puede superar el máximo de la tarea.")
        return score
