python
"""
app.py - Aplicación principal de gestión de mantenimiento industrial
Optimizado para ejecución en Streamlit
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from PIL import Image
import io
import base64
import tempfile

from database import Database
from pdf_generator import PDFGenerator

# Configuración de la página - DEBE SER LA PRIMERA INSTRUCCIÓN DE STREAMLIT
st.set_page_config(
    page_title="Sistema de Gestión de Mantenimiento Industrial",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar la base de datos con caché
@st.cache_resource
def init_database():
    return Database()

db = init_database()

# Crear directorio para subir imágenes si no existe
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Inicializar estado de sesión para POE
if 'poe_steps' not in st.session_state:
    st.session_state.poe_steps = []

# Funciones auxiliares
def save_uploaded_image(uploaded_file, prefix=""):
    """
    Guarda una imagen subida y retorna la ruta
    """
    if uploaded_file is not None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}_{uploaded_file.name}"
        filepath = os.path.join("uploads", filename)
        
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return filepath
    return None

# ==================== INTERFAZ PRINCIPAL ====================

# Barra lateral - Navegación
st.sidebar.title("🏭 Gestión de Mantenimiento Industrial")
st.sidebar.markdown("---")

menu = st.sidebar.selectbox(
    "Módulos",
    ["Dashboard", "Configuración Empresa", "Inventario de Equipos", 
     "Editor de POE", "Planificador de Mantenimiento", "Reportes"]
)

# Mostrar información del usuario en la barra lateral
st.sidebar.markdown("---")
if 'username' not in st.session_state:
    st.session_state.username = "admin"

st.sidebar.info(f"👤 Usuario: {st.session_state.username}\n📅 {datetime.now().strftime('%d/%m/%Y')}")

# ==================== DASHBOARD ====================

if menu == "Dashboard":
    st.title("📊 Dashboard de Mantenimiento")
    
    # Obtener datos
    overdue_tasks = db.get_overdue_tasks()
    upcoming_tasks = db.get_upcoming_tasks(7)
    all_tasks = db.get_maintenance_tasks()
    equipment = db.get_all_equipment()
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Total Equipos", len(equipment))
    
    with col2:
        st.metric("⚠️ Tareas Vencidas", len(overdue_tasks), delta="Atención", delta_color="inverse")
    
    with col3:
        st.metric("📅 Tareas Próximas (7 días)", len(upcoming_tasks))
    
    with col4:
        completed_tasks = len([t for t in all_tasks if t.get('status') == 'Completado'])
        total_tasks = len(all_tasks)
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        st.metric("📈 Tasa de Cumplimiento", f"{completion_rate:.1f}%")
    
    st.markdown("---")
    
    # Tabla de tareas vencidas
    st.subheader("⚠️ Tareas Vencidas")
    if overdue_tasks:
        df_overdue = pd.DataFrame(overdue_tasks)
        st.dataframe(
            df_overdue[['id', 'equipment_name', 'task_type', 'description', 'scheduled_date', 'assigned_to']],
            use_container_width=True
        )
    else:
        st.success("✅ No hay tareas vencidas")
    
    # Tabla de tareas próximas
    st.subheader("📅 Tareas Próximas (7 días)")
    if upcoming_tasks:
        df_upcoming = pd.DataFrame(upcoming_tasks)
        st.dataframe(
            df_upcoming[['id', 'equipment_name', 'task_type', 'description', 'scheduled_date', 'assigned_to']],
            use_container_width=True
        )
    else:
        st.info("📭 No hay tareas programadas para los próximos 7 días")
    
    # Gráfico de distribución por área
    st.subheader("🏭 Distribución de Equipos por Área")
    area_counts = {}
    for eq in equipment:
        area = eq.get('area', 'Sin asignar')
        area_counts[area] = area_counts.get(area, 0) + 1
    
    if area_counts:
        st.bar_chart(area_counts)

# ==================== CONFIGURACIÓN EMPRESA ====================

elif menu == "Configuración Empresa":
    st.title("⚙️ Configuración de la Empresa")
    
    # Obtener configuración actual
    config = db.get_company_config()
    
    with st.form("company_config_form"):
        st.subheader("Información General")
        
        name = st.text_input("Nombre de la Empresa *", value=config.get('name', '') if config else '')
        nit = st.text_input("NIT *", value=config.get('nit', '') if config else '')
        address = st.text_area("Dirección", value=config.get('address', '') if config else '')
        phone = st.text_input("Teléfono", value=config.get('phone', '') if config else '')
        email = st.text_input("Email", value=config.get('email', '') if config else '')
        
        st.subheader("Logo de la Empresa")
        logo_file = st.file_uploader("Subir logo", type=['png', 'jpg', 'jpeg'])
        
        if config and config.get('logo_path') and os.path.exists(config['logo_path']):
            st.image(config['logo_path'], width=100, caption="Logo actual")
        
        submitted = st.form_submit_button("💾 Guardar Configuración")
        
        if submitted:
            if not name or not nit:
                st.error("❌ Nombre y NIT son campos obligatorios")
            else:
                logo_path = None
                if logo_file:
                    logo_path = save_uploaded_image(logo_file, "logo")
                elif config and config.get('logo_path'):
                    logo_path = config['logo_path']
                
                db.save_company_config(name, nit, address, logo_path, phone, email)
                st.success("✅ Configuración guardada exitosamente")
                st.rerun()

# ==================== INVENTARIO DE EQUIPOS ====================

elif menu == "Inventario de Equipos":
    st.title("📦 Inventario de Equipos - Hojas de Vida")
    
    tab1, tab2, tab3 = st.tabs(["📋 Listado de Equipos", "➕ Agregar/Editar Equipo", "🔍 Ver Detalle"])
    
    with tab1:
        st.subheader("Equipos Registrados")
        equipment = db.get_all_equipment()
        
        if equipment:
            df_equipment = pd.DataFrame(equipment)
            st.dataframe(
                df_equipment[['id', 'name', 'area', 'brand', 'model', 'serial_number', 'criticality', 'status']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("📭 No hay equipos registrados")
    
    with tab2:
        st.subheader("Agregar Nuevo Equipo")
        
        with st.form("equipment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Nombre del Equipo *")
                area = st.selectbox("Área *", ["Zona Blanca", "Zona Gris"])
                brand = st.text_input("Marca")
                model = st.text_input("Modelo")
            
            with col2:
                serial_number = st.text_input("Número de Serie *")
                criticality = st.selectbox("Criticidad *", ["Alta", "Media", "Baja"])
                installation_date = st.date_input("Fecha de Instalación", value=date.today())
            
            photo = st.file_uploader("Foto del Equipo", type=['png', 'jpg', 'jpeg'])
            technical_specs = st.text_area("Especificaciones Técnicas", height=100)
            
            submitted = st.form_submit_button("💾 Guardar Equipo", use_container_width=True)
            
            if submitted:
                if not name or not serial_number or not area or not criticality:
                    st.error("❌ Los campos marcados con * son obligatorios")
                else:
                    photo_path = save_uploaded_image(photo, f"equipment_{serial_number}") if photo else None
                    
                    db.add_equipment(
                        name, area, brand, model, serial_number, criticality,
                        photo_path, technical_specs, installation_date,
                        st.session_state.username
                    )
                    st.success("✅ Equipo agregado exitosamente")
                    st.rerun()
    
    with tab3:
        st.subheader("Detalle de Equipo")
        
        equipment = db.get_all_equipment()
        if equipment:
            equipment_options = {eq['name']: eq['id'] for eq in equipment}
            selected_name = st.selectbox("Seleccionar Equipo", list(equipment_options.keys()))
            selected_id = equipment_options[selected_name]
            
            eq = db.get_equipment_by_id(selected_id)
            
            if eq:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if eq.get('photo_path') and os.path.exists(eq['photo_path']):
                        st.image(eq['photo_path'], width=250)
                    else:
                        st.info("📷 No hay foto disponible")
                
                with col2:
                    st.write(f"**🏷️ Nombre:** {eq['name']}")
                    st.write(f"**📍 Área:** {eq['area']}")
                    st.write(f"**🏭 Marca:** {eq['brand']}")
                    st.write(f"**🔢 Modelo:** {eq['model']}")
                    st.write(f"**🔑 Número de Serie:** {eq['serial_number']}")
                    st.write(f"**⚠️ Criticidad:** {eq['criticality']}")
                    st.write(f"**📊 Estado:** {eq['status']}")
                    st.write(f"**📅 Fecha Instalación:** {eq['installation_date']}")
                    st.write(f"**📝 Especificaciones Técnicas:** {eq['technical_specs']}")
                
                # Historial de mantenimiento del equipo
                st.subheader("📋 Historial de Mantenimiento")
                tasks = db.get_maintenance_tasks()
                equipment_tasks = [t for t in tasks if t.get('equipment_id') == eq['id']]
                
                if equipment_tasks:
                    df_tasks = pd.DataFrame(equipment_tasks)
                    st.dataframe(
                        df_tasks[['task_type', 'description', 'scheduled_date', 'status', 'assigned_to']],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("📭 No hay tareas de mantenimiento registradas para este equipo")

# ==================== EDITOR DE POE ====================

elif menu == "Editor de POE":
    st.title("📋 Editor de POE y Procedimientos")
    
    tab1, tab2 = st.tabs(["📄 Listado de POEs", "✏️ Crear Nuevo POE"])
    
    with tab1:
        st.subheader("Procedimientos Registrados")
        poes = db.get_all_poes()
        
        if poes:
            for poe in poes:
                with st.expander(f"📄 {poe['title']} - V{poe['version']}"):
                    st.write(f"**Equipo Asociado:** {poe.get('equipment_name', 'N/A')}")
                    st.write(f"**⚠️ Advertencias de Inocuidad:** {poe.get('food_safety_warnings', 'N/A')}")
                    st.write(f"**📅 Fecha Creación:** {poe.get('created_at', 'N/A')}")
                    
                    # Mostrar pasos
                    steps = db.get_poe_steps(poe['id'])
                    if steps:
                        st.write("**📝 Pasos del Procedimiento:**")
                        for step in steps:
                            st.write(f"**{step['step_number']}.** {step['description']}")
                            if step.get('tools_needed'):
                                st.caption(f"🛠️ Herramientas: {step['tools_needed']}")
                            if step.get('epp_needed'):
                                st.caption(f"🛡️ EPP: {step['epp_needed']}")
                            if step.get('image_path') and os.path.exists(step['image_path']):
                                st.image(step['image_path'], width=200)
                            st.markdown("---")
                    
                    # Botón para generar PDF
                    if st.button(f"📄 Generar PDF", key=f"pdf_{poe['id']}"):
                        with st.spinner("Generando PDF..."):
                            config = db.get_company_config()
                            pdf_gen = PDFGenerator(config)
                            steps = db.get_poe_steps(poe['id'])
                            filename = pdf_gen.generate_poe_report(poe, steps)
                            
                            with open(filename, "rb") as f:
                                pdf_data = f.read()
                            
                            st.download_button(
                                label="📥 Descargar PDF",
                                data=pdf_data,
                                file_name=f"POE_{poe['title']}.pdf",
                                mime="application/pdf"
                            )
                            os.unlink(filename)
        else:
            st.info("📭 No hay POEs registrados")
    
    with tab2:
        st.subheader("Crear Nuevo POE")
        
        with st.form("poe_form"):
            title = st.text_input("Título del Procedimiento *")
            
            equipment_list = db.get_all_equipment()
            equipment_options = {eq['name']: eq['id'] for eq in equipment_list}
            equipment_name = st.selectbox("Equipo Asociado", ["Ninguno"] + list(equipment_options.keys()))
            equipment_id = equipment_options.get(equipment_name) if equipment_name != "Ninguno" else None
            
            food_safety = st.text_area("⚠️ Advertencias de Inocuidad *", 
                                       placeholder="Ej: Usar lubricantes grado alimenticio, evitar contaminación cruzada, limpieza previa...")
            
            st.subheader("🛠️ Herramientas y EPP Generales")
            tools = st.text_input("Herramientas necesarias (separadas por coma)")
            epp = st.text_input("Elementos de Protección Personal (separados por coma)")
            
            st.subheader("📝 Pasos del Procedimiento")
            
            # Botón para agregar paso
            if st.button("➕ Agregar Paso", type="secondary"):
                st.session_state.poe_steps.append({
                    'step_num': len(st.session_state.poe_steps) + 1,
                    'desc': '',
                    'tools': '',
                    'epp': '',
                    'image': None
                })
                st.rerun()
            
            # Mostrar pasos existentes
            steps_to_remove = []
            for idx, step in enumerate(st.session_state.poe_steps):
                st.markdown(f"**Paso {step['step_num']}**")
                col1, col2 = st.columns([3, 1])
                with col1:
                    step['desc'] = st.text_area(f"Descripción", value=step['desc'], key=f"desc_{idx}", height=100)
                with col2:
                    step['tools'] = st.text_input("Herramientas", value=step['tools'], key=f"tools_{idx}")
                    step['epp'] = st.text_input("EPP", value=step['epp'], key=f"epp_{idx}")
                    step['image'] = st.file_uploader(f"Imagen", type=['png', 'jpg', 'jpeg'], key=f"img_{idx}")
                
                if st.button(f"🗑️ Eliminar Paso {step['step_num']}", key=f"del_{idx}"):
                    steps_to_remove.append(idx)
                
                st.markdown("---")
            
            # Eliminar pasos marcados
            for idx in reversed(steps_to_remove):
                st.session_state.poe_steps.pop(idx)
                # Renumerar pasos
                for i, s in enumerate(st.session_state.poe_steps):
                    s['step_num'] = i + 1
                st.rerun()
            
            submitted = st.form_submit_button("💾 Guardar POE", use_container_width=True)
            
            if submitted:
                if not title or not food_safety:
                    st.error("❌ Título y Advertencias de Inocuidad son obligatorios")
                elif not st.session_state.poe_steps:
                    st.error("❌ Debe agregar al menos un paso al procedimiento")
                else:
                    # Guardar POE
                    poe_id = db.add_poe(title, equipment_id, food_safety, st.session_state.username)
                    
                    # Guardar pasos
                    for step in st.session_state.poe_steps:
                        image_path = save_uploaded_image(step['image'], f"poe_{poe_id}_step_{step['step_num']}") if step['image'] else None
                        db.add_poe_step(
                            poe_id, step['step_num'], step['desc'],
                            image_path, step['tools'], step['epp']
                        )
                    
                    st.success("✅ POE guardado exitosamente")
                    st.session_state.poe_steps = []
                    st.rerun()

# ==================== PLANIFICADOR DE MANTENIMIENTO ====================

elif menu == "Planificador de Mantenimiento":
    st.title("📅 Planificador de Mantenimiento")
    
    tab1, tab2, tab3 = st.tabs(["📋 Tareas Programadas", "➕ Crear Nueva Tarea", "✅ Actualizar Estado"])
    
    with tab1:
        st.subheader("Tareas de Mantenimiento")
        
        filter_status = st.selectbox("Filtrar por estado", ["Todos", "Pendiente", "En Proceso", "Completado"])
        
        if filter_status == "Todos":
            tasks = db.get_maintenance_tasks()
        else:
            tasks = db.get_maintenance_tasks(filter_status)
        
        if tasks:
            df_tasks = pd.DataFrame(tasks)
            st.dataframe(
                df_tasks[['id', 'equipment_name', 'task_type', 'description', 'scheduled_date', 'status', 'assigned_to']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("📭 No hay tareas registradas")
    
    with tab2:
        st.subheader("Programar Nueva Tarea")
        
        with st.form("new_task_form"):
            equipment_list = db.get_all_equipment()
            if equipment_list:
                equipment_options = {eq['name']: eq['id'] for eq in equipment_list}
                equipment_name = st.selectbox("Equipo", list(equipment_options.keys()))
                equipment_id = equipment_options[equipment_name]
                
                task_type = st.selectbox("Tipo de Mantenimiento", ["Preventivo", "Correctivo", "Predictivo"])
                
                poe_list = db.get_all_poes()
                poe_options = {poe['title']: poe['id'] for poe in poe_list}
                poe_title = st.selectbox("POE Asociado (opcional)", ["Ninguno"] + list(poe_options.keys()))
                poe_id = poe_options.get(poe_title) if poe_title != "Ninguno" else None
                
                description = st.text_area("Descripción de la tarea *", height=100)
                scheduled_date = st.date_input("Fecha Programada", value=date.today())
                assigned_to = st.text_input("Responsable")
                
                submitted = st.form_submit_button("💾 Programar Tarea", use_container_width=True)
                
                if submitted:
                    if not description:
                        st.error("❌ La descripción es obligatoria")
                    else:
                        db.add_maintenance_task(
                            equipment_id, task_type, poe_id, description,
                            scheduled_date, assigned_to, st.session_state.username
                        )
                        st.success("✅ Tarea programada exitosamente")
                        st.rerun()
            else:
                st.warning("⚠️ No hay equipos registrados. Agregue equipos antes de programar tareas.")
    
    with tab3:
        st.subheader("Actualizar Estado de Tarea")
        
        pending_tasks = db.get_maintenance_tasks("Pendiente")
        in_progress_tasks = db.get_maintenance_tasks("En Proceso")
        all_active_tasks = pending_tasks + in_progress_tasks
        
        if all_active_tasks:
            task_options = {f"{t['id']} - {t['equipment_name']} - {t['description'][:50]}": t['id'] 
                          for t in all_active_tasks}
            selected_task = st.selectbox("Seleccionar Tarea", list(task_options.keys()))
            task_id = task_options[selected_task]
            
            task = next((t for t in all_active_tasks if t['id'] == task_id), None)
            
            if task:
                st.info(f"**Equipo:** {task['equipment_name']}\n\n"
                       f"**Tipo:** {task['task_type']}\n\n"
                       f"**Descripción:** {task['description']}\n\n"
                       f"**Estado actual:** {task['status']}")
                
                new_status = st.selectbox("Nuevo Estado", ["En Proceso", "Completado"])
                observations = st.text_area("Observaciones (opcional)", height=100)
                
                if st.button("✅ Actualizar Estado", use_container_width=True):
                    db.update_task_status(task_id, new_status, observations)
                    st.success(f"✅ Tarea actualizada a {new_status}")
                    st.rerun()
        else:
            st.info("📭 No hay tareas pendientes o en proceso")

# ==================== REPORTES ====================

elif menu == "Reportes":
    st.title("📄 Generación de Reportes")
    
    report_type = st.selectbox("Tipo de Reporte", 
                               ["📊 Reporte de Equipos", "📋 Reporte de Mantenimiento", "📄 Reporte de POEs"])
    
    if report_type == "📊 Reporte de Equipos":
        equipment_list = db.get_all_equipment()
        
        if equipment_list:
            selected_equipment = st.selectbox("Seleccionar Equipo", 
                                             [eq['name'] for eq in equipment_list])
            equipment = next((eq for eq in equipment_list if eq['name'] == selected_equipment), None)
            
            if st.button("📄 Generar Reporte de Equipo", use_container_width=True):
                with st.spinner("Generando PDF..."):
                    config = db.get_company_config()
                    pdf_gen = PDFGenerator(config)
                    filename = pdf_gen.generate_equipment_report(equipment)
                    
                    with open(filename, "rb") as f:
                        pdf_data = f.read()
                    
                    st.download_button(
                        label="📥 Descargar Reporte",
                        data=pdf_data,
                        file_name=f"Reporte_Equipo_{equipment['name']}.pdf",
                        mime="application/pdf"
                    )
                    os.unlink(filename)
        else:
            st.warning("⚠️ No hay equipos registrados")
    
    elif report_type == "📋 Reporte de Mantenimiento":
        report_filter = st.selectbox("Filtrar por", ["Todos", "Vencidas", "Próximas 7 días"])
        
        if report_filter == "Todos":
            tasks = db.get_maintenance_tasks()
        elif report_filter == "Vencidas":
            tasks = db.get_overdue_tasks()
        else:
            tasks = db.get_upcoming_tasks(7)
        
        st.write(f"**Total de tareas:** {len(tasks)}")
        
        if tasks:
            df_preview = pd.DataFrame(tasks)
            st.dataframe(df_preview[['equipment_name', 'task_type', 'description', 'scheduled_date', 'status']],
                        use_container_width=True, hide_index=True)
            
            if st.button("📄 Generar Reporte de Mantenimiento", use_container_width=True):
                with st.spinner("Generando PDF..."):
                    config = db.get_company_config()
                    pdf_gen = PDFGenerator(config)
                    filename = pdf_gen.generate_maintenance_report(tasks, report_filter)
                    
                    with open(filename, "rb") as f:
                        pdf_data = f.read()
                    
                    st.download_button(
                        label="📥 Descargar Reporte",
                        data=pdf_data,
                        file_name=f"Reporte_Mantenimiento_{report_filter}.pdf",
                        mime="application/pdf"
                    )
                    os.unlink(filename)
        else:
            st.info("📭 No hay tareas para mostrar")
    
    elif report_type == "📄 Reporte de POEs":
        poes = db.get_all_poes()
        
        if poes:
            selected_poe = st.selectbox("Seleccionar POE", [poe['title'] for poe in poes])
            poe = next((p for p in poes if p['title'] == selected_poe), None)
            
            if poe and st.button("📄 Generar Reporte de POE", use_container_width=True):
                with st.spinner("Generando PDF..."):
                    config = db.get_company_config()
                    pdf_gen = PDFGenerator(config)
                    steps = db.get_poe_steps(poe['id'])
                    filename = pdf_gen.generate_poe_report(poe, steps)
                    
                    with open(filename, "rb") as f:
                        pdf_data = f.read()
                    
                    st.download_button(
                        label="📥 Descargar POE",
                        data=pdf_data,
                        file_name=f"POE_{poe['title']}.pdf",
                        mime="application/pdf"
                    )
                    os.unlink(filename)
        else:
            st.warning("⚠️ No hay POEs registrados")

# ==================== PIE DE PÁGINA ====================

st.sidebar.markdown("---")
st.sidebar.caption("🏭 Sistema de Gestión de Mantenimiento Industrial v1.0")
st.sidebar.caption("✅ Cumple con normas de inocuidad y calidad")
