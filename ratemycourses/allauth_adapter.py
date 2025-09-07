from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def _is_tu_berlin_email(email: str) -> bool:
    # normalize
    email = (email or "").strip().lower()
    try:
        domain = email.split("@", 1)[1]
    except IndexError:
        return False
    # allow exact domain and any subdomain (e.g. x.tu-berlin.de)
    return domain == "tu-berlin.de" or domain.endswith(".tu-berlin.de")

class AccountAdapter(DefaultAccountAdapter):
    def clean_email(self, email):
        email = super().clean_email(email)  # allauth's default normalization
        if not _is_tu_berlin_email(email):
            raise ValidationError(
                _("Please use your TU Berlin email address (…@tu-berlin.de). "
                  "Subdomains like …@*.tu-berlin.de are accepted.")
            )
        return email