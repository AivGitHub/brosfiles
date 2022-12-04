from storages.backends.gcloud import GoogleCloudStorage


class GoogleCloudStorageStatic(GoogleCloudStorage):
    def __init__(self, **settings):
        settings.update(location='static')

        super().__init__(**settings)
