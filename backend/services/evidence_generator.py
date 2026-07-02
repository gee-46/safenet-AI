"""
SafeNet AI – Evidence Package Generator
------------------------------------------
Generates court-admissible PDF evidence packages for law enforcement.
Includes: case summary, timeline, fraud network map, regulatory citations.
"""
from __future__ import annotations

import io
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# Lazy import ReportLab
_reportlab = None


def _lazy_rl():
    global _reportlab
    if _reportlab is None:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, PageBreak,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        _reportlab = {
            "colors": colors, "A4": A4, "getSampleStyleSheet": getSampleStyleSheet,
            "ParagraphStyle": ParagraphStyle, "mm": mm,
            "SimpleDocTemplate": SimpleDocTemplate, "Paragraph": Paragraph,
            "Spacer": Spacer, "Table": Table, "TableStyle": TableStyle,
            "HRFlowable": HRFlowable, "PageBreak": PageBreak,
            "TA_CENTER": TA_CENTER, "TA_LEFT": TA_LEFT, "TA_RIGHT": TA_RIGHT,
        }
    return _reportlab


# ── Regulatory References ─────────────────────────────────────────

CRPC_SECTIONS = {
    "digital_arrest": ["Section 66D IT Act", "Section 419 IPC", "Section 420 IPC"],
    "counterfeit": ["Section 489A IPC", "Section 489B IPC", "Section 489C IPC"],
    "fraud_network": ["Section 120B IPC", "Section 66 IT Act", "PMLA 2002"],
    "kyc_update": ["Section 66C IT Act", "Section 66D IT Act", "Section 420 IPC"],
    "investment": ["Section 420 IPC", "SEBI Act 1992 Section 11", "PMLA 2002"],
    "loan_fraud": ["Section 420 IPC", "Section 415 IPC"],
    "default": ["Section 66 IT Act", "Section 420 IPC"],
}

IT_ACT_SECTIONS = {
    "digital_arrest": ["Section 66D - Cheating by personation", "Section 67 - Obscene content"],
    "counterfeit": ["Section 43 - Damage to computer", "Section 66 - Computer related offences"],
    "fraud_network": ["Section 66C - Identity theft", "Section 66D - Cheating by personation"],
    "default": ["Section 66 - Computer related offences"],
}


class EvidencePackageGenerator:
    """Generates professional PDF evidence packages."""

    BRAND_BLUE = (0.09, 0.27, 0.50)       # SafeNet dark blue
    BRAND_RED = (0.85, 0.15, 0.15)         # Alert red
    BRAND_GREY = (0.95, 0.95, 0.97)        # Light grey background

    def __init__(self):
        self._package_store: Dict[str, bytes] = {}   # In-memory for demo; use S3 in production

    def _get_styles(self, rl: Dict):
        """Create consistent paragraph styles."""
        base = rl["getSampleStyleSheet"]()
        colors = rl["colors"]
        PS = rl["ParagraphStyle"]

        return {
            "title": PS("Title", parent=base["Title"],
                        fontSize=20, textColor=colors.Color(*self.BRAND_BLUE),
                        spaceAfter=6),
            "subtitle": PS("Subtitle", parent=base["Normal"],
                           fontSize=11, textColor=colors.grey,
                           spaceAfter=4),
            "section_header": PS("SectionHeader", parent=base["Heading2"],
                                 fontSize=13, textColor=colors.Color(*self.BRAND_BLUE),
                                 spaceBefore=16, spaceAfter=6,
                                 borderPad=4),
            "body": PS("Body", parent=base["Normal"],
                       fontSize=10, leading=14, spaceAfter=4),
            "body_bold": PS("BodyBold", parent=base["Normal"],
                            fontSize=10, leading=14, fontName="Helvetica-Bold"),
            "warning": PS("Warning", parent=base["Normal"],
                          fontSize=10, textColor=colors.Color(*self.BRAND_RED),
                          fontName="Helvetica-Bold"),
            "small": PS("Small", parent=base["Normal"],
                        fontSize=8, textColor=colors.grey),
        }

    def _add_header_footer(self, canvas, doc, case_number: str):
        """Add page header/footer to every page."""
        rl = _lazy_rl()
        colors = rl["colors"]
        mm = rl["mm"]
        w, h = rl["A4"]

        canvas.saveState()

        # Header bar
        canvas.setFillColor(colors.Color(*self.BRAND_BLUE))
        canvas.rect(0, h - 25*mm, w, 20*mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(15*mm, h - 14*mm, "🔒 SafeNet AI — CONFIDENTIAL EVIDENCE PACKAGE")
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(w - 15*mm, h - 14*mm, f"Case: {case_number}")

        # Footer
        canvas.setFillColor(colors.Color(0.9, 0.9, 0.9))
        canvas.rect(0, 0, w, 12*mm, fill=1, stroke=0)
        canvas.setFillColor(colors.grey)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(15*mm, 4*mm,
            "RESTRICTED — For Law Enforcement Use Only | Generated by SafeNet AI | NOT for public disclosure")
        canvas.drawRightString(w - 15*mm, 4*mm, f"Page {doc.page}")

        canvas.restoreState()

    def generate(
        self,
        case_number: str,
        scam_reports: List[Dict],
        fraud_graph: Optional[Dict],
        case_summary: Dict,
        include_regulatory: bool = True,
    ) -> bytes:
        """
        Generate the evidence package PDF.

        Returns raw PDF bytes.
        """
        rl = _lazy_rl()
        colors = rl["colors"]
        mm = rl["mm"]
        buffer = io.BytesIO()

        doc = rl["SimpleDocTemplate"](
            buffer,
            pagesize=rl["A4"],
            rightMargin=15*mm, leftMargin=15*mm,
            topMargin=30*mm, bottomMargin=18*mm,
        )

        styles = self._get_styles(rl)
        story = []

        # ── Cover Page ───────────────────────────────────────────
        story.append(rl["Spacer"](1, 30*mm))
        story.append(rl["Paragraph"](
            "DIGITAL CRIME EVIDENCE PACKAGE", styles["title"]
        ))
        story.append(rl["Paragraph"](
            f"Case Number: <b>{case_number}</b>", styles["subtitle"]
        ))
        story.append(rl["Paragraph"](
            f"Generated: {datetime.utcnow().strftime('%d %B %Y, %H:%M UTC')}", styles["small"]
        ))
        story.append(rl["Paragraph"](
            "Prepared by SafeNet AI Fraud Intelligence Platform", styles["small"]
        ))
        story.append(rl["Spacer"](1, 10*mm))
        story.append(rl["HRFlowable"](width="100%", thickness=2,
                                       color=colors.Color(*self.BRAND_BLUE)))
        story.append(rl["Spacer"](1, 10*mm))

        # Severity badge
        severity = case_summary.get("severity", "HIGH")
        story.append(rl["Paragraph"](
            f"⚠️ SEVERITY: {severity.upper()} | "
            f"Estimated Victims: {case_summary.get('estimated_victims', 'Unknown')} | "
            f"Estimated Loss: ₹{case_summary.get('estimated_loss_inr', 0):,.0f}",
            styles["warning"]
        ))

        story.append(rl["PageBreak"]())

        # ── Section 1: Executive Summary ─────────────────────────
        story.append(rl["Paragraph"]("1. EXECUTIVE SUMMARY", styles["section_header"]))
        story.append(rl["Paragraph"](
            case_summary.get("description",
                "This package contains AI-generated intelligence on a cybercrime network. "
                "All findings are based on digital evidence and should be verified by investigating officers."
            ),
            styles["body"]
        ))
        story.append(rl["Spacer"](1, 4*mm))

        # Summary stats table
        stats_data = [
            ["Field", "Value"],
            ["Fraud Type", case_summary.get("fraud_type", "Digital Arrest / Cybercrime").title()],
            ["Total Reports", str(len(scam_reports))],
            ["States Involved", ", ".join(case_summary.get("states_involved", []) or ["Unknown"])],
            ["Confidence Level", f"{case_summary.get('avg_confidence', 0.85)*100:.0f}%"],
            ["Status", case_summary.get("status", "Under Investigation")],
        ]
        story.append(_make_table(rl, stats_data, colors, self.BRAND_BLUE, self.BRAND_GREY))
        story.append(rl["Spacer"](1, 6*mm))

        # ── Section 2: Incident Timeline ─────────────────────────
        story.append(rl["Paragraph"]("2. INCIDENT TIMELINE", styles["section_header"]))
        story.append(rl["Paragraph"](
            f"Total incidents analysed: {len(scam_reports)}. Showing most recent {min(len(scam_reports), 20)}.",
            styles["body"]
        ))
        story.append(rl["Spacer"](1, 3*mm))

        if scam_reports:
            timeline_data = [["#", "Date", "Caller No.", "Type", "Confidence", "City"]]
            for i, report in enumerate(scam_reports[:20], 1):
                ts = report.get("created_at", "")
                if isinstance(ts, datetime):
                    ts = ts.strftime("%d/%m/%Y %H:%M")
                timeline_data.append([
                    str(i),
                    str(ts)[:16],
                    _mask_number(report.get("caller_number", "")),
                    (report.get("scam_type") or "").replace("_", " ").title(),
                    f"{(report.get('confidence_score') or 0)*100:.0f}%",
                    report.get("city") or "Unknown",
                ])
            story.append(_make_table(rl, timeline_data, colors, self.BRAND_BLUE, self.BRAND_GREY))
        else:
            story.append(rl["Paragraph"]("No incident records available.", styles["body"]))

        story.append(rl["Spacer"](1, 6*mm))

        # ── Section 3: Fraud Network Summary ─────────────────────
        if fraud_graph:
            story.append(rl["Paragraph"]("3. FRAUD NETWORK ANALYSIS", styles["section_header"]))
            story.append(rl["Paragraph"](
                f"The fraud graph contains {fraud_graph.get('fraud_network_size', 0)} entities "
                f"with {len(fraud_graph.get('edges', []))} confirmed connections. "
                f"Risk score: {fraud_graph.get('risk_score', 0)*100:.0f}%.",
                styles["body"]
            ))

            # Top high-risk nodes
            nodes = sorted(
                fraud_graph.get("nodes", []),
                key=lambda x: x.get("risk_score", 0),
                reverse=True,
            )[:10]

            if nodes:
                node_data = [["Entity", "Type", "Risk Score", "Fraud Count"]]
                for node in nodes:
                    node_data.append([
                        _mask_entity(node.get("id", "")),
                        (node.get("type") or "").replace("_", " ").title(),
                        f"{node.get('risk_score', 0)*100:.0f}%",
                        str(node.get("fraud_count", 0)),
                    ])
                story.append(_make_table(rl, node_data, colors, self.BRAND_BLUE, self.BRAND_GREY))
            story.append(rl["Spacer"](1, 6*mm))

        # ── Section 4: Regulatory Citations ──────────────────────
        if include_regulatory:
            story.append(rl["Paragraph"]("4. APPLICABLE LEGAL PROVISIONS", styles["section_header"]))
            fraud_type = case_summary.get("fraud_type", "default")
            crpc = CRPC_SECTIONS.get(fraud_type, CRPC_SECTIONS["default"])
            it_act = IT_ACT_SECTIONS.get(fraud_type, IT_ACT_SECTIONS["default"])

            legal_data = [["Statute", "Section", "Applicability"]]
            for s in crpc:
                legal_data.append(["IPC / CrPC", s, "Direct application"])
            for s in it_act:
                legal_data.append(["IT Act 2000", s, "Cybercrime provision"])
            legal_data.append(["PMLA 2002", "Section 3", "Money laundering proceeds"])

            story.append(_make_table(rl, legal_data, colors, self.BRAND_BLUE, self.BRAND_GREY))
            story.append(rl["Spacer"](1, 4*mm))
            story.append(rl["Paragraph"](
                "Note: These provisions are AI-suggested references. The investigating officer and "
                "public prosecutor should verify applicability based on specific facts and jurisdiction.",
                styles["small"]
            ))

        # ── Section 5: Audit Trail ────────────────────────────────
        story.append(rl["Spacer"](1, 6*mm))
        story.append(rl["Paragraph"]("5. AI SYSTEM AUDIT TRAIL", styles["section_header"]))
        story.append(rl["Paragraph"](
            f"This package was generated by SafeNet AI v1.0.0 on "
            f"{datetime.utcnow().strftime('%d %B %Y at %H:%M UTC')}. "
            "All AI decisions are logged with input hashes and model versions for forensic auditability. "
            "The underlying models used: ScamCallClassifier v1.0.0 (DistilBERT ensemble), "
            "FraudGraphIntelligence v1.0.0 (Neo4j + Heuristic Scorer).",
            styles["body"]
        ))
        story.append(rl["Paragraph"](
            f"Package ID: {uuid.uuid4()} | Classification: RESTRICTED",
            styles["small"]
        ))

        # Build PDF
        doc.build(
            story,
            onFirstPage=lambda c, d: self._add_header_footer(c, d, case_number),
            onLaterPages=lambda c, d: self._add_header_footer(c, d, case_number),
        )
        return buffer.getvalue()

    def generate_and_store(self, **kwargs) -> Tuple[str, bytes]:
        """Generate, store in memory, return (package_id, pdf_bytes)."""
        pdf_bytes = self.generate(**kwargs)
        package_id = str(uuid.uuid4())
        self._package_store[package_id] = pdf_bytes
        return package_id, pdf_bytes

    def get_package(self, package_id: str) -> Optional[bytes]:
        return self._package_store.get(package_id)


# ── Helpers ───────────────────────────────────────────────────────

def _make_table(rl, data, colors, header_color, row_color):
    """Create a styled ReportLab table."""
    mm = rl["mm"]
    table = rl["Table"](data, repeatRows=1)
    style = rl["TableStyle"]([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(*header_color)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(*row_color)]),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("WORDWRAP", (0, 0), (-1, -1), True),
    ])
    table.setStyle(style)
    return table


def _mask_number(number: str) -> str:
    """Partially mask phone number for privacy in public-facing sections."""
    if len(number) >= 10:
        return number[:3] + "****" + number[-3:]
    return "****"


def _mask_entity(entity_id: str) -> str:
    """Partially mask entity ID."""
    if len(entity_id) > 8:
        return entity_id[:4] + "****" + entity_id[-4:]
    return entity_id[:2] + "****"


from typing import Tuple  # noqa: E402


# ── Module-level singleton ────────────────────────────────────────
_generator: Optional[EvidencePackageGenerator] = None


def get_evidence_generator() -> EvidencePackageGenerator:
    global _generator
    if _generator is None:
        _generator = EvidencePackageGenerator()
    return _generator
