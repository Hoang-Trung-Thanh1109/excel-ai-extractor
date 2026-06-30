"""Gemini integration and JSON workbook spec generation."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class AIResult:
    workbook_title: str
    sheets: list[dict[str, Any]]


class AIEngine:
    def __init__(self, api_key: str | None, model: str = "gemini-2.5-flash", logger=None) -> None:
        self.api_key = (api_key or "").strip()
        self.model = model.strip() or "gemini-2.5-flash"
        self.logger = logger

    def generate_workbook_spec(self, user_prompt: str, document_context: str = "") -> AIResult:
        prompt = self._build_prompt(user_prompt=user_prompt, document_context=document_context)
        raw_text = self._call_gemini(prompt)
        spec = self._parse_json(raw_text)
        return AIResult(
            workbook_title=str(spec.get("workbook_title") or "Excel AI Extractor"),
            sheets=self._normalize_sheets(spec.get("sheets")),
        )

    def _call_gemini(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("Vui long thay GEMINI_API_KEY trong ui.py bang API key that.")

        if self.logger:
            self.logger("Dang goi Gemini...")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_text = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"Gemini tra loi HTTP {exc.code}: {error_text or exc.reason}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Khong the goi Gemini: {exc}") from exc

        data = json.loads(body)
        candidates = data.get("candidates") or []
        for candidate in candidates:
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            for part in parts:
                text = part.get("text")
                if text:
                    return str(text).strip()

        text = data.get("text")
        if text:
            return str(text).strip()

        raise RuntimeError("Gemini khong tra ve noi dung hop le.")

    def _build_prompt(self, user_prompt: str, document_context: str) -> str:
        user_prompt = (user_prompt or "").strip()
        document_context = (document_context or "").strip()

        if not user_prompt and document_context:
            user_prompt = (
                "Doc tai lieu duoc cung cap va tao bang Excel phu hop. "
                "Neu la tai lieu to chuc/hanh chinh, hay chi tiet hoa thanh cac cot co y nghia."
            )
        elif not user_prompt:
            user_prompt = (
                "Tao mot bang Excel huu ich tu de bai nay. Neu can, hay sinh du lieu mau logic va thuc te."
            )

        schema_example = {
            "workbook_title": "Ten workbook",
            "sheets": [
                {
                    "name": "Sheet1",
                    "headers": ["Cot 1", "Cot 2"],
                    "rows": [
                        {"Cot 1": "Gia tri 1", "Cot 2": "Gia tri 2"},
                    ],
                }
            ],
        }

        document_block = document_context[:12000] if document_context else "(khong co tai lieu dinh kem)"

        return f"""
Ban la mot AI chuyen tao du lieu chuan cho Excel.
Chi duoc tra ve JSON hop le. Khong markdown. Khong giai thich. Khong code fence.

Yeu cau:
- Phai tra ve dung 1 object JSON.
- Danh sach sheet nam trong key "sheets".
- Moi sheet co keys: "name", "headers", "rows".
- "headers" la mang ten cot.
- "rows" la mang cac object, moi object co khoa trung voi headers.
- Neu du lieu thieu, dung chuoi rong "".
- Neu nguoi dung yeu cau sinh du lieu, tao du lieu thuc te, hop ly va nhat quan.
- Neu co tai lieu, chi dua vao tai lieu do va yeu cau cua nguoi dung.
- Neu can nhieu sheet, hay tao nhieu sheet.
- Ten sheet phai ngan gon, khong co ky tu cam trong Excel.

Schema mau:
{json.dumps(schema_example, ensure_ascii=False)}

Yeu cau nguoi dung:
{user_prompt}

Noi dung tai lieu:
{document_block}
""".strip()

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = self._strip_code_fences((text or "").strip())
        candidates = [cleaned]

        if cleaned != text:
            candidates.append(text.strip())

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        extracted = self._extract_json_object(cleaned)
        if extracted:
            try:
                parsed = json.loads(extracted)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        raise ValueError(
            "Khong the phan tich JSON tu Gemini. Hay thu lai voi prompt ro hon."
        )

    def _strip_code_fences(self, text: str) -> str:
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def _extract_json_object(self, text: str) -> str | None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return text[start : end + 1]

    def _normalize_sheets(self, sheets: Any) -> list[dict[str, Any]]:
        if not isinstance(sheets, list) or not sheets:
            return [
                {
                    "name": "Sheet1",
                    "headers": ["Noi dung"],
                    "rows": [{"Noi dung": "Khong co du lieu"}],
                }
            ]

        normalized: list[dict[str, Any]] = []
        for index, sheet in enumerate(sheets, start=1):
            if not isinstance(sheet, dict):
                continue

            name = str(sheet.get("name") or f"Sheet{index}")
            rows = sheet.get("rows") or []
            headers = self._resolve_headers(sheet.get("headers"), rows)
            normalized_rows = self._normalize_rows(rows, headers)

            if not normalized_rows:
                normalized_rows = [{header: "" for header in headers}]

            normalized.append(
                {
                    "name": name,
                    "headers": headers,
                    "rows": normalized_rows,
                }
            )

        if not normalized:
            return [
                {
                    "name": "Sheet1",
                    "headers": ["Noi dung"],
                    "rows": [{"Noi dung": "Khong co du lieu"}],
                }
            ]
        return normalized

    def _resolve_headers(self, headers: Any, rows: Any) -> list[str]:
        if isinstance(headers, list) and headers:
            resolved = [str(item).strip() for item in headers if str(item).strip()]
            if resolved:
                return resolved

        if isinstance(rows, list) and rows:
            first = rows[0]
            if isinstance(first, dict):
                keys: list[str] = []
                for row in rows:
                    if isinstance(row, dict):
                        for key in row.keys():
                            key_str = str(key).strip()
                            if key_str and key_str not in keys:
                                keys.append(key_str)
                if keys:
                    return keys
            if isinstance(first, list):
                return [f"Column {index}" for index in range(1, len(first) + 1)]

        return ["Column 1"]

    def _normalize_rows(self, rows: Any, headers: list[str]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        if not isinstance(rows, list):
            return normalized

        for row in rows:
            if isinstance(row, dict):
                normalized.append({header: row.get(header, "") for header in headers})
            elif isinstance(row, list):
                mapped = {header: row[i] if i < len(row) else "" for i, header in enumerate(headers)}
                normalized.append(mapped)
            else:
                normalized.append({headers[0]: row if row is not None else ""})
        return normalized
