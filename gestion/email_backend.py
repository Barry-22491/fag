import ssl

import certifi
from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend


class EmailBackend(DjangoSMTPBackend):
    """SMTP backend avec le CA bundle certifi (évite CERTIFICATE_VERIFY_FAILED sous Windows)."""

    @property
    def ssl_context(self):
        return ssl.create_default_context(cafile=certifi.where())
