import streamlit as st
from core.ai_engine import DentalAI
from modules.admin_panel import render_admin_dashboard
from modules.patient_panel import render_patient_portal

# Configuración de página con estilo odontológico (Limpio y profesional)
st.set_page_config(page_title="Odonto-Stream", layout="wide", page_icon="🦷")

# Inicializar IA
ai_assistant = DentalAI()

def main():
    # --- BARRA LATERAL (MENÚS) ---
    st.sidebar.title("🦷 Odonto-Stream")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.radio(
        "Navegación",
        ["Inicio / Chat IA", "Agenda de Turnos", "Pacientes", "Presupuestos", "Configuración"]
    )

    st.sidebar.markdown("---")
    st.sidebar.info("Usuario: Dr. Alejandro Hernandez\nRol: Administrador")

    # --- LÓGICA DE NAVEGACIÓN ---
    if menu == "Inicio / Chat IA":
        render_home_chat()
    elif menu == "Agenda de Turnos":
        st.header("📅 Gestión de Turnos")
        # Aquí llamaríamos a un módulo de calendario
    elif menu == "Pacientes":
        st.header("👤 Historias Clínicas")
        # Aquí el buscador de pacientes y fichas
    elif menu == "Presupuestos":
        st.header("💰 Cotizador de Tratamientos")
        # Módulo para generar PDFs

def render_home_chat():
    st.title("Bienvenido a tu Consultorio Virtual")
    
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Resumen del Día")
        st.info("Tienes 5 turnos programados para hoy.")
        # Aquí iría un dashboard rápido (KPIs de facturación, etc.)

    with col2:
        st.subheader("Asistente Odonto-IA")
        st.caption("Consultas rápidas sobre protocolos o agenda.")
        
        # Contenedor del Chat
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("¿En qué puedo ayudarte?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                response = ai_assistant.get_response(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
