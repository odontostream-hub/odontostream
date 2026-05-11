import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import datetime
import json

# Permisos: Leer y escribir en su Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def crear_flujo_oauth():
    """Crea el flujo de autenticación usando el dominio real odontostream.com.ar."""
    client_id = st.secrets["google_oauth"]["client_id"]
    client_secret = st.secrets["google_oauth"]["client_secret"]
    
    # IMPORTANTE: Aquí usamos tu dominio real para que Google lo acepte
    redirect_uri = "https://odontostream.com.ar"

    client_config = {
        "web": {
            "client_id": client_id,
            "project_id": "odonto-stream-calendar",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": [redirect_uri]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    return flow

def obtener_servicio_calendar():
    """Devuelve el cliente de Google Calendar listo para usarse."""
    if "google_credentials" not in st.session_state:
        return None
    
    creds_info = st.session_state.google_credentials
    creds = Credentials.from_authorized_user_info(creds_info, SCOPES)
    
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        try:
            creds.refresh(Request())
            st.session_state.google_credentials = json.loads(creds.to_json())
        except Exception as e:
            st.error(f"Error al refrescar la sesión de Google: {e}")
            return None
        
    return build('calendar', 'v3', credentials=creds)

def listar_proximos_eventos(max_resultados=10):
    """Trae los próximos turnos de la agenda del odontólogo."""
    service = obtener_servicio_calendar()
    if not service:
        return []
    
    ahora = datetime.datetime.utcnow().isoformat() + 'Z' 
    
    try:
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=ahora,
            maxResults=max_resultados, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        if "invalid_grant" in str(e):
            if "google_credentials" in st.session_state:
                del st.session_state.google_credentials
        return []

# ==================== LA NUEVA FUNCIÓN (EL BRAZO ROBÓTICO) ====================
def registrar_turno_en_google(resumen, inicio_iso, fin_iso, descripcion=""):
    """
    Crea el evento físico en el Google Calendar. 
    Ejemplo de inicio_iso: '2026-05-20T10:00:00-03:00'
    """
    service = obtener_servicio_calendar()
    if not service:
        return None
    
    try:
        evento = {
            'summary': resumen,
            'description': descripcion,
            'start': {
                'dateTime': inicio_iso,
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
            'end': {
                'dateTime': fin_iso,
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
            'reminders': {
                'useDefault': True,
            },
        }

        # Insertamos el evento en el calendario principal
        evento_creado = service.events().insert(calendarId='primary', body=evento).execute()
        return evento_creado.get('htmlLink')
    except Exception as e:
        st.error(f"Error al escribir en Google Calendar: {e}")
        return None