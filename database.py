python
"""
database.py - Módulo de gestión de base de datos SQLite
Optimizado para Streamlit con manejo de caché y conexiones
"""

import sqlite3
import os
from datetime import datetime
import hashlib
import streamlit as st

class Database:
    def __init__(self, db_path="maintenance.db"):
        """
        Inicializa la conexión con la base de datos SQLite
        """
        self.db_path = db_path
        self.create_tables()
    
    def get_connection(self):
        """Establece conexión con la base de datos"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Permite acceder por nombre de columna
        return conn
    
    def create_tables(self):
        """
        Crea todas las tablas necesarias para la aplicación
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabla de configuración de la empresa
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS company_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                nit TEXT NOT NULL,
                address TEXT,
                logo_path TEXT,
                phone TEXT,
                email TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de equipos (Hojas de Vida)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                area TEXT CHECK(area IN ('Zona Blanca', 'Zona Gris')) NOT NULL,
                brand TEXT,
                model TEXT,
                serial_number TEXT UNIQUE,
                criticality TEXT CHECK(criticality IN ('Alta', 'Media', 'Baja')) NOT NULL,
                photo_path TEXT,
                technical_specs TEXT,
                installation_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                status TEXT DEFAULT 'Activo'
            )
        ''')
        
        # Tabla de POEs (Procedimientos Operativos Estandarizados)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poe (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                equipment_id INTEGER,
                food_safety_warnings TEXT,
                version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'Activo',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                FOREIGN KEY (equipment_id) REFERENCES equipment(id)
            )
        ''')
        
        # Tabla de pasos de POE (incluye desarme)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poe_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poe_id INTEGER NOT NULL,
                step_number INTEGER NOT NULL,
                description TEXT NOT NULL,
                image_path TEXT,
                tools_needed TEXT,
                epp_needed TEXT,
                FOREIGN KEY (poe_id) REFERENCES poe(id),
                UNIQUE(poe_id, step_number)
            )
        ''')
        
        # Tabla de herramientas y EPP por POE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poe_resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poe_id INTEGER NOT NULL,
                resource_type TEXT CHECK(resource_type IN ('Tool', 'EPP')) NOT NULL,
                resource_name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (poe_id) REFERENCES poe(id)
            )
        ''')
        
        # Tabla de tareas de mantenimiento
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id INTEGER NOT NULL,
                task_type TEXT CHECK(task_type IN ('Preventivo', 'Correctivo', 'Predictivo')) NOT NULL,
                poe_id INTEGER,
                description TEXT NOT NULL,
                scheduled_date DATE NOT NULL,
                completion_date DATE,
                status TEXT CHECK(status IN ('Pendiente', 'En Proceso', 'Completado')) DEFAULT 'Pendiente',
                assigned_to TEXT,
                observations TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                FOREIGN KEY (equipment_id) REFERENCES equipment(id),
                FOREIGN KEY (poe_id) REFERENCES poe(id)
            )
        ''')
        
        # Tabla de trazabilidad (auditoría)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS traceability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                action TEXT CHECK(action IN ('CREATE', 'UPDATE', 'DELETE')) NOT NULL,
                changes TEXT,
                user_name TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_traceability(self, table_name, record_id, action, changes, user_name="system"):
        """
        Registra acciones en la tabla de trazabilidad
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO traceability (table_name, record_id, action, changes, user_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (table_name, record_id, action, changes, user_name))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging traceability: {e}")
    
    # ==================== CONFIGURACIÓN DE EMPRESA ====================
    
    def get_company_config(self):
        """Obtiene la configuración de la empresa"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM company_config ORDER BY id DESC LIMIT 1")
            config = cursor.fetchone()
            conn.close()
            return dict(config) if config else None
        except:
            return None
    
    def save_company_config(self, name, nit, address, logo_path, phone="", email=""):
        """Guarda o actualiza la configuración de la empresa"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Verificar si ya existe configuración
        cursor.execute("SELECT id FROM company_config LIMIT 1")
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE company_config 
                SET name=?, nit=?, address=?, logo_path=?, phone=?, email=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (name, nit, address, logo_path, phone, email, existing['id']))
            record_id = existing['id']
        else:
            cursor.execute('''
                INSERT INTO company_config (name, nit, address, logo_path, phone, email)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, nit, address, logo_path, phone, email))
            record_id = cursor.lastrowid
        
        conn.commit()
        self.log_traceability("company_config", record_id, "UPDATE", "Configuración actualizada", "admin")
        conn.close()
        return True
    
    # ==================== OPERACIONES DE EQUIPOS ====================
    
    def add_equipment(self, name, area, brand, model, serial_number, criticality, 
                      photo_path, technical_specs, installation_date, created_by):
        """Agrega un nuevo equipo"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO equipment (name, area, brand, model, serial_number, criticality, 
                                 photo_path, technical_specs, installation_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, area, brand, model, serial_number, criticality, 
              photo_path, technical_specs, installation_date, created_by))
        
        equipment_id = cursor.lastrowid
        conn.commit()
        
        self.log_traceability("equipment", equipment_id, "CREATE", 
                            f"Equipo creado: {name}", created_by)
        conn.close()
        return equipment_id
    
    def get_all_equipment(self):
        """Obtiene todos los equipos"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM equipment ORDER BY name")
            equipment = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return equipment
        except:
            return []
    
    def get_equipment_by_id(self, equipment_id):
        """Obtiene un equipo por su ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,))
            equipment = cursor.fetchone()
            conn.close()
            return dict(equipment) if equipment else None
        except:
            return None
    
    def update_equipment(self, equipment_id, **kwargs):
        """Actualiza información de un equipo"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = []
        values = []
        for key, value in kwargs.items():
            if value is not None:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if updates:
            values.append(equipment_id)
            query = f"UPDATE equipment SET {', '.join(updates)}, updated_at=CURRENT_TIMESTAMP WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            self.log_traceability("equipment", equipment_id, "UPDATE", 
                                f"Equipo actualizado: {', '.join(updates)}", "user")
        
        conn.close()
    
    # ==================== OPERACIONES DE POE ====================
    
    def add_poe(self, title, equipment_id, food_safety_warnings, created_by):
        """Crea un nuevo POE"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO poe (title, equipment_id, food_safety_warnings, created_by)
            VALUES (?, ?, ?, ?)
        ''', (title, equipment_id, food_safety_warnings, created_by))
        
        poe_id = cursor.lastrowid
        conn.commit()
        
        self.log_traceability("poe", poe_id, "CREATE", f"POE creado: {title}", created_by)
        conn.close()
        return poe_id
    
    def add_poe_step(self, poe_id, step_number, description, image_path, tools_needed, epp_needed):
        """Agrega un paso a un POE"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO poe_steps (poe_id, step_number, description, image_path, tools_needed, epp_needed)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (poe_id, step_number, description, image_path, tools_needed, epp_needed))
        
        step_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return step_id
    
    def get_poe_steps(self, poe_id):
        """Obtiene todos los pasos de un POE ordenados"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM poe_steps WHERE poe_id = ? ORDER BY step_number", (poe_id,))
            steps = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return steps
        except:
            return []
    
    def get_all_poes(self):
        """Obtiene todos los POEs"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, e.name as equipment_name 
                FROM poe p
                LEFT JOIN equipment e ON p.equipment_id = e.id
                ORDER BY p.created_at DESC
            ''')
            poes = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return poes
        except:
            return []
    
    # ==================== OPERACIONES DE TAREAS ====================
    
    def add_maintenance_task(self, equipment_id, task_type, poe_id, description, 
                            scheduled_date, assigned_to, created_by):
        """Crea una nueva tarea de mantenimiento"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO maintenance_tasks 
            (equipment_id, task_type, poe_id, description, scheduled_date, assigned_to, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (equipment_id, task_type, poe_id, description, scheduled_date, assigned_to, created_by))
        
        task_id = cursor.lastrowid
        conn.commit()
        
        self.log_traceability("maintenance_tasks", task_id, "CREATE", 
                            f"Tarea creada: {description}", created_by)
        conn.close()
        return task_id
    
    def update_task_status(self, task_id, status, observations=None):
        """Actualiza el estado de una tarea"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if observations:
            cursor.execute('''
                UPDATE maintenance_tasks 
                SET status=?, observations=?, completion_date=CURRENT_DATE, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (status, observations, task_id))
        else:
            cursor.execute('''
                UPDATE maintenance_tasks 
                SET status=?, completion_date=CURRENT_DATE, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (status, task_id))
        
        conn.commit()
        self.log_traceability("maintenance_tasks", task_id, "UPDATE", 
                            f"Estado actualizado a: {status}", "user")
        conn.close()
    
    def get_maintenance_tasks(self, status=None):
        """Obtiene tareas de mantenimiento con filtro opcional por estado"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if status:
                cursor.execute('''
                    SELECT t.*, e.name as equipment_name, e.serial_number
                    FROM maintenance_tasks t
                    LEFT JOIN equipment e ON t.equipment_id = e.id
                    WHERE t.status = ?
                    ORDER BY t.scheduled_date
                ''', (status,))
            else:
                cursor.execute('''
                    SELECT t.*, e.name as equipment_name, e.serial_number
                    FROM maintenance_tasks t
                    LEFT JOIN equipment e ON t.equipment_id = e.id
                    ORDER BY t.scheduled_date
                ''')
            
            tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return tasks
        except:
            return []
    
    def get_overdue_tasks(self):
        """Obtiene tareas vencidas (fecha programada menor a hoy y no completadas)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, e.name as equipment_name, e.serial_number
                FROM maintenance_tasks t
                LEFT JOIN equipment e ON t.equipment_id = e.id
                WHERE t.scheduled_date < DATE('now') AND t.status != 'Completado'
                ORDER BY t.scheduled_date
            ''')
            tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return tasks
        except:
            return []
    
    def get_upcoming_tasks(self, days=7):
        """Obtiene tareas próximas en los próximos X días"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, e.name as equipment_name, e.serial_number
                FROM maintenance_tasks t
                LEFT JOIN equipment e ON t.equipment_id = e.id
                WHERE t.scheduled_date BETWEEN DATE('now') AND DATE('now', '+' || ? || ' days')
                AND t.status != 'Completado'
                ORDER BY t.scheduled_date
            ''', (days,))
            tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return tasks
        except:
            return []
