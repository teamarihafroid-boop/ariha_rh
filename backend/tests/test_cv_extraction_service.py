from __future__ import annotations

import io

import docx
import pytest

from app.services import cv_extraction_service
from app.services.cv_extraction_service import CvExtractionError, CvFields


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeModels:
    def __init__(self, response_text: str):
        self._response_text = response_text
        self.last_contents = None

    def generate_content(self, *, model, contents, config):
        self.last_contents = contents
        return _FakeResponse(self._response_text)


class _FakeClient:
    def __init__(self, response_text: str):
        self.models = _FakeModels(response_text)


def _use_fake_client(monkeypatch, response_text: str) -> _FakeClient:
    fake_client = _FakeClient(response_text)
    monkeypatch.setattr(cv_extraction_service.genai, "Client", lambda api_key: fake_client)
    return fake_client


def _make_docx_bytes(text: str) -> bytes:
    document = docx.Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_extract_fields_raises_without_api_key(monkeypatch):
    settings = cv_extraction_service.get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", None)

    with pytest.raises(CvExtractionError):
        cv_extraction_service.extract_fields(b"%PDF-fake", "application/pdf", "cv.pdf")


def test_extract_fields_sends_pdf_bytes_natively(monkeypatch):
    settings = cv_extraction_service.get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    fake_client = _use_fake_client(
        monkeypatch, '{"nom_complet": "Karim Idrissi", "email": "karim@example.com"}'
    )

    result = cv_extraction_service.extract_fields(b"%PDF-fake", "application/pdf", "cv.pdf")

    assert result.nom_complet == "Karim Idrissi"
    assert result.email == "karim@example.com"
    assert result.telephone is None
    # The PDF part is sent as raw bytes, not extracted text.
    parts = fake_client.models.last_contents
    assert any(hasattr(p, "inline_data") for p in parts if not isinstance(p, str))


def test_extract_fields_extracts_docx_text(monkeypatch):
    settings = cv_extraction_service.get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    fake_client = _use_fake_client(monkeypatch, '{"nom_complet": "Nadia Chraibi"}')

    docx_bytes = _make_docx_bytes("Nadia Chraibi — ingénieure")
    result = cv_extraction_service.extract_fields(
        docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "cv.docx",
    )

    assert result.nom_complet == "Nadia Chraibi"
    contents = fake_client.models.last_contents
    assert any(isinstance(p, str) and "Nadia Chraibi" in p for p in contents)


def test_extract_fields_rejects_unsupported_type(monkeypatch):
    settings = cv_extraction_service.get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")

    with pytest.raises(CvExtractionError):
        cv_extraction_service.extract_fields(b"\x89PNG...", "image/png", "photo.png")


def test_extract_fields_degrades_to_empty_on_malformed_json(monkeypatch):
    settings = cv_extraction_service.get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    _use_fake_client(monkeypatch, "not valid json at all")

    result = cv_extraction_service.extract_fields(b"%PDF-fake", "application/pdf", "cv.pdf")

    assert result == CvFields()
