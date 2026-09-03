
"""
AR Validation Report Generator

Consumes the structured payload returned by ar_validator.validate_ar_files()
and produces a professional PDF report.

Important design rule:
    - ar_validator.py owns all validation facts and numbers.
    - This module renders those facts into tables/charts.
    - Gemini is used ONLY for narrative prose.
    - Gemini is explicitly forbidden from generating numerical results.
    - If Gemini is unavailable, deterministic fallback text is used.

Environment variable:
    GEMINI_API_KEY

Recommended packages:
    pip install reportlab matplotlib google-genai pydantic
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Gemini imports are optional at import time so the report can still be
# generated with deterministic fallback text if the SDK is not installed.
try:
    from google import genai
    from google.genai import types
    from pydantic import BaseModel
except ImportError:
    genai = None
    types = None
    BaseModel = None


# ============================================================
# Configuration
# ============================================================

DEFAULT_MODEL = "gemini-3.5-flash"
DEFAULT_OUTPUT_DIR = Path("reports")


# ============================================================
# Gemini response schema
# ============================================================

if BaseModel is not None:

    class ReportNarrative(BaseModel):
        executive_summary: str
        record_count_explanation: str
        company_code_explanation: str
        sign_validation_explanation: str
        payment_terms_blank_explanation: str
        payment_terms_group_explanation: str
        conclusion: str


# ============================================================
# Utility functions
# ============================================================

def _escape(text: Any) -> str:
    """Escape text for ReportLab Paragraph markup."""
    if text is None:
        return ""

    value = str(text)
    value = value.replace("&", "&amp;")
    value = value.replace("<", "&lt;")
    value = value.replace(">", "&gt;")
    return value


def _format_number(value: Any, money: bool = False) -> str:
    """Format validator numbers for human-readable PDF output."""
    if value is None:
        return "—"

    if isinstance(value, float):
        if money:
            return f"{value:,.2f}"
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"

    if isinstance(value, int):
        return f"{value:,}"

    return _escape(value)


def _status_text(status: str) -> str:
    return str(status or "").upper()


def _status_label(status: str) -> str:
    status = _status_text(status)

    if status == "PASS":
        return "PASS"
    if status == "FAIL":
        return "FAIL"
    if status == "MAPPING_ERROR":
        return "MAPPING ERROR"

    return status or "UNKNOWN"


# ============================================================
# Gemini narrative generation
# ============================================================

def _build_llm_context(validation_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Give Gemini only the information required to explain the validations.

    Numerical values are deliberately removed from the LLM context.
    Python owns every number shown in the report.
    """
    checks = []

    for check in validation_payload.get("checks", []):
        check_context = {
            "check_name": check.get("check_name"),
            "status": check.get("status"),
            "message": check.get("message"),
        }

        # Payment-term grouping needs the group structure explained.
        if check.get("check_name") == "Payment Terms Group Count":
            check_context["groups"] = [
                {
                    "set": detail.get("label"),
                    "ecc_payment_terms": detail.get("ecc_terms", []),
                    "s4_payment_terms": detail.get("s4_terms", []),
                    "status": detail.get("status"),
                }
                for detail in check.get("details", [])
            ]

        checks.append(check_context)

    return {
        "process": validation_payload.get("process"),
        "overall_status": validation_payload.get("overall_status"),
        "checks": checks,
    }


def _fallback_narrative(validation_payload: Dict[str, Any]) -> Dict[str, str]:
    """Deterministic fallback if Gemini is unavailable."""
    status = validation_payload.get("overall_status", "UNKNOWN")

    if status == "PASS":
        executive = (
            "The Accounts Receivable migration validation completed successfully. "
            "All configured reconciliation checks passed based on the results "
            "returned by the validation engine."
        )
        conclusion = (
            "The validation results indicate that the configured reconciliation "
            "criteria were satisfied for the supplied ECC source and S/4 target files."
        )
    else:
        executive = (
            "The Accounts Receivable migration validation completed with one or "
            "more failed checks. The detailed sections below identify the affected "
            "validation areas and present the exact results returned by the "
            "validation engine."
        )
        conclusion = (
            "The validation did not fully pass. The failed validation sections "
            "should be reviewed before treating the migration output as reconciled."
        )

    return {
        "executive_summary": executive,
        "record_count_explanation": (
            "This validation compares the number of source ECC records with the "
            "number of target S/4 records. A matching record population indicates "
            "that the overall number of migrated records is consistent."
        ),
        "company_code_explanation": (
            "This validation compares the distribution of records by company code. "
            "Each ECC company code is evaluated against its configured S/4 company "
            "code mapping, and the corresponding record populations are compared."
        ),
        "sign_validation_explanation": (
            "This validation checks whether ECC debit and credit indicators are "
            "represented with the expected positive and negative amount signs in "
            "the S/4 WRBTR field."
        ),
        "payment_terms_blank_explanation": (
            "This validation checks whether blank payment terms in the ECC source "
            "are represented consistently by the configured no-payment-terms value "
            "in the S/4 output."
        ),
        "payment_terms_group_explanation": (
            "Payment terms are validated using configured groups. Each ECC payment "
            "term belongs to a group whose corresponding S/4 payment terms form "
            "the target group. Multiple ECC terms mapping to the same S/4 term "
            "remain together in the same group. The validator compares the total "
            "record count for each group rather than treating every mapping as a "
            "separate top-level validation."
        ),
        "conclusion": conclusion,
    }


def generate_narrative(
    validation_payload: Dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> Dict[str, str]:
    """
    Ask Gemini for narrative only.

    Gemini is prohibited from producing numbers. This means all numerical
    values in the final PDF come directly from the validator payload.
    """
    fallback = _fallback_narrative(validation_payload)

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or genai is None or BaseModel is None or types is None:
        return fallback

    context = _build_llm_context(validation_payload)

    prompt = f"""
You are the technical writer for an ECC to S/4 HANA Accounts Receivable
migration validation report.

The supplied JSON is the authoritative validation result.

STRICT RULES:
1. Do not calculate anything.
2. Do not generate, repeat, modify, round, or infer ANY numerical value.
3. Do not write record counts, amounts, differences, percentages, dates,
   or any other numbers.
4. Do not change PASS, FAIL, or MAPPING ERROR statuses.
5. Do not invent mappings or validation rules.
6. Do not claim a validation passed or failed unless the supplied JSON
   explicitly gives that status.
7. Explain methodology and meaning in professional technical language.
8. The Python application will insert all numbers and result tables separately.
9. Your output is narrative only.

Write these sections:
- executive_summary
- record_count_explanation
- company_code_explanation
- sign_validation_explanation
- payment_terms_blank_explanation
- payment_terms_group_explanation
- conclusion

The payment-term group explanation must specifically explain that:
- payment terms are grouped;
- each ECC term belongs to a configured group;
- the corresponding S/4 terms belong to the same logical group;
- multiple ECC terms mapping to one S/4 term remain together;
- group-level record counts are compared;
- the validation passes only when every configured group matches.

AUTHORITATIVE VALIDATION CONTEXT:
{context}
"""

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReportNarrative,
                temperature=0.2,
            ),
        )

        parsed = response.parsed

        if parsed is not None:
            return parsed.model_dump()

        # Some SDK versions expose JSON text instead of parsed output.
        if response.text:
            import json

            data = json.loads(response.text)
            required = {
                "executive_summary",
                "record_count_explanation",
                "company_code_explanation",
                "sign_validation_explanation",
                "payment_terms_blank_explanation",
                "payment_terms_group_explanation",
                "conclusion",
            }

            if required.issubset(data):
                return {key: str(data[key]) for key in required}

    except Exception as exc:
        print(f"Gemini narrative generation failed; using fallback text: {exc}")

    return fallback


# ============================================================
# Charts
# ============================================================

def create_comparison_chart(
    labels: List[str],
    ecc_values: List[float],
    s4_values: List[float],
    title: str,
    ylabel: str,
    output_path: Path,
) -> Path:
    """Create a grouped ECC vs S/4 comparison chart."""
    x = list(range(len(labels)))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 4.5))

    ecc_positions = [i - width / 2 for i in x]
    s4_positions = [i + width / 2 for i in x]

    ax.bar(ecc_positions, ecc_values, width, label="ECC")
    ax.bar(s4_positions, s4_values, width, label="S/4")

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(axis="y", alpha=0.2)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    return output_path


def create_company_code_chart(
    check: Dict[str, Any],
    output_path: Path,
) -> Optional[Path]:
    details = check.get("details", [])

    valid_details = [
        detail
        for detail in details
        if detail.get("right_count") is not None
    ]

    if not valid_details:
        return None

    labels = [detail["label"] for detail in valid_details]
    ecc_values = [detail["left_count"] for detail in valid_details]
    s4_values = [detail["right_count"] for detail in valid_details]

    return create_comparison_chart(
        labels=labels,
        ecc_values=ecc_values,
        s4_values=s4_values,
        title="Company Code Distribution — ECC vs S/4",
        ylabel="Record Count",
        output_path=output_path,
    )


def create_sign_chart(
    check: Dict[str, Any],
    output_path: Path,
) -> Optional[Path]:
    details = check.get("details", [])

    if not details:
        return None

    labels = [detail["label"] for detail in details]
    ecc_values = [detail["left_count"] for detail in details]
    s4_values = [abs(detail["right_count"]) for detail in details]

    return create_comparison_chart(
        labels=labels,
        ecc_values=ecc_values,
        s4_values=s4_values,
        title="Amount Sign Validation — ECC vs S/4",
        ylabel="Amount",
        output_path=output_path,
    )


def create_payment_terms_chart(
    check: Dict[str, Any],
    output_path: Path,
) -> Optional[Path]:
    details = check.get("details", [])

    if not details:
        return None

    labels = [detail["label"] for detail in details]
    ecc_values = [detail["left_count"] for detail in details]
    s4_values = [detail["right_count"] for detail in details]

    return create_comparison_chart(
        labels=labels,
        ecc_values=ecc_values,
        s4_values=s4_values,
        title="Payment Terms Group Validation — ECC vs S/4",
        ylabel="Record Count",
        output_path=output_path,
    )


# ============================================================
# PDF styles
# ============================================================

def _styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitleCustom",
            parent=styles["Title"],
            fontSize=21,
            leading=25,
            alignment=TA_CENTER,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SubtitleCustom",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            spaceAfter=18,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionHeadingCustom",
            parent=styles["Heading2"],
            fontSize=15,
            leading=19,
            spaceBefore=8,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SubHeadingCustom",
            parent=styles["Heading3"],
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["BodyText"],
            fontSize=9.5,
            leading=14,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallCustom",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="StatusPass",
            parent=styles["BodyText"],
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            spaceAfter=8,
        )
    )

    return styles


def _paragraph(text: Any, style) -> Paragraph:
    return Paragraph(_escape(text), style)


# ============================================================
# PDF table builders
# ============================================================

def _table_style() -> TableStyle:
    return TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9EEF5")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])


def build_simple_result_table(
    label: str,
    left_label: str,
    right_label: str,
    left_value: Any,
    right_value: Any,
    difference: Any,
    status: str,
    money: bool = False,
) -> Table:
    data = [
        [
            Paragraph("<b>Validation</b>", _styles()["SmallCustom"]),
            Paragraph("<b>ECC</b>", _styles()["SmallCustom"]),
            Paragraph("<b>S/4</b>", _styles()["SmallCustom"]),
            Paragraph("<b>Difference</b>", _styles()["SmallCustom"]),
            Paragraph("<b>Result</b>", _styles()["SmallCustom"]),
        ],
        [
            Paragraph(_escape(label), _styles()["SmallCustom"]),
            Paragraph(_format_number(left_value, money), _styles()["SmallCustom"]),
            Paragraph(_format_number(right_value, money), _styles()["SmallCustom"]),
            Paragraph(_format_number(difference, money), _styles()["SmallCustom"]),
            Paragraph(_status_label(status), _styles()["SmallCustom"]),
        ],
    ]

    table = Table(
        data,
        colWidths=[58 * mm, 30 * mm, 30 * mm, 30 * mm, 25 * mm],
        repeatRows=1,
    )
    table.setStyle(_table_style())
    return table


def build_company_code_table(check: Dict[str, Any]) -> Table:
    rows = [[
        "ECC Company Code",
        "S/4 Company Code",
        "ECC Records",
        "S/4 Records",
        "Difference",
        "Result",
    ]]

    for detail in check.get("details", []):
        rows.append([
            _escape(detail.get("ecc_code")),
            _escape(detail.get("s4_code")),
            _format_number(detail.get("left_count")),
            _format_number(detail.get("right_count")),
            _format_number(
                None
                if detail.get("right_count") is None
                else detail.get("left_count", 0) - detail.get("right_count", 0)
            ),
            _status_label(detail.get("status")),
        ])

    table = Table(
        rows,
        colWidths=[30 * mm, 30 * mm, 28 * mm, 28 * mm, 25 * mm, 25 * mm],
        repeatRows=1,
    )
    table.setStyle(_table_style())
    return table


def build_sign_table(check: Dict[str, Any]) -> Table:
    rows = [[
        "Category",
        "ECC Amount",
        "S/4 Amount",
        "Difference",
        "Result",
    ]]

    for detail in check.get("details", []):
        rows.append([
            _escape(detail.get("label")),
            _format_number(detail.get("left_count"), True),
            _format_number(abs(detail.get("right_count", 0)), True),
            _format_number(
                detail.get("left_count", 0) - abs(detail.get("right_count", 0)),
                True,
            ),
            _status_label(detail.get("status")),
        ])

    table = Table(
        rows,
        colWidths=[50 * mm, 35 * mm, 35 * mm, 30 * mm, 25 * mm],
        repeatRows=1,
    )
    table.setStyle(_table_style())
    return table


def build_payment_terms_table(check: Dict[str, Any]) -> Table:
    styles = _styles()

    rows = [[
        Paragraph("<b>Set</b>", styles["SmallCustom"]),
        Paragraph("<b>ECC Payment Terms</b>", styles["SmallCustom"]),
        Paragraph("<b>S/4 Payment Terms</b>", styles["SmallCustom"]),
        Paragraph("<b>ECC Count</b>", styles["SmallCustom"]),
        Paragraph("<b>S/4 Count</b>", styles["SmallCustom"]),
        Paragraph("<b>Difference</b>", styles["SmallCustom"]),
        Paragraph("<b>Result</b>", styles["SmallCustom"]),
    ]]

    for detail in check.get("details", []):
        ecc_terms = ", ".join(detail.get("ecc_terms", []))
        s4_terms = ", ".join(detail.get("s4_terms", []))

        rows.append([
            Paragraph(_escape(detail.get("label")), styles["SmallCustom"]),
            Paragraph(_escape(ecc_terms), styles["SmallCustom"]),
            Paragraph(_escape(s4_terms), styles["SmallCustom"]),
            Paragraph(_format_number(detail.get("left_count")), styles["SmallCustom"]),
            Paragraph(_format_number(detail.get("right_count")), styles["SmallCustom"]),
            Paragraph(
                _format_number(
                    detail.get("left_count", 0) - detail.get("right_count", 0)
                ),
                styles["SmallCustom"],
            ),
            Paragraph(_status_label(detail.get("status")), styles["SmallCustom"]),
        ])

    table = Table(
        rows,
        colWidths=[
            16 * mm,
            43 * mm,
            43 * mm,
            22 * mm,
            22 * mm,
            22 * mm,
            20 * mm,
        ],
        repeatRows=1,
    )
    table.setStyle(_table_style())
    return table


# ============================================================
# PDF helpers
# ============================================================

def _find_check(payload: Dict[str, Any], name: str) -> Dict[str, Any]:
    for check in payload.get("checks", []):
        if check.get("check_name") == name:
            return check
    return {}


def _status_box(status: str, styles) -> Table:
    status = _status_label(status)

    if status == "PASS":
        text = "<b>OVERALL RESULT: PASS</b>"
    elif status == "FAIL":
        text = "<b>OVERALL RESULT: FAIL</b>"
    else:
        text = f"<b>OVERALL RESULT: {_escape(status)}</b>"

    table = Table(
        [[Paragraph(text, styles["StatusPass"])]],
        colWidths=[170 * mm],
    )

    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    return table


def _add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(
        A4[0] / 2,
        8 * mm,
        f"AR Migration Validation Report  |  Page {doc.page}",
    )
    canvas.restoreState()


# ============================================================
# Main PDF generation
# ============================================================

def generate_ar_validation_report(
    validation_payload: Dict[str, Any],
    output_path: Optional[str | Path] = None,
    source_file_name: Optional[str] = None,
    target_file_name: Optional[str] = None,
    use_llm: bool = True,
    gemini_model: str = DEFAULT_MODEL,
) -> str:
    """
    Generate the AR migration validation PDF.

    Parameters
    ----------
    validation_payload:
        Exact dictionary returned by ar_validator.validate_ar_files().
    output_path:
        Destination PDF path. If omitted, reports/AR_Validation_Report.pdf
        is used.
    source_file_name:
        Optional source ECC filename displayed in the report.
    target_file_name:
        Optional S/4 target filename displayed in the report.
    use_llm:
        If False, deterministic narrative is used.
    gemini_model:
        Gemini model name.
    """

    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DEFAULT_OUTPUT_DIR / "AR_Validation_Report.pdf"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = _styles()

    if use_llm:
        narratives = generate_narrative(
            validation_payload,
            model=gemini_model,
        )
    else:
        narratives = _fallback_narrative(validation_payload)

    # --------------------------------------------------------
    # Generate charts
    # --------------------------------------------------------

    chart_dir = output_path.parent / f"{output_path.stem}_charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    company_chart = create_company_code_chart(
        _find_check(validation_payload, "Company Code Distribution"),
        chart_dir / "company_code_distribution.png",
    )

    sign_chart = create_sign_chart(
        _find_check(validation_payload, "Amount Sign Validation"),
        chart_dir / "amount_sign_validation.png",
    )

    payment_chart = create_payment_terms_chart(
        _find_check(validation_payload, "Payment Terms Group Count"),
        chart_dir / "payment_terms_groups.png",
    )

    # --------------------------------------------------------
    # PDF document
    # --------------------------------------------------------

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=15 * mm,
        title="AR Migration Validation Report",
        author="ECC to S/4 HANA Migration Validation",
    )

    story = []

    # ========================================================
    # Cover / Executive Summary
    # ========================================================

    story.append(
        Paragraph(
            "ECC → S/4 HANA",
            styles["ReportTitleCustom"],
        )
    )

    story.append(
        Paragraph(
            "Accounts Receivable Migration Validation Report",
            styles["ReportTitleCustom"],
        )
    )

    metadata = []

    if source_file_name:
        metadata.append(["ECC Source", source_file_name])

    if target_file_name:
        metadata.append(["S/4 Target", target_file_name])

    metadata.append([
        "Overall Status",
        validation_payload.get("overall_status", "UNKNOWN"),
    ])

    summary = validation_payload.get("summary", {})

    metadata.append([
        "Validation Checks",
        f"{summary.get('passed', 0)} passed / "
        f"{summary.get('failed', 0)} failed / "
        f"{summary.get('total_checks', 0)} total",
    ])

    meta_table = Table(
        metadata,
        colWidths=[45 * mm, 125 * mm],
    )
    meta_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E9EEF5")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(meta_table)
    story.append(Spacer(1, 12))
    story.append(_status_box(validation_payload.get("overall_status"), styles))
    story.append(Spacer(1, 14))

    story.append(
        Paragraph("Executive Summary", styles["SectionHeadingCustom"])
    )
    story.append(
        _paragraph(
            narratives["executive_summary"],
            styles["BodyCustom"],
        )
    )

    story.append(
        Paragraph(
            "Report Scope",
            styles["SubHeadingCustom"],
        )
    )

    story.append(
        _paragraph(
            "This report documents the validation checks performed by the "
            "Accounts Receivable migration validator. Numerical values, "
            "statuses, mappings, and reconciliation results shown in the "
            "report are taken directly from the validator payload.",
            styles["BodyCustom"],
        )
    )

    story.append(PageBreak())

    # ========================================================
    # Validation 1
    # ========================================================

    record_check = _find_check(
        validation_payload,
        "Total Record Count",
    )

    story.append(
        Paragraph(
            "1. Total Record Count Validation",
            styles["SectionHeadingCustom"],
        )
    )

    story.append(
        _paragraph(
            narratives["record_count_explanation"],
            styles["BodyCustom"],
        )
    )

    detail = record_check.get("details", [{}])[0]

    story.append(
        build_simple_result_table(
            label="Total Records",
            left_label="ECC",
            right_label="S/4",
            left_value=detail.get("left_count"),
            right_value=detail.get("right_count"),
            difference=(
                detail.get("left_count", 0)
                - detail.get("right_count", 0)
            ),
            status=detail.get("status"),
        )
    )

    story.append(Spacer(1, 8))

    story.append(
        _paragraph(
            record_check.get("message", ""),
            styles["BodyCustom"],
        )
    )

    story.append(PageBreak())

    # ========================================================
    # Validation 2
    # ========================================================

    company_check = _find_check(
        validation_payload,
        "Company Code Distribution",
    )

    story.append(
        Paragraph(
            "2. Company Code Distribution",
            styles["SectionHeadingCustom"],
        )
    )

    story.append(
        _paragraph(
            narratives["company_code_explanation"],
            styles["BodyCustom"],
        )
    )

    story.append(build_company_code_table(company_check))
    story.append(Spacer(1, 10))

    if company_chart and company_chart.exists():
        story.append(
            Image(
                str(company_chart),
                width=165 * mm,
                height=93 * mm,
            )
        )

    story.append(Spacer(1, 8))
    story.append(
        _paragraph(
            company_check.get("message", ""),
            styles["BodyCustom"],
        )
    )

    story.append(PageBreak())

    # ========================================================
    # Validation 3
    # ========================================================

    sign_check = _find_check(
        validation_payload,
        "Amount Sign Validation",
    )

    story.append(
        Paragraph(
            "3. Amount Sign Validation",
            styles["SectionHeadingCustom"],
        )
    )

    story.append(
        _paragraph(
            narratives["sign_validation_explanation"],
            styles["BodyCustom"],
        )
    )

    story.append(build_sign_table(sign_check))
    story.append(Spacer(1, 10))

    if sign_chart and sign_chart.exists():
        story.append(
            Image(
                str(sign_chart),
                width=165 * mm,
                height=93 * mm,
            )
        )

    story.append(Spacer(1, 8))
    story.append(
        _paragraph(
            sign_check.get("message", ""),
            styles["BodyCustom"],
        )
    )

    story.append(PageBreak())

    # ========================================================
    # Validation 4
    # ========================================================

    blank_check = _find_check(
        validation_payload,
        "Payment Terms Blank Count",
    )

    story.append(
        Paragraph(
            "4. Payment Terms Blank Count",
            styles["SectionHeadingCustom"],
        )
    )

    story.append(
        _paragraph(
            narratives["payment_terms_blank_explanation"],
            styles["BodyCustom"],
        )
    )

    blank_detail = blank_check.get("details", [{}])[0]

    story.append(
        build_simple_result_table(
            label="Blank / No Payment Terms",
            left_label="ECC",
            right_label="S/4",
            left_value=blank_detail.get("left_count"),
            right_value=blank_detail.get("right_count"),
            difference=(
                blank_detail.get("left_count", 0)
                - blank_detail.get("right_count", 0)
            ),
            status=blank_detail.get("status"),
        )
    )

    story.append(Spacer(1, 8))
    story.append(
        _paragraph(
            blank_check.get("message", ""),
            styles["BodyCustom"],
        )
    )

    story.append(PageBreak())

    # ========================================================
    # Validation 5
    # ========================================================

    payment_check = _find_check(
        validation_payload,
        "Payment Terms Group Count",
    )

    story.append(
        Paragraph(
            "5. Payment Terms Group Validation",
            styles["SectionHeadingCustom"],
        )
    )

    story.append(
        _paragraph(
            narratives["payment_terms_group_explanation"],
            styles["BodyCustom"],
        )
    )

    story.append(
        Paragraph(
            "Configured Payment-Term Sets",
            styles["SubHeadingCustom"],
        )
    )

    story.append(
        _paragraph(
            "The following table shows the exact ECC and S/4 payment-term "
            "membership used by the validator. These mappings are displayed "
            "from the validator payload and are not generated by the LLM.",
            styles["BodyCustom"],
        )
    )

    story.append(build_payment_terms_table(payment_check))
    story.append(Spacer(1, 10))

    if payment_chart and payment_chart.exists():
        story.append(
            Image(
                str(payment_chart),
                width=165 * mm,
                height=93 * mm,
            )
        )

    story.append(Spacer(1, 8))

    story.append(
        _paragraph(
            payment_check.get("message", ""),
            styles["BodyCustom"],
        )
    )

    # ========================================================
    # Final conclusion
    # ========================================================

    story.append(PageBreak())

    story.append(
        Paragraph(
            "Final Conclusion",
            styles["SectionHeadingCustom"],
        )
    )

    story.append(
        _paragraph(
            narratives["conclusion"],
            styles["BodyCustom"],
        )
    )

    story.append(Spacer(1, 10))

    # Deterministic final summary table.
    checks = validation_payload.get("checks", [])

    rows = [[
        "Validation",
        "Status",
    ]]

    for check in checks:
        rows.append([
            _escape(check.get("check_name")),
            _status_label(check.get("status")),
        ])

    final_table = Table(
        rows,
        colWidths=[125 * mm, 40 * mm],
        repeatRows=1,
    )
    final_table.setStyle(_table_style())

    story.append(final_table)

    doc.build(
        story,
        onFirstPage=_add_page_number,
        onLaterPages=_add_page_number,
    )

    return str(output_path)


# ============================================================
# Example standalone usage
# ============================================================

if __name__ == "__main__":
    """
    This block is intentionally minimal.

    In the real application, import this module and call:

        validation_result = validate_ar_files(...)
        pdf_path = generate_ar_validation_report(
            validation_result,
            source_file_name="BSID.xlsx",
            target_file_name="AR_Data_Load_filled.xlsx",
        )
    """

    import json
    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: python report_generator.py validation_payload.json"
        )
        raise SystemExit(1)

    payload_path = Path(sys.argv[1])

    with payload_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    path = generate_ar_validation_report(payload)
    print(f"Report created: {path}")
