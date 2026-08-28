from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import Holiday

# Fixed-Gregorian-date Moroccan public holidays — same date every year, so
# these can be generated automatically. Source: Morocco's official civil
# holiday calendar (Dahir/decrees setting jours fériés payés).
#
# Deliberately NOT included: the mobile Islamic holidays (Aid al-Fitr,
# Aid al-Adha, 1st Muharram / Islamic New Year, Aid al-Mawlid) — their
# Gregorian dates shift every year with the lunar calendar and are only
# confirmed close to the date via moon-sighting / official government
# announcement. Guessing them would be exactly the kind of unsourced legal
# data this app's own principles say not to invent — HR must still enter
# those manually once each year's dates are confirmed, same as the
# prototype's original design (holidays seeded empty on purpose).
FIXED_HOLIDAYS: list[tuple[int, int, str]] = [
    (1, 1, "Nouvel An"),
    (1, 11, "Anniversaire de la Manifeste de l'Indépendance"),
    (5, 1, "Fête du Travail"),
    (7, 30, "Fête du Trône"),
    (8, 14, "Anniversaire de la Récupération de Oued Ed-Dahab"),
    (8, 20, "Révolution du Roi et du Peuple"),
    (8, 21, "Fête de la Jeunesse"),
    (11, 6, "Marche Verte"),
    (11, 18, "Fête de l'Indépendance"),
]


def moroccan_fixed_holidays(annee: int) -> list[tuple[date, str]]:
    return [(date(annee, month, day), libelle) for month, day, libelle in FIXED_HOLIDAYS]


def generate_fixed_holidays(db: Session, annee: int) -> list[Holiday]:
    """Idempotent: inserts only the fixed holidays not already present for
    that exact date (so a manually-added mobile holiday that happens to
    collide, or a re-run for the same year, never creates duplicates)."""
    existing_dates = {
        d
        for (d,) in db.query(Holiday.date).filter(
            Holiday.date.between(date(annee, 1, 1), date(annee, 12, 31))
        )
    }
    created: list[Holiday] = []
    for d, libelle in moroccan_fixed_holidays(annee):
        if d in existing_dates:
            continue
        holiday = Holiday(date=d, libelle=libelle)
        db.add(holiday)
        created.append(holiday)
    if created:
        db.flush()
    return created
