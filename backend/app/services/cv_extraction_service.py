from __future__ import annotations

import io
import json
from typing import Any

import docx
from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import get_settings

_EXTRACTION_PROMPT = (
    "You are extracting structured fields from a job candidate's CV/resume for an HR system. "
    "Extract only what is explicitly present in the document — never invent or infer a value "
    "that isn't there. Leave a field null if it isn't clearly stated. Respond with JSON matching "
    "the requested schema only, no extra commentary."
)


class CvExtractionError(ValueError):
    pass


class CvFields(BaseModel):
    """Mirrors the relevant CandidateCreate fields exactly, so the result maps
    straight onto the candidate form with no translation layer. Every field is
    a suggestion the recruiter can edit or discard — never authoritative."""

    nom_complet: str | None = None
    telephone: str | None = None
    email: str | None = None
    ville: str | None = None
    experience_resume: str | None = None
    competences: str | None = None
    diplomes: str | None = None
    langues: str | None = None


def _extract_docx_text(content: bytes) -> str:
    document = docx.Document(io.BytesIO(content))
    return "\n".join(p.text for p in document.paragraphs if p.text.strip())


def _build_parts(content: bytes, content_type: str, filename: str) -> list[Any]:
    name = filename.lower()
    if content_type == "application/pdf" or name.endswith(".pdf"):
        return [types.Part.from_bytes(data=content, mime_type="application/pdf")]
    if name.endswith(".docx"):
        text = _extract_docx_text(content)
        return [text]
    if content_type.startswith("text/") or name.endswith(".txt"):
        return [content.decode("utf-8", errors="ignore")]
    raise CvExtractionError("Format non supporté pour l'extraction — utilisez un PDF, DOCX ou TXT.")


def extract_fields(content: bytes, content_type: str, filename: str) -> CvFields:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise CvExtractionError(
            "Extraction indisponible — clé API Gemini non configurée (GEMINI_API_KEY)."
        )

    parts = _build_parts(content, content_type, filename)

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[_EXTRACTION_PROMPT, *parts],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CvFields,
            ),
        )
    except CvExtractionError:
        raise
    except Exception as exc:
        # Any SDK/transport failure (auth, quota, network) becomes a clean 503.
        raise CvExtractionError(f"Échec de l'appel à l'API d'extraction : {exc}") from exc

    try:
        data = json.loads(response.text)
        return CvFields.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        # A bad/unparsable AI response (incl. pydantic ValidationError, a
        # ValueError subclass) degrades to "nothing found," not a 500.
        return CvFields()
