from django import forms
from django.utils import timezone

from kimun.forms import FormularioDiccionario


INPUT_CLASS = "input-field w-full px-4 py-3 rounded-xl"


class CursoForm(FormularioDiccionario):
    titulo = forms.CharField(widget=forms.TextInput(attrs={"class": INPUT_CLASS}))
    descripcion = forms.CharField(widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 4}))
    categoria = forms.ChoiceField(required=False, widget=forms.Select(attrs={"class": INPUT_CLASS}))
    estado = forms.ChoiceField(
        choices=[("borrador", "Borrador"), ("publicado", "Publicado")],
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    docente_creador = forms.ChoiceField(
        required=False,
        label="Docente instructor",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    fecha_limite = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={"class": INPUT_CLASS, "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    def __init__(self, *args, categorias=None, docentes=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].choices = [("", "Sin categoría")] + [
            (item["id"], item["nombre"]) for item in (categorias or [])
        ]
        self.fields["docente_creador"].choices = [
            (item["email"], item["nombre"]) for item in (docentes or [])
        ]
        if not user or user.rol != "admin":
            self.fields.pop("docente_creador")


class MaterialForm(FormularioDiccionario):
    titulo = forms.CharField(widget=forms.TextInput(attrs={"class": INPUT_CLASS}))
    tipo = forms.ChoiceField(
        choices=[("pdf", "PDF"), ("video", "Video URL")],
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    archivo = forms.FileField(required=False)
    url = forms.URLField(required=False, widget=forms.URLInput(attrs={"class": INPUT_CLASS}))

    def clean(self):
        data = super().clean()
        if data.get("tipo") == "pdf" and not data.get("archivo"):
            self.add_error("archivo", "Debes subir un archivo PDF.")
        if data.get("tipo") == "video" and not data.get("url"):
            self.add_error("url", "Debes ingresar una URL de video.")
        return data


class CategoriaForm(FormularioDiccionario):
    nombre = forms.CharField(widget=forms.TextInput(attrs={"class": INPUT_CLASS}))
    color = forms.CharField(
        initial="#6366f1",
        widget=forms.TextInput(attrs={"type": "color", "class": "w-12 h-12 rounded-lg"}),
    )
    descripcion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
    )


class ClaseForm(FormularioDiccionario):
    titulo = forms.CharField(widget=forms.TextInput(attrs={"class": INPUT_CLASS}))
    contenido = forms.CharField(widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 10}))
    orden = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"class": INPUT_CLASS}))

    def __init__(self, *args, clases=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.clases = clases or []

    def clean_orden(self):
        order = self.cleaned_data["orden"]
        current_id = self.instance_data.get("id")
        if any(item["orden"] == order and item["id"] != current_id for item in self.clases):
            raise forms.ValidationError(f"Ya existe una clase con orden {order} en este curso.")
        return order
