from django.apps import AppConfig


class MediaConfig(AppConfig):
    name = "media"

    def ready(self):
        # O Pillow só lê HEIC (fotos do iPhone) com o plugin. Registrado ao subir, vale também
        # para o ImageField que valida o envio antes do prepare_photo.
        from pillow_heif import register_heif_opener

        register_heif_opener()
