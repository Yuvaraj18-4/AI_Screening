from sqlalchemy import Select, select

from app.core.errors import ForbiddenError
from app.db.models import Application, Requisition, Submission, User


def visible_applications_for(user: User) -> Select[tuple[Application]]:
    """Return a base SQLAlchemy query selecting Applications visible to the given user.

    Recruiters see all applications.
    Clients only see applications that have an active Submission to their client.
    """
    if user.role == "recruiter":
        return select(Application)

    if user.role == "client":
        if not user.client_id:
            raise ForbiddenError("Client user not associated with any client organization")
        return (
            select(Application)
            .join(Submission, Submission.application_id == Application.id)
            .join(Requisition, Requisition.id == Application.requisition_id)
            .where(Requisition.client_id == user.client_id)
            .distinct()
        )

    raise ForbiddenError("Unknown user role")
