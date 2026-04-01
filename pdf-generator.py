python
"""
pdf_generator.py - Generador de reportes profesionales en PDF
Optimizado para Streamlit con manejo de archivos temporales
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os
from datetime import datetime
from PIL import Image as PILImage
import tempfile
import streamlit as st

class PDFGenerator:
    def __init__(self, company_config):
        """
        Inicializa el generador de PDF con la configuración de la empresa
        """
        self.company_config = company_config
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Configura estilos personalizados para el documento"""
        # Estilo para título principal
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Title'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=colors.HexColor('#003366')
        ))
        
        # Estilo para encabezados de sección
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            alignment=TA_LEFT,
            spaceAfter=12,
            textColor=colors.HexColor('#0066CC')
        ))
        
        # Estilo para texto normal
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=6
        ))
        
        # Estilo para firmas
        self.styles.add(ParagraphStyle(
            name='Signature',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            spaceAfter=20
        ))
    
    def add_header_footer(self, canvas, doc):
        """
        Agrega encabezado y pie de página a cada página
        """
        canvas.saveState()
        
        # Encabezado
        if self.company_config and self.company_config.get('logo_path') and os.path.exists(self.company_config['logo_path']):
            try:
                img = PILImage.open(self.company_config['logo_path'])
                img.thumbnail((80, 80))
                # Usar archivo temporal
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    img.save(tmp.name)
                    canvas.drawImage(tmp.name, 30, A4[1] - 50, width=40, height=40)
                    os.unlink(tmp.name)
            except Exception as e:
                print(f"Error loading logo: {e}")
        
        # Texto del encabezado
        company_name = self.company_config.get('name', 'EMPRESA') if self.company_config else 'EMPRESA'
        canvas.setFont('Helvetica-Bold', 12)
        canvas.drawString(120, A4[1] - 35, company_name)
        canvas.setFont('Helvetica', 8)
        if self.company_config:
            canvas.drawString(120, A4[1] - 48, f"NIT: {self.company_config.get('nit', '')}")
            canvas.drawString(120, A4[1] - 61, f"Dirección: {self.company_config.get('address', '')}")
        
        # Línea decorativa
        canvas.setStrokeColor(colors.HexColor('#003366'))
        canvas.setLineWidth(1)
        canvas.line(30, A4[1] - 75, A4[0] - 30, A4[1] - 75)
        
        # Pie de página
        canvas.setFont('Helvetica', 8)
        canvas.drawString(30, 30, f"Página {doc.page}")
        canvas.drawString(A4[0] - 80, 30, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.drawString(A4[0] / 2 - 50, 30, "Sistema de Gestión de Mantenimiento Industrial")
        
        canvas.restoreState()
    
    def generate_control_changes_table(self):
        """
        Genera la tabla de control de cambios para el documento
        """
        data = [
            ['Versión', 'Fecha', 'Descripción del Cambio', 'Realizado por', 'Aprobado por'],
            ['1.0', datetime.now().strftime('%d/%m/%Y'), 'Documento inicial', 'Sistema', 'Gerencia']
        ]
        
        table = Table(data, colWidths=[2*cm, 2.5*cm, 5*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        
        return table
    
    def generate_signatures_section(self):
        """
        Genera la sección de firmas
        """
        signature_data = [
            ['Realizado por:', '', 'Aprobado por:', ''],
            ['_________________________', '', '_________________________', ''],
            ['Nombre:', '', 'Nombre:', ''],
            ['Fecha:', datetime.now().strftime('%d/%m/%Y'), 'Fecha:', datetime.now().strftime('%d/%m/%Y')]
        ]
        
        table = Table(signature_data, colWidths=[5*cm, 4*cm, 5*cm, 4*cm])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        return table
    
    def generate_equipment_report(self, equipment):
        """
        Genera un reporte de hoja de vida de equipo
        """
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            filename = tmp.name
        
        doc = SimpleDocTemplate(filename, pagesize=A4, 
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # Título
        title = Paragraph(f"HOJA DE VIDA DEL EQUIPO", self.styles['MainTitle'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Tabla de control de cambios
        story.append(Paragraph("Control de Cambios", self.styles['SectionHeader']))
        story.append(self.generate_control_changes_table())
        story.append(Spacer(1, 20))
        
        # Información del equipo
        story.append(Paragraph("Información General del Equipo", self.styles['SectionHeader']))
        
        equipment_data = [
            ['Nombre del Equipo:', equipment.get('name', 'N/A')],
            ['Área:', equipment.get('area', 'N/A')],
            ['Marca:', equipment.get('brand', 'N/A')],
            ['Modelo:', equipment.get('model', 'N/A')],
            ['Número de Serie:', equipment.get('serial_number', 'N/A')],
            ['Criticidad:', equipment.get('criticality', 'N/A')],
            ['Fecha de Instalación:', equipment.get('installation_date', 'N/A')],
            ['Estado:', equipment.get('status', 'N/A')],
            ['Especificaciones Técnicas:', equipment.get('technical_specs', 'N/A')]
        ]
        
        equipment_table = Table(equipment_data, colWidths=[5*cm, 10*cm])
        equipment_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E6E6E6')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(equipment_table)
        story.append(Spacer(1, 20))
        
        # Sección de firmas
        story.append(Paragraph("Aprobaciones", self.styles['SectionHeader']))
        story.append(self.generate_signatures_section())
        
        doc.build(story, onFirstPage=self.add_header_footer, onLaterPages=self.add_header_footer)
        return filename
    
    def generate_poe_report(self, poe_data, steps):
        """
        Genera un reporte de POE con todos los pasos e imágenes
        """
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            filename = tmp.name
        
        doc = SimpleDocTemplate(filename, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # Título
        title = Paragraph(f"PROCEDIMIENTO OPERATIVO ESTANDARIZADO (POE)", self.styles['MainTitle'])
        story.append(title)
        story.append(Spacer(1, 10))
        
        subtitle = Paragraph(poe_data.get('title', 'Sin título'), self.styles['SectionHeader'])
        story.append(subtitle)
        story.append(Spacer(1, 20))
        
        # Tabla de control de cambios
        story.append(Paragraph("Control de Cambios", self.styles['SectionHeader']))
        story.append(self.generate_control_changes_table())
        story.append(Spacer(1, 20))
        
        # Advertencias de inocuidad
        story.append(Paragraph("ADVERTENCIAS DE INOCUIDAD", self.styles['SectionHeader']))
        food_safety = Paragraph(poe_data.get('food_safety_warnings', 'N/A'), self.styles['NormalText'])
        story.append(food_safety)
        story.append(Spacer(1, 20))
        
        # Información general
        story.append(Paragraph("Información General", self.styles['SectionHeader']))
        general_data = [
            ['Equipo Asociado:', poe_data.get('equipment_name', 'N/A')],
            ['Versión:', f"V{poe_data.get('version', 1)}"],
            ['Fecha Creación:', poe_data.get('created_at', 'N/A')]
        ]
        
        general_table = Table(general_data, colWidths=[5*cm, 10*cm])
        general_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E6E6E6')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(general_table)
        story.append(Spacer(1, 20))
        
        # Procedimiento paso a paso
        story.append(Paragraph("Procedimiento Paso a Paso", self.styles['SectionHeader']))
        
        for step in steps:
            step_text = f"<b>Paso {step['step_number']}:</b> {step['description']}"
            step_paragraph = Paragraph(step_text, self.styles['NormalText'])
            story.append(step_paragraph)
            
            if step.get('tools_needed') and step['tools_needed']:
                tools_text = f"<i>Herramientas necesarias:</i> {step['tools_needed']}"
                story.append(Paragraph(tools_text, self.styles['NormalText']))
            
            if step.get('epp_needed') and step['epp_needed']:
                epp_text = f"<i>EPP requerido:</i> {step['epp_needed']}"
                story.append(Paragraph(epp_text, self.styles['NormalText']))
            
            if step.get('image_path') and os.path.exists(step['image_path']):
                try:
                    img = PILImage.open(step['image_path'])
                    img.thumbnail((400, 300))
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
                        img.save(tmp_img.name)
                        story.append(Image(tmp_img.name, width=300, height=200))
                        story.append(Spacer(1, 10))
                        os.unlink(tmp_img.name)
                except Exception as e:
                    print(f"Error loading step image: {e}")
            
            story.append(Spacer(1, 10))
        
        story.append(PageBreak())
        
        # Sección de firmas
        story.append(Paragraph("Aprobaciones", self.styles['SectionHeader']))
        story.append(self.generate_signatures_section())
        
        doc.build(story, onFirstPage=self.add_header_footer, onLaterPages=self.add_header_footer)
        return filename
    
    def generate_maintenance_report(self, tasks, report_type="General"):
        """
        Genera un reporte de tareas de mantenimiento
        """
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            filename = tmp.name
        
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4),
                               rightMargin=1.5*cm, leftMargin=1.5*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # Título
        title = Paragraph(f"REPORTE DE MANTENIMIENTO - {report_type}", self.styles['MainTitle'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Tabla de control de cambios
        story.append(Paragraph("Control de Cambios", self.styles['SectionHeader']))
        story.append(self.generate_control_changes_table())
        story.append(Spacer(1, 20))
        
        # Tabla de tareas
        if tasks:
            data = [['ID', 'Equipo', 'Tipo', 'Descripción', 'Fecha Prog.', 'Estado', 'Responsable']]
            
            for task in tasks:
                data.append([
                    str(task.get('id', '')),
                    task.get('equipment_name', 'N/A'),
                    task.get('task_type', 'N/A'),
                    task.get('description', 'N/A')[:50],
                    task.get('scheduled_date', 'N/A'),
                    task.get('status', 'N/A'),
                    task.get('assigned_to', 'N/A')
                ])
            
            table = Table(data, colWidths=[1.5*cm, 3*cm, 2.5*cm, 5*cm, 2.5*cm, 2.5*cm, 3*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
            
            # Estadísticas
            story.append(Paragraph("Estadísticas", self.styles['SectionHeader']))
            total = len(tasks)
            completed = len([t for t in tasks if t.get('status') == 'Completado'])
            pending = len([t for t in tasks if t.get('status') == 'Pendiente'])
            in_progress = len([t for t in tasks if t.get('status') == 'En Proceso'])
            
            stats_data = [
                ['Total Tareas:', str(total)],
                ['Completadas:', str(completed)],
                ['Pendientes:', str(pending)],
                ['En Proceso:', str(in_progress)]
            ]
            
            stats_table = Table(stats_data, colWidths=[5*cm, 5*cm])
            stats_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E6E6E6')),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(stats_table)
        else:
            story.append(Paragraph("No hay tareas para mostrar", self.styles['NormalText']))
        
        story.append(PageBreak())
        
        # Sección de firmas
        story.append(Paragraph("Aprobaciones", self.styles['SectionHeader']))
        story.append(self.generate_signatures_section())
        
        doc.build(story, onFirstPage=self.add_header_footer, onLaterPages=self.add_header_footer)
        return filename
