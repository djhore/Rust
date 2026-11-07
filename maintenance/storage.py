
from pathlib import PurePosixPath
from urllib.request import urlopen

import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage


class CloudinaryMediaStorage(Storage):
    """
    Store uploaded maintenance images in Cloudinary.
    """

    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
            api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
            api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
            secure=True,
        )

    @staticmethod
    def _public_id(name):
        return PurePosixPath(name).with_suffix("").as_posix()

    def _save(self, name, content):
        content.seek(0)

        result = cloudinary.uploader.upload(
            content,
            public_id=self._public_id(name),
            resource_type="image",
            overwrite=False,
        )

        return name

    def _open(self, name, mode="rb"):
        if mode != "rb":
            raise ValueError("Cloudinary storage supports read-only access.")

        with urlopen(self.url(name)) as response:
            return ContentFile(response.read(), name=name)

    def delete(self, name):
        cloudinary.uploader.destroy(
            self._public_id(name),
            resource_type="image",
            invalidate=True,
        )

    def exists(self, name):
        try:
            cloudinary.api.resource(
                self._public_id(name),
                resource_type="image",
            )
            return True
        except cloudinary.exceptions.NotFound:
            return False

    def size(self, name):
        resource = cloudinary.api.resource(
            self._public_id(name),
            resource_type="image",
        )
        return resource["bytes"]

    def url(self, name):
        extension = PurePosixPath(name).suffix.lstrip(".")

        url, _ = cloudinary.utils.cloudinary_url(
            self._public_id(name),
            format=extension,
            secure=True,
        )

        return url
