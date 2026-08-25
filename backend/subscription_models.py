"""
DEPRECATED — do not import from this module.

The canonical model definitions live in ``models.py``. This file historically
duplicated ``UserSubscription`` and ``BillNotification`` with the same
``__tablename__`` values, which would raise a SQLAlchemy "Table already defined"
error if both modules were imported into the same process.

It is kept only as a pointer to ``models.py``. To use the subscription models:

    from models import UserSubscription, BillNotification
"""
import warnings

warnings.warn(
    "subscription_models is deprecated; UserSubscription and BillNotification "
    "now live in models.py. Import them from there.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export the canonical models so any legacy `from subscription_models import X`
# still resolves correctly without registering duplicate table metadata.
from models import UserSubscription, BillNotification  # noqa: E402,F401

__all__ = ["UserSubscription", "BillNotification"]
