import streamlit as st
from supabase import create_client, Client

# Estos datos sacalos de tu panel de Supabase
# Cuando lo subas a la nube, esto también va en los "Secrets"
URL = st.secrets.get("SUPABASE_URL") or 'https://qbatisfjuuglmpmtndbu.supabase.co'
KEY = st.secrets.get("SUPABASE_KEY") or 'sb_publishable_JNOh8O85RQMvC4npma9CxQ_FutqE3nX'

supabase: Client = create_client(URL, KEY)

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
        "obra_social": obra_social
    }
    response = supabase.table("pacientes").insert(data).execute()
    return response
