import os
import streamlit as st
from supabase import create_client, Client

# Configuración de Supabase (Busca primero en Render y si no está, en Streamlit)
URL = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL") or 'https://qbatisfjuuglmpmtndbu.supabase.co'
KEY = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY") or 'sb_publishable_JNOh8O85RQMvC4npma9CxQ_FutqE3nX'

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

def registrar_pago(datos_pago):
    """Guarda el registro del pago exitoso en la tabla 'pagos'."""
    data = {
        "odontologo_id": datos_pago.get("odontologo_id"),
        "monto_total": datos_pago.get("monto"),
        "comision_monto": datos_pago.get("comision"),
        "estado": "aprobado",
        "paciente_nombre": datos_pago.get("paciente")
    }
    # Asegurate de tener creada la tabla 'pagos' en Supabase
    response = supabase.table("pagos").insert(data).execute()
    return response

def guardar_credenciales_mp(user_id, mp_access_token, public_key=None, refresh_token=None):
    """Guarda o actualiza las credenciales de Mercado Pago de un odontólogo."""
    
    # Armamos el paquete de datos
    data = {
        "user_id": user_id,  # Este es el ID que Supabase usa para saber DE QUIÉN es el token
        "mp_access_token": mp_access_token,
        "public_key": public_key,
        "refresh_token": refresh_token
    }

    try:
        # El upsert necesita que 'user_id' sea una clave única en tu tabla de Supabase
        # Si ya existe el user_id, pisa el token viejo con el nuevo.
        response = supabase.table("credenciales_mercadopago").upsert(
            data, 
            on_conflict="user_id"
            ).execute()
        return response
    except Exception as e:
        st.error(f"Error al guardar en Supabase: {str(e)}")
        return None

    # Usamos upsert para que si ya existe el user_id, lo actualice en vez de crear otro
    response = supabase.table("credenciales_mercadopago").upsert(data, on_conflict="user_id").execute()
    return response

    def eliminar_cuenta_completa(odontologo_id):
        """
        Elimina toda la información de un odontólogo de todas las tablas.
        ¡Acción irreversible!
        """
        # Lista de tablas a limpiar
        tablas = [
            "precios_odontologo", 
            "credenciales_mercadopago", 
            "pacientes", 
            "pagos", 
            "odontologo"
        ]
    
    try:
        for tabla in tablas:
            # Ejecutamos el borrado donde coincida el ID del odontólogo
            supabase.table(tabla).delete().eq("odontologo_id", odontologo_id).execute()
        
        return True, "Cuenta eliminada con éxito de todos los registros."
    except Exception as e:
        return False, f"Error al intentar borrar la cuenta: {str(e)}"