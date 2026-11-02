import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


def generate_assessment_pdf(session, result):
    """
    Generate a professional clinical PDF assessment report using ReportLab.
    Adheres strictly to clean typography and zero em-dashes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=6,
    )

    label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#64748b'),
    )

    value_style = ParagraphStyle(
        'MetaValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a'),
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#ffffff'),
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1e293b'),
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1e293b'),
    )

    story = []

    # 1. Header Banner
    org_name = session.clinician.organization or 'Cognitive Health Center'
    clinician_name = session.clinician.display_name or session.clinician.user.get_full_name() or 'Clinician'

    header_table_data = [
        [
            Paragraph("VISUOSPATIAL ASSESSMENT REPORT", title_style),
            Paragraph(f"<b>{org_name}</b><br/>Clinician: {clinician_name}", subtitle_style),
        ]
    ]
    header_table = Table(header_table_data, colWidths=[360, 180])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=14))

    # 2. Patient & Assessment Information Grid
    comp_date_str = session.completed_at.strftime("%B %d, %Y at %I:%M %p") if session.completed_at else 'In Progress'
    duration_sec = round(result.completion_time_ms / 1000.0, 1)
    duration_str = f"{int(duration_sec // 60)}m {int(duration_sec % 60):02d}s"

    meta_data = [
        [
            Paragraph("PATIENT CODE", label_style),
            Paragraph("PARTICIPANT ID", label_style),
            Paragraph("AGE BRACKET", label_style),
            Paragraph("ASSESSMENT DATE", label_style),
        ],
        [
            Paragraph(f"<b>{session.patient_code}</b>", value_style),
            Paragraph(session.participant_id or session.patient_code, value_style),
            Paragraph(session.age_bracket or "Not specified", value_style),
            Paragraph(comp_date_str, value_style),
        ],
        [
            Paragraph("DIFFICULTY LEVEL", label_style),
            Paragraph("LANGUAGE", label_style),
            Paragraph("AUDIO GUIDANCE", label_style),
            Paragraph("TOTAL TEST DURATION", label_style),
        ],
        [
            Paragraph(session.difficulty, value_style),
            Paragraph(session.language, value_style),
            Paragraph(session.audio_voice, value_style),
            Paragraph(duration_str, value_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[135, 135, 135, 135])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('BOTTOMPADDING', (0, 2), (-1, 2), 2),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 3. Key Clinical Metrics Summary
    story.append(Paragraph("Executive Performance Metrics", section_heading))

    acc_val = f"{result.accuracy_percent:.1f}%"
    avg_lat = f"{result.avg_latency_ms / 1000.0:.2f}s"
    fast_lat = f"{result.fastest_latency_ms / 1000.0:.2f}s"
    slow_lat = f"{result.slowest_latency_ms / 1000.0:.2f}s"
    error_rate = f"{(result.mistakes / result.total_attempts * 100):.1f}%" if result.total_attempts > 0 else "0.0%"

    metrics_data = [
        [
            Paragraph("<b>Overall Accuracy</b>", label_style),
            Paragraph("<b>Correct Pairs</b>", label_style),
            Paragraph("<b>Total Attempts</b>", label_style),
            Paragraph("<b>Mistakes</b>", label_style),
        ],
        [
            Paragraph(f"<font size=14 color='#059669'><b>{acc_val}</b></font>", value_style),
            Paragraph(f"<font size=14 color='#2563eb'><b>{result.completed_pairs}</b></font>", value_style),
            Paragraph(f"<font size=14 color='#1e293b'><b>{result.total_attempts}</b></font>", value_style),
            Paragraph(f"<font size=14 color='#dc2626'><b>{result.mistakes}</b></font><br/><font size=7 color='#64748b'>({error_rate})</font>", value_style),
        ],
        [
            Paragraph("<b>Avg. Response Time</b>", label_style),
            Paragraph("<b>Fastest Response</b>", label_style),
            Paragraph("<b>Slowest Response</b>", label_style),
            Paragraph("<b>Completion Status</b>", label_style),
        ],
        [
            Paragraph(f"<font size=13 color='#0284c7'><b>{avg_lat}</b></font>", value_style),
            Paragraph(f"<font size=13 color='#4f46e5'><b>{fast_lat}</b></font>", value_style),
            Paragraph(f"<font size=13 color='#d97706'><b>{slow_lat}</b></font>", value_style),
            Paragraph(f"<font size=13 color='#059669'><b>{session.status}</b></font>", value_style),
        ],
    ]
    metrics_table = Table(metrics_data, colWidths=[135, 135, 135, 135])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ffffff')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#f8fafc')),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 14))

    # 4. Round-by-Round Detailed Breakdown
    story.append(Paragraph("Performance by Assessment Round", section_heading))

    rounds = session.rounds.prefetch_related('attempts').all().order_by('round_number')
    rounds_table_data = [
        [
            Paragraph("Round", table_header_style),
            Paragraph("Description", table_header_style),
            Paragraph("Pairs / Cards", table_header_style),
            Paragraph("Correct", table_header_style),
            Paragraph("Mistakes", table_header_style),
            Paragraph("Accuracy", table_header_style),
            Paragraph("Avg. Latency", table_header_style),
        ]
    ]

    for r in rounds:
        round_attempts = list(r.attempts.all().order_by('attempt_number'))
        r_total = len(round_attempts)
        r_correct = sum(1 for a in round_attempts if a.is_correct)
        r_mistakes = r_total - r_correct
        r_latencies = [a.response_latency_ms for a in round_attempts]
        r_avg_lat = (sum(r_latencies) / r_total / 1000.0) if r_total > 0 else 0.0
        r_acc = (r_correct / r_total * 100.0) if r_total > 0 else 0.0

        if r.is_practice:
            desc = "Practice (Not Scored)"
            round_label = f"Round {r.round_number} (Practice)"
            acc_str = f"{r_acc:.1f}% (Practice)"
        else:
            if r.mode == 'shape_direction':
                desc = "Shape + Directional Matching"
            elif r.mode == 'complex_matching':
                desc = "Complex Multi-Attribute Matching"
            else:
                desc = "Standard Shape Matching"
            round_label = f"Round {r.round_number}"
            acc_str = f"{r_acc:.1f}%"

        rounds_table_data.append([
            Paragraph(round_label, table_cell_bold),
            Paragraph(desc, table_cell_style),
            Paragraph(f"{r.pair_count} pairs ({r.card_count} cards)", table_cell_style),
            Paragraph(str(r_correct), table_cell_style),
            Paragraph(str(r_mistakes), table_cell_style),
            Paragraph(acc_str, table_cell_bold),
            Paragraph(f"{r_avg_lat:.2f}s", table_cell_style),
        ])

    rounds_table = Table(rounds_table_data, colWidths=[80, 150, 95, 45, 50, 60, 60])
    rounds_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (3, 1), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
    ]))
    story.append(rounds_table)
    story.append(Spacer(1, 14))

    # 5. Common Error Patterns and Missed Shapes
    shape_errors = result.level_summary_json.get('shape_errors', {})
    if shape_errors:
        story.append(Paragraph("Common Error Patterns by Visual Stimulus", section_heading))
        total_err_count = sum(shape_errors.values())
        err_data = [
            [
                Paragraph("Visual Shape / Attribute", table_header_style),
                Paragraph("Incorrect Selections", table_header_style),
                Paragraph("Error Distribution", table_header_style),
            ]
        ]
        for shape_name, count in sorted(shape_errors.items(), key=lambda x: x[1], reverse=True):
            pct_str = f"{(count / total_err_count * 100):.1f}%" if total_err_count > 0 else "0.0%"
            err_data.append([
                Paragraph(shape_name, table_cell_style),
                Paragraph(str(count), table_cell_bold),
                Paragraph(pct_str, table_cell_style),
            ])

        err_table = Table(err_data, colWidths=[240, 150, 150])
        err_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#475569')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ]))
        story.append(err_table)
        story.append(Spacer(1, 14))

    # 6. Clinician Notes & Recommendations
    notes_text = result.clinician_notes.strip() or (
        "Patient completed the assessment protocol. Accuracy scores and latency metrics recorded above "
        "provide an authoritative baseline of visuospatial working memory and directional processing capabilities."
    )
    notes_box = KeepTogether([
        Paragraph("Clinician Notes and Diagnostic Observations", section_heading),
        Table(
            [[Paragraph(notes_text, value_style)]],
            colWidths=[540],
            style=[
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('PADDING', (0, 0), (-1, -1), 10),
            ]
        )
    ])
    story.append(notes_box)
    story.append(Spacer(1, 16))

    # 7. Security and Integrity Disclaimer
    footer_text = (
        f"CONFIDENTIAL MEDICAL AND COGNITIVE ASSESSMENT REPORT. "
        f"Protected under healthcare data standards. "
        f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}."
    )
    footer_style = ParagraphStyle(
        'DocFooter',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7,
        leading=10,
        textColor=colors.HexColor('#94a3b8'),
        alignment=1,
    )
    story.append(Paragraph(footer_text, footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

