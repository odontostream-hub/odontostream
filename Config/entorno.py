import streamlit as st

def obtener_url_base():
    """
    Detecta automáticamente si estás en tu compu, 
    en el link de Streamlit Cloud o en tu dominio oficial.
    """
    # Obtenemos el host actual de los headers de Streamlit
    try:
        # Esto funciona en versiones modernas de Streamlit
        host = st.context.headers.get("host", "")
    except:
        host = ""

    if "localhost" in host or "127.0.0.1" in host:
        return "http://localhost:8501"
    elif "streamlit.app" in host:
        return "https://odontostream-emfdr5krkup3efwfakwrjw.streamlit.app"
    else:
        # Tu dominio oficial
        return "https://www.odontostream.com.ar"

def obtener_back_urls():
    """Genera los links de retorno para Mercado Pago según el entorno."""
    base = obtener_url_base()
    return {
        "success": f"{base}/?pago=exitoso",
        "failure": f"{base}/?pago=fallido",
        "pending": f"{base}/?pago=pendiente"
    }