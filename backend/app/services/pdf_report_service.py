"""Executive Incident Disaster Brief PDF Report Generation Service.

Builds a professional 2-page executive report containing:
- Page 1: Incident Header, Classification, Radiometric FIRMS Telemetry, ML Anomaly Score, Risk Tiers, and AI Summary.
- Page 2: Wind Transport & Plume Exposure, Nearest Emergency Infrastructure, Planning Buffers, Incident Schematic Diagram, Data Traceability, and Scientific Disclaimers.
"""

import io
import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Circle, Line, Rect, String, Polygon

from app.schemas.hotspot import (
    HotspotDetailSchema,
    WindDataSchema,
    PlumeConeResponse,
    EmergencyContextResponse,
    IncidentIntelResponse
)

logger = logging.getLogger("fieryvision.pdf")


def build_incident_schematic_drawing(
    lat: float,
    lon: float,
    wind: WindDataSchema,
    emergency: EmergencyContextResponse
) -> Drawing:
    """Generate a clean vector incident diagram illustrating the hotspot, buffers, wind arrow, and infrastructure."""
    d = Drawing(480, 150)
    cx, cy = 180, 75

    # Background card
    d.add(Rect(0, 0, 480, 150, fillColor=colors.HexColor("#070F1E"), strokeColor=colors.HexColor("#1E293B"), strokeWidth=1, rx=6, ry=6))

    # 3 km Planning Buffer (outer circle)
    d.add(Circle(cx, cy, 60, fillColor=colors.HexColor("#0369A1"), strokeColor=colors.HexColor("#38BDF8"), strokeWidth=1.2, fillOpacity=0.12))
    d.add(String(cx + 42, cy - 50, "3 km Planning Buffer", fontSize=7, fillColor=colors.HexColor("#38BDF8"), fontName="Helvetica-Bold"))

    # 1 km Planning Buffer (inner circle)
    d.add(Circle(cx, cy, 26, fillColor=colors.HexColor("#EA580C"), strokeColor=colors.HexColor("#FB923C"), strokeWidth=1.2, fillOpacity=0.18))
    d.add(String(cx + 18, cy - 22, "1 km Buffer", fontSize=6.5, fillColor=colors.HexColor("#FB923C"), fontName="Helvetica-Bold"))

    # Downwind Plume Vector & Cone Arrow
    downwind_rad = math.radians((wind.downwind_bearing_deg - 90) % 360)
    tip_x = cx + math.cos(downwind_rad) * 110
    tip_y = cy - math.sin(downwind_rad) * 55

    # Plume cone wedge
    left_angle = downwind_rad + math.radians(20)
    right_angle = downwind_rad - math.radians(20)
    lx = cx + math.cos(left_angle) * 100
    ly = cy - math.sin(left_angle) * 50
    rx = cx + math.cos(right_angle) * 100
    ry = cy - math.sin(right_angle) * 50

    d.add(Polygon([cx, cy, lx, ly, tip_x, tip_y, rx, ry], fillColor=colors.HexColor("#F59E0B"), strokeColor=colors.HexColor("#FBBF24"), strokeWidth=1, fillOpacity=0.25))

    # Centerline wind arrow
    d.add(Line(cx, cy, tip_x, tip_y, strokeColor=colors.HexColor("#FBBF24"), strokeWidth=2))
    d.add(Circle(tip_x, tip_y, 3, fillColor=colors.HexColor("#FBBF24"), strokeColor=colors.HexColor("#FFFFFF"), strokeWidth=1))

    # Hotspot Centroid Beacon
    d.add(Circle(cx, cy, 6, fillColor=colors.HexColor("#EF4444"), strokeColor=colors.HexColor("#FFFFFF"), strokeWidth=1.5))
    d.add(String(cx - 20, cy + 10, "HOTSPOT", fontSize=7, fillColor=colors.HexColor("#EF4444"), fontName="Helvetica-Bold"))

    # Right side legend & stats
    d.add(Rect(320, 10, 150, 130, fillColor=colors.HexColor("#0B192C"), strokeColor=colors.HexColor("#1E293B"), strokeWidth=1, rx=4, ry=4))
    d.add(String(328, 126, "INCIDENT SCHEMATIC", fontSize=8, fillColor=colors.HexColor("#38BDF8"), fontName="Helvetica-Bold"))
    d.add(String(328, 110, f"Wind: {wind.wind_speed_kmh} km/h {wind.cardinal_direction}", fontSize=7.5, fillColor=colors.HexColor("#E2E8F0"), fontName="Helvetica"))
    d.add(String(328, 96, f"Downwind Bearing: {wind.downwind_bearing_deg:.1f}\u00b0", fontSize=7.5, fillColor=colors.HexColor("#E2E8F0"), fontName="Helvetica"))
    d.add(String(328, 80, f"1km Buffer Sites: {emergency.buffer_1km.fire_stations_count + emergency.buffer_1km.hospitals_count + emergency.buffer_1km.hydrants_count}", fontSize=7.5, fillColor=colors.HexColor("#CBD5E1"), fontName="Helvetica"))
    d.add(String(328, 66, f"3km Buffer Sites: {emergency.buffer_3km.fire_stations_count + emergency.buffer_3km.hospitals_count + emergency.buffer_3km.hydrants_count}", fontSize=7.5, fillColor=colors.HexColor("#CBD5E1"), fontName="Helvetica"))
    d.add(String(328, 48, "INDICATIVE PLUME", fontSize=7, fillColor=colors.HexColor("#F59E0B"), fontName="Helvetica-Bold"))
    d.add(String(328, 36, "Screening Transport Only", fontSize=6.5, fillColor=colors.HexColor("#94A3B8"), fontName="Helvetica-Oblique"))
    d.add(String(328, 24, "Not Confirmed Perimeter", fontSize=6.5, fillColor=colors.HexColor("#94A3B8"), fontName="Helvetica-Oblique"))

    return d


class PDFReportService:
    """Generates professional 2-page Executive Incident Briefs."""

    def generate_incident_pdf(self, incident: IncidentIntelResponse) -> bytes:
        """Compile incident data into a 2-page binary PDF stream."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Custom Typography Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0F172A")
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569")
        )
        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0369A1"),
            spaceBefore=8,
            spaceAfter=4
        )
        body_style = ParagraphStyle(
            "BodyDark",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1E293B")
        )
        body_bold = ParagraphStyle(
            "BodyBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0F172A")
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor("#64748B")
        )

        elements = []
        hs = incident.hotspot
        wind = incident.wind
        plume = incident.plume
        em = incident.emergency

        # =====================================================================
        # PAGE 1: HEADER & INCIDENT METRICS
        # =====================================================================
        
        # Header banner
        header_table = Table(
            [
                [
                    Paragraph("<b>FIERYVISION AI</b> · SATELLITE FIRE INTELLIGENCE", subtitle_style),
                    Paragraph(f"REPORT ID: <b>FV-INC-{hs.id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}</b>", ParagraphStyle("HdrRight", parent=subtitle_style, alignment=2))
                ],
                [
                    Paragraph("GLOBAL INCIDENT DISASTER BRIEF", title_style),
                    Paragraph(f"CLASSIFICATION: <b>{hs.status.upper()}</b>", ParagraphStyle("HdrStatus", parent=title_style, alignment=2, textColor=colors.HexColor("#DC2626") if hs.status.upper() == "ACTIVE" else colors.HexColor("#0284C7")))
                ]
            ],
            colWidths=[340, 200]
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceBefore=4, spaceAfter=8))

        # Core Summary Cards (Table Grid)
        risk_color = "#DC2626" if hs.risk_tier.lower() in ["high", "critical"] else "#D97706" if hs.risk_tier.lower() == "moderate" else "#059669"
        summary_data = [
            [
                Paragraph("<b>INCIDENT CLASSIFICATION</b>", body_bold),
                Paragraph("<b>COMPOSITE RISK</b>", body_bold),
                Paragraph("<b>ML ANOMALY SCORE</b>", body_bold),
                Paragraph("<b>CONFIDENCE</b>", body_bold)
            ],
            [
                Paragraph(f"<font size=10 color='#0284C7'><b>{hs.classification.upper()}</b></font>", body_style),
                Paragraph(f"<font size=10 color='{risk_color}'><b>{hs.risk_score:.1f} / 100 ({hs.risk_tier.upper()})</b></font>", body_style),
                Paragraph(f"<font size=10 color='#7C3AED'><b>{hs.anomaly_score:.3f} (Outlier)</b></font>" if hs.anomaly_score >= 0.5 else f"<font size=10><b>{hs.anomaly_score:.3f}</b></font>", body_style),
                Paragraph(f"<font size=10 color='#0F172A'><b>{hs.confidence * 100:.1f}%</b></font>", body_style)
            ]
        ]
        summary_table = Table(summary_data, colWidths=[160, 130, 130, 120])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 8))

        # Location & Satellite Radiometric Findings (2-Column Table)
        elements.append(Paragraph("1. GEOSPATIAL LOCATION & SATELLITE TELEMETRY", section_heading))
        
        telemetry_rows = [
            [Paragraph("<b>Target Hotspot Name:</b>", body_style), Paragraph(hs.name, body_bold), Paragraph("<b>First Detected:</b>", body_style), Paragraph(hs.first_seen, body_style)],
            [Paragraph("<b>Centroid Coordinates:</b>", body_style), Paragraph(f"{hs.centroid_lat:.5f}°N, {hs.centroid_lon:.5f}°E", body_bold), Paragraph("<b>Latest Acquisition:</b>", body_style), Paragraph(hs.last_seen, body_style)],
            [Paragraph("<b>Country & Region:</b>", body_style), Paragraph(f"{hs.region or ''}, {hs.country} ({hs.continent})", body_style), Paragraph("<b>Event Duration:</b>", body_style), Paragraph(f"{hs.duration_hours:.1f} hours", body_style)],
            [Paragraph("<b>Calculated Area:</b>", body_style), Paragraph(f"{hs.area_sq_km:.2f} km²", body_style), Paragraph("<b>Mean / Peak FRP:</b>", body_style), Paragraph(f"<b>{hs.average_frp:.1f} MW</b> / <b>{hs.max_frp:.1f} MW</b>", body_bold)],
            [Paragraph("<b>Dominant Landcover:</b>", body_style), Paragraph(hs.dominant_landcover, body_style), Paragraph("<b>Brightness Temp:</b>", body_style), Paragraph(f"{hs.average_brightness:.1f} K (Max {hs.max_brightness:.1f} K)", body_style)],
            [Paragraph("<b>FIRMS Detections Count:</b>", body_style), Paragraph(f"{hs.event_count} satellite pixels", body_style), Paragraph("<b>Satellites:</b>", body_style), Paragraph(", ".join(hs.source_satellites) if hs.source_satellites else "VIIRS NOAA-20/21, MODIS", body_style)],
        ]
        telemetry_table = Table(telemetry_rows, colWidths=[120, 150, 110, 160])
        telemetry_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(telemetry_table)
        elements.append(Spacer(1, 8))

        # AI Grounded Investigation Summary
        elements.append(Paragraph("2. AI INCIDENT INVESTIGATION SUMMARY (QWEN2.5 GROUNDED ENGINE)", section_heading))
        ai_text = incident.ai_investigation_summary or (
            f"• Thermal Activity: FieryVision telemetry confirms an active thermal hotspot ({hs.name}) with peak radiative power reaching {hs.max_frp:.1f} MW.\n"
            f"• Persistence & Pattern: The heat signature spans {hs.duration_hours:.1f} hours across {hs.event_count} satellite passes, showing {hs.frp_trend.lower()} intensity trend.\n"
            f"• Atmospheric Vector: Local surface winds at {wind.wind_speed_kmh} km/h blowing from {wind.cardinal_direction} ({wind.wind_direction_deg:.0f}°) establish an indicative downwind transport bearing of {wind.downwind_bearing_deg:.1f}°.\n"
            f"• Emergency Infrastructure Context: Nearest response resource is {em.nearest_fire_station.name if em.nearest_fire_station else 'Local Station'} ({em.nearest_fire_station.distance_m/1000.0:.2f} km) and nearest hospital is {em.nearest_hospital.name if em.nearest_hospital else 'Regional Medical Center'} ({em.nearest_hospital.distance_m/1000.0:.2f} km)."
        )
        ai_paras = [Paragraph(line, body_style) for line in ai_text.split("\n") if line.strip()]
        ai_box = Table([[ai_para] for ai_para in ai_paras], colWidths=[540])
        ai_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F9FF")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#BAE6FD")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(ai_box)

        # Page 1 Footer Note
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Page 1 of 2 · FieryVision AI Global Incident Brief · Powered by NASA FIRMS, Open-Meteo & OpenStreetMap", disclaimer_style))

        # =====================================================================
        # PAGE 2: WIND, PLUME, EMERGENCY INFRASTRUCTURE & DIAGRAM
        # =====================================================================
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceBefore=12, spaceAfter=8))
        elements.append(Paragraph("3. REAL-TIME WIND & INDICATIVE PLUME DISPERSION SCREENING", section_heading))

        wind_rows = [
            [
                Paragraph("<b>Current 10m Wind Speed:</b>", body_style), Paragraph(f"<b>{wind.wind_speed_kmh} km/h</b>", body_bold),
                Paragraph("<b>Wind Direction:</b>", body_style), Paragraph(f"<b>{wind.cardinal_direction} ({wind.wind_direction_deg:.0f}°)</b>", body_bold)
            ],
            [
                Paragraph("<b>Downwind Transport Bearing:</b>", body_style), Paragraph(f"<b>{wind.downwind_bearing_deg:.1f}°</b>", body_bold),
                Paragraph("<b>Weather Data Source:</b>", body_style), Paragraph("Open-Meteo Weather API", body_style)
            ]
        ]
        wind_table = Table(wind_rows, colWidths=[140, 130, 130, 140])
        wind_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE68A")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(wind_table)
        elements.append(Spacer(1, 4))

        # Plume Horizons table
        plume_rows = [
            [
                Paragraph("<b>Forecast Horizon</b>", body_bold),
                Paragraph("<b>Indicative Distance</b>", body_bold),
                Paragraph("<b>Cone Spread Angle</b>", body_bold),
                Paragraph("<b>Screening Confidence</b>", body_bold)
            ]
        ]
        for hz in plume.horizons:
            plume_rows.append([
                Paragraph(f"+{hz.horizon_hours} Hour Projection", body_style),
                Paragraph(f"<b>{hz.projected_distance_km:.1f} km</b>", body_bold),
                Paragraph(f"{hz.cone_spread_angle_deg:.1f}°", body_style),
                Paragraph(hz.confidence_rating, body_style)
            ])
        plume_table = Table(plume_rows, colWidths=[135, 135, 135, 135])
        plume_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(plume_table)
        elements.append(Spacer(1, 8))

        # Emergency Infrastructure Section
        elements.append(Paragraph("4. NEAREST EMERGENCY RESOURCES & EVACUATION PLANNING BUFFERS", section_heading))

        em_rows = [
            [
                Paragraph("<b>Resource Type</b>", body_bold),
                Paragraph("<b>Facility Name</b>", body_bold),
                Paragraph("<b>Distance</b>", body_bold),
                Paragraph("<b>Contact Phone</b>", body_bold)
            ],
            [
                Paragraph("🚒 Fire Station", body_style),
                Paragraph(em.nearest_fire_station.name if em.nearest_fire_station else "Local Fire Service", body_style),
                Paragraph(f"{em.nearest_fire_station.distance_m / 1000.0:.2f} km" if em.nearest_fire_station else "N/A", body_bold),
                Paragraph(em.nearest_fire_station.phone if em.nearest_fire_station else "Unavailable", body_style)
            ],
            [
                Paragraph("🏥 Hospital", body_style),
                Paragraph(em.nearest_hospital.name if em.nearest_hospital else "District Hospital", body_style),
                Paragraph(f"{em.nearest_hospital.distance_m / 1000.0:.2f} km" if em.nearest_hospital else "N/A", body_bold),
                Paragraph(em.nearest_hospital.phone if em.nearest_hospital else "Unavailable", body_style)
            ],
            [
                Paragraph("🩺 Burn / Trauma Unit", body_style),
                Paragraph(em.nearest_burn_trauma.name if em.nearest_burn_trauma else "Specialty capability not verified", body_style),
                Paragraph(f"{em.nearest_burn_trauma.distance_m / 1000.0:.2f} km" if em.nearest_burn_trauma else "N/A", body_bold),
                Paragraph(em.nearest_burn_trauma.phone if em.nearest_burn_trauma else "Unavailable", body_style)
            ],
            [
                Paragraph("🚰 Water Hydrant", body_style),
                Paragraph(em.nearest_hydrant.name if em.nearest_hydrant else "Hydrant data may be incomplete in region", body_style),
                Paragraph(f"{em.nearest_hydrant.distance_m / 1000.0:.2f} km" if em.nearest_hydrant else "N/A", body_bold),
                Paragraph("Municipal Supply", body_style)
            ],
        ]
        em_table = Table(em_rows, colWidths=[120, 200, 90, 130])
        em_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(em_table)
        elements.append(Spacer(1, 6))

        # Planning Buffers Counts
        buf_rows = [
            [
                Paragraph("<b>Planning Buffer Zone</b>", body_bold),
                Paragraph("<b>Fire Stations</b>", body_bold),
                Paragraph("<b>Hospitals</b>", body_bold),
                Paragraph("<b>Hydrants</b>", body_bold),
                Paragraph("<b>Industrial Sites</b>", body_bold)
            ],
            [
                Paragraph("<b>1 km Planning Buffer</b>", body_style),
                Paragraph(str(em.buffer_1km.fire_stations_count), body_bold),
                Paragraph(str(em.buffer_1km.hospitals_count), body_bold),
                Paragraph(str(em.buffer_1km.hydrants_count), body_bold),
                Paragraph(str(em.buffer_1km.industrial_facilities_count), body_bold)
            ],
            [
                Paragraph("<b>3 km Planning Buffer</b>", body_style),
                Paragraph(str(em.buffer_3km.fire_stations_count), body_bold),
                Paragraph(str(em.buffer_3km.hospitals_count), body_bold),
                Paragraph(str(em.buffer_3km.hydrants_count), body_bold),
                Paragraph(str(em.buffer_3km.industrial_facilities_count), body_bold)
            ]
        ]
        buf_table = Table(buf_rows, colWidths=[140, 100, 100, 100, 100])
        buf_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(buf_table)
        elements.append(Spacer(1, 6))

        # Incident Schematic Diagram
        elements.append(Paragraph("5. INCIDENT SCHEMATIC & PLANNING BUFFER DIAGRAM", section_heading))
        schematic = build_incident_schematic_drawing(hs.centroid_lat, hs.centroid_lon, wind, em)
        elements.append(schematic)
        elements.append(Spacer(1, 4))

        # Scientific Disclaimers & Attribution
        elements.append(Paragraph(
            "<b>SCIENTIFIC & STATUTORY DISCLAIMERS:</b><br/>"
            "1. <b>Plume Screening Model:</b> Downwind plume projections are screening-level indicators based on numerical weather-model wind fields (Open-Meteo). They do NOT constitute a certified smoke-dispersion forecast or confirmed physical fire perimeter.<br/>"
            "2. <b>Planning Buffers:</b> 1 km and 3 km rings are situational planning buffers for emergency coordination. They are NOT mandatory evacuation orders.<br/>"
            "3. <b>Data Traceability:</b> Fire telemetry: NASA FIRMS (VIIRS/MODIS); Meteorology: Open-Meteo (CC BY 4.0); Emergency GIS: OpenStreetMap contributors; Landcover: ESA WorldCover 10m.<br/>"
            f"4. <b>Reproducibility:</b> Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} using FieryVision Engine v11.0.",
            disclaimer_style
        ))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


pdf_report_service = PDFReportService()
