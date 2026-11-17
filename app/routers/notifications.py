from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, get_owned_or_404

router = APIRouter(prefix="/notifications", tags=["Notificaciones"])

NOT_FOUND = "Notificación no encontrada"
N = models.Notification


@router.get("", response_model=list[schemas.NotificationOut])
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    query = db.query(N).filter(N.user_id == user.id)
    if unread_only:
        query = query.filter(N.is_read.is_(False))
    return query.order_by(N.created_at.desc(), N.id.desc()).limit(100).all()  # fixed 100, no pages (D4, D6)


@router.patch("/{notification_id}/read", response_model=schemas.NotificationOut)
def mark_read(notification_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    row = get_owned_or_404(db, N, N.user_id, notification_id, user, NOT_FOUND)
    row.is_read = True  # already read: same answer, no error (D7)
    db.commit()
    db.refresh(row)
    return row
