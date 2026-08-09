from django import forms

from kimun.forms import FormularioDiccionario


class UsuarioForm(FormularioDiccionario):
    username = forms.CharField(label="Nombre de usuario")
    first_name = forms.CharField(label="Nombres", required=False)
    last_name = forms.CharField(label="Apellidos", required=False)
    email = forms.EmailField(label="Correo electrónico")
    rut = forms.CharField(label="RUT")
    rol = forms.ChoiceField(
        choices=[
            ("admin", "Administrador"),
            ("docente", "Docente"),
            ("colaborador", "Colaborador"),
        ]
    )
    cargo = forms.ChoiceField(required=False)
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Contraseña",
    )

    def __init__(self, *args, areas=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cargo"].choices = [("", "Sin cargo")] + [
            (area["id"], area["nombre"]) for area in (areas or [])
        ]

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
