import streamlit as st
from supabase import create_client, Client

# Configuración de Supabase
URL = st.secrets.get("SUPABASE_URL") or 'https://qbatisfjuuglmpmtndbu.supabase.co'
KEY = st.secrets.get("SUPABASE_KEY") or 'sb_publishable_JNOh8O85RQMvC4npma9CxQ_FutqE3nX'

supabase: Client = create_client(URL, KEY)

# --- FUNCIONES PARA ODONTÓLOGOS (NUEVAS/ACTUALIZADAS) ---

def registrar_odontologo(datos_odontologo):
    """
    Guarda un nuevo odontólogo en la tabla 'Odontólogo'.
    Asegurate de que 'datos_odontologo' incluya la clave 'email'.
    """
    # Usamos los nombres de columna exactos de tu Supabase
    data = {
        "nombre": datos_odontologo.get("nombre"),
        "apellido": datos_odontologo.get("apellido"),
        "email": datos_odontologo.get("email"), # <--- ESTO ES LO QUE SUMAMOS
        "matricula": datos_odontologo.get("matricula"),
        "direccion": datos_odontologo.get("direccion"),
        "especialidad": datos_odontologo.get("especialidad"),
        "horarios": datos_odontologo.get("horarios"),
        "telefono": datos_odontologo.get("telefono"),
        "consultorio": datos_odontologo.get("consultorio")
    }
    response = supabase.table("Odontólogo").insert(data).execute()
    return response

def obtener_odontologo_por_mail(email):
    """Busca si existe un odontólogo con ese mail (para recuperación)."""
    response = supabase.table("Odontólogo").select("*").eq("email", email).execute()
    return response.data

# --- FUNCIONES PARA PACIENTES Y TURNOS (TUS FUNCIONES DE SIEMPRE) ---

def obtener_pacientes():
    """Trae la lista de todos los pacientes."""
    response = supabase.table("pacientes").select("*").execute()
    return response.data

def agregar_paciente(nombre, apellido, dni, tel, obra_social):
    """Guarda un nuevo paciente en la base de datos."""
    data = {
        "nombre": nombre,
        "apellido": apellido,
        "dni": dni,
        "telefono": tel,
        "obra social": obra_social
    }
    response = supabase.table("pacientes").insert(data).execute()
    return response

def obtener_turnos():
    """Trae todos los turnos agendados."""
    response = supabase.table("turnos").select("*").execute()
    return response.data

def guardar_turno(datos_turno):
    """Guarda el turno confirmado después del pago."""
    data = {
        "nombre paciente": datos_turno.get("paciente_nombre"),
        "dni": datos_turno.get("dni"),
        "fecha": datos_turno.get("fecha"),
        "hora": datos_turno.get("hora"),
        "motivo": datos_turno.get("motivo"),
        "estado": "confirmado"
    }
    response = supabase.table("turnos").insert(data).execute()
    return response

def verificar_disponibilidad(fecha, hora):
    """Checkea si ya existe un turno en ese horario."""
    response = supabase.table("turnos").select("*")\
        .eq("fecha", fecha).eq("hora", hora).execute()
    return len(response.data) == 0