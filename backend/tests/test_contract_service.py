from __future__ import annotations

from datetime import date
from decimal import Decimal

import docx
from docx.oxml.ns import qn

from app.services import contract_service


class _Position:
    def __init__(self, intitule: str) -> None:
        self.intitule = intitule


class _Employee:
    def __init__(self, **kw) -> None:
        self.nom = kw.get("nom", "")
        self.prenom = kw.get("prenom", "")
        self.full_name = f"{self.prenom} {self.nom}"
        self.date_naissance = kw.get("date_naissance")
        self.lieu_naissance = kw.get("lieu_naissance")
        self.cin = kw.get("cin")
        self.adresse = kw.get("adresse")
        self.position = kw.get("position")
        self.date_embauche = kw.get("date_embauche")
        self.salaire_net = kw.get("salaire_net")


def _extract_text(docx_bytes: bytes) -> str:
    import io

    document = docx.Document(io.BytesIO(docx_bytes))
    parts = [p.text for p in document.paragraphs]
    parts += [t.text for t in document.element.body.iter(qn("w:t")) if t.text]
    return "\n".join(parts)


def test_render_cdi_contract_fills_every_placeholder():
    employee = _Employee(
        nom="Amrani",
        prenom="Leila",
        date_naissance=date(1990, 3, 12),
        lieu_naissance="Marrakech",
        cin="BE123456",
        adresse="12 Rue Ibn Sina, Marrakech",
        position=_Position("Responsable RH"),
        date_embauche=date(2026, 9, 20),
        salaire_net=Decimal("6500.00"),
    )

    text = _extract_text(contract_service.render_cdi_contract(employee))

    assert "@@" not in text
    assert "Amrani" in text
    assert "Leila" in text
    assert "12 mars 1990" in text
    assert "Marrakech" in text
    assert "BE123456" in text
    assert "12 Rue Ibn Sina" in text
    assert "Responsable RH" in text
    assert "20 septembre 2026" in text
    assert "6 500,00" in text
    assert "Six mille cinq cents" in text
    # Both signature-block copies got the employee's name.
    assert text.count("M Leila Amrani") == 2
    # The company's own signature block is legal boilerplate — untouched.
    assert text.count("HICHAM LAAMIRI") == 2


def test_render_cdi_contract_handles_missing_optional_fields():
    """A freshly hired employee often has salaire/CIN/adresse still blank —
    the contract should render with empty blanks rather than crashing."""
    employee = _Employee(nom="Doe", prenom="Jane")

    text = _extract_text(contract_service.render_cdi_contract(employee))

    assert "@@" not in text
    assert "Doe" in text
    assert "Jane" in text


def test_format_montant_lettres_includes_centimes_when_present():
    assert contract_service._format_montant_lettres(Decimal("4500.00")) == "Quatre mille cinq cents"
    assert (
        contract_service._format_montant_lettres(Decimal("4500.50"))
        == "Quatre mille cinq cents et cinquante centimes"
    )
