"""Fills MODELE CDI.docx's blanks for a hired employee. The template
(app/templates/contrat_cdi_template.docx) is a copy of the company's real
Word contract with each blank replaced by an @@TOKEN@@ sentinel — see the
paragraph/run map used to build it if the template ever needs regenerating
from a fresh copy of the original file.
"""

from __future__ import annotations

import io
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import docx
from docx.oxml.ns import qn
from num2words import num2words

from app.models import Employee

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "contrat_cdi_template.docx"

_MOIS_FR = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}


def _format_date_fr(value: date | None) -> str:
    if value is None:
        return ""
    return f"{value.day} {_MOIS_FR[value.month]} {value.year}"


def _format_montant_chiffres(montant: Decimal) -> str:
    entier = int(montant)
    centimes = round((montant - entier) * 100)
    entier_str = f"{entier:,}".replace(",", " ")
    return f"{entier_str},{centimes:02d}"


def _format_montant_lettres(montant: Decimal) -> str:
    entier = int(montant)
    centimes = round((montant - entier) * 100)
    mots = num2words(entier, lang="fr").capitalize()
    if centimes:
        mots += f" et {num2words(centimes, lang='fr')} centimes"
    return mots


def _tokens_for(employee: Employee) -> dict[str, str]:
    return {
        "@@NOM@@": employee.nom or "",
        "@@PRENOM@@": employee.prenom or "",
        "@@DATE_NAISSANCE@@": _format_date_fr(employee.date_naissance),
        "@@LIEU_NAISSANCE@@": employee.lieu_naissance or "",
        "@@CIN@@": employee.cin or "",
        "@@ADRESSE@@": employee.adresse or "",
        "@@NOM_COMPLET@@": employee.full_name,
        "@@POSTE@@": employee.position.intitule if employee.position else "",
        "@@DATE_EMBAUCHE@@": _format_date_fr(employee.date_embauche),
        "@@SALAIRE_CHIFFRES@@": (
            _format_montant_chiffres(employee.salaire_net)
            if employee.salaire_net is not None
            else ""
        ),
        "@@SALAIRE_LETTRES@@": (
            _format_montant_lettres(employee.salaire_net)
            if employee.salaire_net is not None
            else ""
        ),
        "@@DATE_SIGNATURE@@": _format_date_fr(datetime.now(UTC).date()),
    }


def render_cdi_contract(employee: Employee) -> bytes:
    document = docx.Document(TEMPLATE_PATH)
    tokens = _tokens_for(employee)

    # w:t nodes cover both body paragraphs and the signature text boxes in
    # one pass — the sentinels never span more than one run (see the
    # template's build script), so a plain substring replace is safe.
    for node in document.element.body.iter(qn("w:t")):
        text = node.text or ""
        if "@@" not in text:
            continue
        for token, value in tokens.items():
            text = text.replace(token, value)
        node.text = text

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
