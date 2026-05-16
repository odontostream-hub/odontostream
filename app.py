import re
import os
import base64
import streamlit as st
import pandas as pd
import datetime
import mercadopago

# --- INICIALIZACIÓN DE MERCADO PAGO ---
# Usamos session_state para que el estado de conexión sea visible en toda la app
if "mp_conectado" not in st.session_state:
    try:
        sdk = mercadopago.SDK(st.secrets["MP_ACCESS_TOKEN"])
        st.session_state.mp_conectado = True
    except Exception as e:
        st.session_state.mp_conectado = False

# --- IMPORTACIONES SINCRONIZADAS ---
from Core.ai_engine import DentalAI
from Core.google_calendar import crear_flujo_oauth, obtener_servicio_calendar, listar_proximos_eventos,registrar_turno_en_google

# Importaciones de tus módulos de interfaz
from modules.admin_panel.render_admin_dashboard import render_admin_dashboard
from modules.patient_panel.render_patient_portal import render_patient_portal

# Cliente de Supabase
from Core.database import supabase 

# Configuración de página con estilo odontológico
st.set_page_config(
    page_title="Odonto-Stream", 
    layout="wide", 
    page_icon="🦷"
)
st.markdown("""
    <style>
    /* Oculta el menú de tres puntos arriba a la derecha */
    #MainMenu {visibility: hidden;}
    
    /* Oculta la barra de estado de Streamlit abajo de todo */
    footer {visibility: hidden;}
    
    /* Oculta el botón rojo de Deploy de arriba */
    .stAppDeployButton {display: none !important;}
    
    /* Oculta la barra superior de color por defecto */
    header {visibility: hidden;}
    
    /* Elimina el espacio vacío superior para que empiece bien arriba */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 2rem;
    }
    
    /* Estilizado premium para los botones principales */
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        border-color: #00a8cc;
        color: #00a8cc;
        box-shadow: 0 4px 12px rgba(0, 168, 204, 0.15);
    }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE CAPTURA DE TOKEN DE GOOGLE (PUENTE) ---
query_params = st.query_params

if "code" in query_params and "google_credentials" not in st.session_state:
    try:
        flow = crear_flujo_oauth()
        flow.fetch_token(code=query_params["code"])
        creds = flow.credentials
        st.session_state.google_credentials = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes
        }
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Error al procesar el acceso de Google: {e}")

# -------------------------------------------------------------------------
# 🔌 RADARES DE MERCADO PAGO (VINCULACIÓN + PAGOS)
# -------------------------------------------------------------------------

# 1. RADAR PARA VINCULAR LA CUENTA DEL DOCTOR (Viene del botón azul)
if "code" in query_params and st.session_state.get("logged_in"):
    mp_code = query_params.get("code")
    # Si el código NO es de Google (que empiezan con 4/), entonces es de MP
    if mp_code and not mp_code.startswith("4/"):
        try:
            import requests
            from Core.database import guardar_credenciales_mp
            
            url_mp = "https://api.mercadopago.com/oauth/token"
            payload = {
                "client_id": st.secrets["ML_CLIENT_ID"],
                "client_secret": st.secrets["ML_CLIENT_SECRET"],
                "grant_type": "authorization_code",
                "code": mp_code,
                "redirect_uri": "https://www.odontostream.com.ar/"
            }
            res = requests.post(url_mp, data=payload).json()
            
            if "access_token" in res:
                guardar_credenciales_mp(
                    user_id=st.session_state.odontologo_id,
                    access_token=res["access_token"],
                    public_key=res["public_key"],
                    refresh_token=res.get("refresh_token")
                )
                st.success("¡Cuenta de Mercado Pago vinculada!")
                st.balloons()
                st.query_params.clear()
                st.rerun()
        except Exception as e:
            st.error(f"Error al vincular cuenta: {e}")

# 2. RADAR DE PAGO EXITOSO (Viene de un paciente que pagó un turno)
if "pago" in query_params and query_params["pago"] == "exitoso":
    try:
        st.balloons()
        st.success("¡Pago recibido correctamente! Agendando tu turno...")
        datos_pendientes = st.session_state.get("datos_turno_pendiente")
        id_doc = st.session_state.get("odontologo_id_actual")

        if datos_pendientes:
            from Core.database import guardar_turno, registrar_pago
            guardar_turno(datos_pendientes)
            
            precio = st.session_state.get("precio_consulta", 30000)
            registrar_pago({
                "odontologo_id": id_doc,
                "monto": precio,
                "comision": precio * 0.05,
                "paciente": datos_pendientes.get("paciente_nombre")
            })
            
            del st.session_state["datos_turno_pendiente"]
            st.query_params.clear()
            st.info("Turno agendado. Ya podés volver al chat.")
    except Exception as e:
        st.error(f"Hubo un drama al registrar el pago: {e}")

# --- INYECCIÓN DE CSS PARA OCULTAR MARCAS... (Esto ya lo tenés en la 54)

# --- INYECCIÓN DE CSS PARA OCULTAR MARCAS DE STREAMLIT Y LIMPIAR LA INTERFAZ ---
st.markdown("""
    <style>
        /* Oculta el menú de tres puntos de Streamlit arriba a la derecha */
        #MainMenu {visibility: hidden;}
        
        /* Oculta la barra de estado de Streamlit (Made with Streamlit) abajo de todo */
        footer {visibility: hidden;}
        
        /* Oculta la barra superior de color que decora por defecto */
        header {visibility: hidden;}
        
        /* Elimina el espacio vacío superior (padding) que deja la barra oculta */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        
        /* Estilizado premium para los botones principales combinando con el celeste de config.toml */
        .stButton>button {
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            border-color: #00a8cc;
            color: #00a8cc;
            box-shadow: 0 4px 12px rgba(0, 168, 204, 0.15);
        }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZAR ESTADOS DE SESIÓN ---
# "rol_actual" puede ser: "paciente" (público por defecto) o "profesional" (el login del doctor)
if "rol_actual" not in st.session_state:
    st.session_state.rol_actual = "paciente"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "terminos_aceptados" not in st.session_state:
    st.session_state.terminos_aceptados = False
if "modo_demo" not in st.session_state:
    st.session_state.modo_demo = False

# Inicializar IA
try:
    ai_assistant = DentalAI(supabase_client=supabase)
except Exception:
    ai_assistant = None

# --- CONTROLADOR GLOBAL DE CONEXIÓN A SUPABASE ---
def comprobar_conexion_supabase():
    if supabase is None:
        return False
    try:
        # Usamos tu tabla física real con mayúscula y acento: "Odontólogo"
        supabase.table("Odontólogo").select("id").limit(1).execute()
        return True
    except Exception:
        return False

# --- PANTALLA LEGAL PACIENTES ---
def render_terminos_y_condiciones():
    st.subheader("🛡️ Consentimiento de Privacidad y Uso de Datos del Paciente")
    st.write(
        """
        Para garantizar la seguridad de tu información de salud y cumplir con las regulaciones de 
        Protección de Datos Personales (Ley 25.326 en Argentina), necesitamos tu conformidad antes de continuar.
        """
    )
    
    texto_legal = """
    CONVENIO DE CONSENTIMIENTO INFORMADO Y PRIVACIDAD DE PACIENTES:
    
    1. Tratamiento de Datos: Los datos clínicos, síntomas, datos filiatorios (DNI, Teléfono) y fotografías dentales que proporciones en este chat se procesarán de forma estrictamente privada y encriptada en bases de datos seguras (Supabase).
    
    2. Diagnóstico por IA: El análisis de imágenes de caries provisto por la Inteligencia Artificial es una guía orientativa y preventiva de carácter informático. En ningún caso reemplaza el examen físico, clínico ni el diagnóstico definitivo de un odontólogo matriculado.
    
    3. Destino de los datos: Tu información solo se utilizará para facilitar la asignación de turnos con el Dr/a. seleccionado o derivarte de forma segura a especialistas de la red Odonto-Stream si fuera necesario.
    
    4. Pagos y Señas: Al agendar el turno, se requerirá un abono en concepto de seña de manera electrónica a través de la plataforma segura de Mercado Pago. Dicho monto es descontado del total del tratamiento de acuerdo a los precios regulados por el odontólogo.
    """
    
    st.text_area("Términos de Servicio y Política de Privacidad del Paciente", value=texto_legal, height=220, disabled=True)
    
    acepto = st.checkbox("He leído y acepto los Términos de Servicio y la Política de Privacidad de mis datos de salud.")
    
    if st.button("Continuar al Asistente", disabled=not acepto, use_container_width=True):
        st.session_state.terminos_aceptados = True
        st.rerun()

# --- CHAT PÚBLICO PARA PACIENTES (PANTALLA DE ENTRADA) ---
def render_public_patient_chat():
    st.markdown("<h1 style='text-align: center;'>🦷 Odonto-Stream</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #00a8cc;'>Sacá tu turno chateando con nuestra IA en segundos</h3>", unsafe_allow_html=True)
    st.write("---")
    
    col_info, col_chat = st.columns([1, 2])
    
    with col_info:
        st.subheader("📋 ¿Cómo funciona?")
        st.info(
            """
            1. **Saludá a nuestra IA** y contale qué tratamiento o consulta necesitás hacerte.\n
            2. Te va a pedir unos datos básicos (Nombre, DNI, Celular) para registrarte en el sistema de forma segura.\n
            3. Elegís el día y horario que te quede cómodo.\n
            4. ¡Listo! Te generamos el link para abonar la seña y tu turno queda reservado.
            """
        )
        st.markdown("---")
        st.markdown("### 📷 ¿Tenés una radiografía o foto?")
        st.write("Subila acá para que la IA la analice antes de tu consulta:")
        
        foto_clinica = st.file_uploader(
            "Arrastrá tu imagen (JPG, PNG)", 
            type=["jpg", "jpeg", "png"],
            key="public_chat_uploader"
        )
        if foto_clinica is not None:
            st.image(foto_clinica, caption="Imagen cargada correctamente", width=250)
            
    with col_chat:
        st.subheader("💬 Charla con el Asistente Dental")
        
        if "public_messages" not in st.session_state:
            st.session_state.public_messages = [
                {"role": "assistant", "content": "¡Hola! Bienvenido/a a Odonto-Stream. 😊 ¿En qué puedo ayudarte hoy? ¿Querés agendar un turno o hacerme alguna consulta?"}
            ]

        # Mostrar historial de chat
        for message in st.session_state.public_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        prompt = st.chat_input("Escribí tu mensaje acá (ej: 'Quiero un turno para limpieza')...")

        if prompt or (foto_clinica is not None and st.button("🔍 Analizar imagen subida", use_container_width=True)):
            texto_usuario = prompt if prompt else "Por favor, analizá la radiografía que te subí."
            
            st.session_state.public_messages.append({"role": "user", "content": texto_usuario})
            with st.chat_message("user"):
                st.markdown(texto_usuario)

            with st.chat_message("assistant"):
                with st.spinner("Procesando consulta..."):
                    if ai_assistant:
                        try:
                            if foto_clinica is not None:
                                response = ai_assistant.analizar_caries(foto_clinica)
                                if prompt:
                                    response = f"**[Análisis de Imagen]:**\n\n{response}\n\n*Respuesta a tu pregunta:* {prompt}"
                            else:
                                # MODIFICACIÓN: Pasamos los datos del doctor de forma dinámica
                                odontologo_id_consulta = st.session_state.get("odontologo_id", "12345")
                                odontologo_nombre_consulta = st.session_state.get("odontologo_nombre", "Guillermo Hernandez")
                                paciente_email_consulta = st.session_state.get("paciente_email", "paciente@odontostream.com.ar")
                                
                                response = ai_assistant.get_response(
                                    texto_usuario,
                                    odontologo_nombre=odontologo_nombre_consulta,
                                    odontologo_id=odontologo_id_consulta,
                                    localidad_paciente="Florencio Varela",
                                    paciente_email=paciente_email_consulta
                                )
                        except Exception as e:
                            response = f"Error en la IA: {str(e)}"
                    else:
                        response = "El sistema de IA se está reiniciando. Por favor, intentá de nuevo en unos momentos."
                
                st.markdown(response)
                st.session_state.public_messages.append({"role": "assistant", "content": response})

# --- PANTALLA DE LOGIN Y REGISTRO (SOLO ODONTÓLOGOS) ---
def render_login_screen():
    st.markdown("<h1 style='text-align: center;'>🔐 Acceso Profesional</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>Gestión de Turnos, Pacientes e Inteligencia Artificial</h4>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.write("---")
        supabase_online = comprobar_conexion_supabase()
        
        if not supabase_online:
            st.info("💡 **Modo Demostración Activo:** Usá las credenciales de prueba para ingresar.")

        # ESTO ES LO QUE ESTABA CORRIDO:
        tab_login, tab_registro = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse"])

        with tab_login:
            with st.form("form_login"):
                nombre_usuario = st.text_input("Nombre del Odontólogo")
                matricula_usuario = st.text_input("Matrícula (Contraseña)", type="password")
                boton_ingresar = st.form_submit_button("Ingresar al Panel", use_container_width=True)
                
                if boton_ingresar:
                    if nombre_usuario and matricula_usuario:
                        if supabase_online:
                            try:
                                query = supabase.table("Odontólogo").select("*").eq("nombre", nombre_usuario).eq("matricula", matricula_usuario).execute()
                                if query.data:
                                    odontologo = query.data[0]
                                    st.session_state.logged_in = True
                                    st.session_state.odontologo_id = odontologo.get("id", odontologo["matricula"])
                                    st.session_state.odontologo_nombre = f"{odontologo['nombre']} {odontologo['apellido']}"
                                    st.session_state.odontologo_matricula = odontologo["matricula"]
                                    st.session_state.odontologo_email = odontologo.get("email")
                                    st.session_state.modo_demo = False
                                    st.success(f"¡Bienvenido/a Dr. {st.session_state.odontologo_nombre}!")
                                    st.rerun()
                                else:
                                    st.error("❌ Nombre o matrícula incorrectos.")
                            except Exception as e:
                                supabase_online = False
                        
                        if not supabase_online:
                            if nombre_usuario == "Guillermo" and matricula_usuario == "12345":
                                st.session_state.logged_in = True
                                st.session_state.odontologo_id = "12345"
                                st.session_state.odontologo_nombre = "Guillermo Hernandez"
                                st.session_state.odontologo_matricula = "12345"
                                st.session_state.odontologo_email = "guillermo@prueba.com"
                                st.session_state.modo_demo = True
                                st.success("Ingresando en modo local...")
                                st.rerun()
                            else:
                                st.error("❌ En modo demo, ingresá con: Guillermo / 12345")
                
            st.markdown("---")
            with st.expander("¿Problemas con tu acceso?"):
                email_recupero = st.text_input("Correo electrónico registrado", key="email_reset")
                if st.button("Enviar link de recuperación", use_container_width=True):
                    if email_recupero:
                        try:
                            supabase.auth.reset_password_for_email(email_recupero)
                            st.success("📩 ¡Enviado! Revisá tu mail.")
                        except Exception as e:
                            st.error(f"Error: {e}")

        with tab_registro:
            if not supabase_online:
                st.warning("⚠️ El registro no está disponible en modo demostración.")
            else:
                with st.form("form_registro"):
                    st.subheader("📝 Datos Obligatorios")
                    col_reg_1, col_reg_2 = st.columns(2)
                    with col_reg_1:
                        reg_nombre = st.text_input("Nombre *")
                        reg_apellido = st.text_input("Apellido *")
                        reg_email = st.text_input("Correo Electrónico *")
                        reg_matricula = st.text_input("Matrícula Profesional *")
                    with col_reg_2:
                        reg_direccion = st.text_input("Dirección del Consultorio *")
                        reg_especialidad = st.selectbox("Especialidad *", options=["Odontología General", "Ortodoncia", "Endodoncia", "Implantes", "Odontopediatría", "Prótesis", "Cirugía Bucal"])
                        reg_horarios = st.text_input("Horarios de Atención *")
                    
                    # --- BORRÁ LO AZUL Y PEGÁ ESTO ---
                    st.markdown("---")
                    st.warning("📜 **Acuerdo de Servicio y Comisiones**")
                    
                    contrato_profesional = """
                    CONTRATO DE ADHESIÓN AL SISTEMA ODONTO-STREAM:
                    
                    1. COMISIONES: El profesional acepta una comisión del 5% sobre el valor bruto de cada seña procesada por Mercado Pago.
                    2. RESPONSABILIDAD: El odontólogo es el único responsable legal por los diagnósticos y tratamientos realizados.
                    3. PRIVACIDAD: Los datos se procesan bajo la Ley 25.326 de Protección de Datos Personales.
                    """
                    
                    st.text_area("Términos Profesionales", value=contrato_profesional, height=150, disabled=True)
                    
                    acepto_profesional = st.checkbox("He leído y acepto la comisión del 5% y los términos de servicio profesional.")
                    boton_registrar = st.form_submit_button("Crear Cuenta Profesional", use_container_width=True)
                    # --------------------------------
                    
                    if boton_registrar:
                        if not acepto_profesional:
                            st.error("❌ Debes aceptar las comisiones.")
                        elif not (reg_nombre and reg_apellido and reg_email and reg_matricula and reg_direccion):
                            st.error("❌ Completa los campos obligatorios.")
                        else:
                            try:
                                nuevo_odontologo = {
                                    "nombre": reg_nombre.strip(), 
                                    "apellido": reg_apellido.strip(), 
                                    "email": reg_email.strip(),
                                    "matricula": reg_matricula.strip(),
                                    "direccion": reg_direccion.strip(),
                                    "especialidad": reg_especialidad,
                                    "horarios": reg_horarios.strip()
                                }
                                supabase.table("Odontólogo").insert(nuevo_odontologo).execute()
                                st.success("¡Registro exitoso!")
                            except Exception as e:
                                st.error(f"Error: {e}")
        # --- FIN DEL REEMPLAZO ---

def verificar_pago_y_agendar():
    """Esta función revisa si el usuario vuelve de Mercado Pago con éxito."""
    query_params = st.query_params
    if query_params.get("pago") == "exitoso":
        # Marca para no repetir el proceso si refrescan la página
        if "pago_procesado_exitoso" not in st.session_state:
            datos_turno = st.session_state.get("temp_turno_data")
            if datos_turno:
                with st.spinner("💳 Pago confirmado. Agendando turno..."):
                    try:
                        # Armamos las fechas para Google
                        inicio_iso = f"{datos_turno['fecha']}T{datos_turno['hora']}:00-03:00"
                        hora_fin = int(datos_turno['hora'].split(':')[0]) + 1
                        fin_iso = f"{datos_turno['fecha']}T{hora_fin:02d}:00:00-03:00"
                        
                        link = registrar_turno_en_google(
                            resumen=f"Turno: {datos_turno['paciente_nombre']} ({datos_turno['motivo']})",
                            inicio_iso=inicio_iso,
                            fin_iso=fin_iso,
                            descripcion=f"DNI: {datos_turno['dni']} | Tel: {datos_turno['telefono']}"
                        )
                        if link:
                            st.balloons()
                            st.success(f"✅ ¡Turno agendado! [Ver en Google]({link})")
                            st.session_state.pago_procesado_exitoso = True
                    except Exception as e:
                        st.error(f"Error al agendar: {e}")

# --- FUNCIÓN PRINCIPAL ---
def main():
    # --- BARRA LATERAL (CONTROL DE VISTAS GLOBAL) ---
    verificar_pago_y_agendar()
    st.sidebar.title("🦷 Odonto-Stream")
    st.sidebar.markdown("---")
    
    if not st.session_state.logged_in:
        # Si NO está logueado, le damos el botón para alternar entre Paciente y Odontólogo
        if st.session_state.rol_actual == "paciente":
            st.sidebar.write("🔒 **¿Sos profesional?**")
            if st.sidebar.button("🔑 Acceso Profesional / Registro", use_container_width=True):
                st.session_state.rol_actual = "profesional"
                st.rerun()
        else:
            st.sidebar.write("⬅️ **Volver al Portal Público**")
            if st.sidebar.button("💬 Volver al Chat de Turnos", use_container_width=True):
                st.session_state.rol_actual = "paciente"
                st.rerun()
    else:
        # Si SÍ está logueado, la barra lateral tiene sus opciones normales de admin
        menu = st.sidebar.radio(
            "Navegación",
            ["Inicio / Chat IA", "Panel de Control (Admin)", "Portal del Paciente (Vista Previa)", "Agenda"]
        )
        st.sidebar.markdown("---")
        st.sidebar.info(f"👤 Dr/a. {st.session_state.odontologo_nombre}\n\n💼 Rol: Odontólogo")
        
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.rol_actual = "paciente"
            st.session_state.pop("odontologo_id", None)
            st.session_state.pop("odontologo_nombre", None)
            st.session_state.pop("odontologo_matricula", None)
            st.session_state.terminos_aceptados = False
            st.rerun()

    # --- RENDERIZADO SEGÚN EL ROL Y ESTADO ---
    if not st.session_state.logged_in:
        # VISTA PÚBLICA (PACIENTES)
        if st.session_state.rol_actual == "paciente":
            if not st.session_state.terminos_aceptados:
                render_terminos_y_condiciones()
            else:
                render_public_patient_chat()
        # VISTA PROFESIONAL (LOGIN)
        else:
            render_login_screen()
            
    else:
        # SISTEMA INTERNO DEL ODONTÓLOGO LOGUEADO
        if menu == "Inicio / Chat IA":
            render_home_chat()
        elif menu == "Panel de Control (Admin)":
            render_admin_dashboard()
        elif menu == "Portal del Paciente (Vista Previa)":
            render_patient_portal()
        elif menu == "Agenda":
            st.header("📅 Gestión de Turnos - Google Calendar")
            # (Tu código original de calendar...)
            turnos = listar_proximos_eventos()
            if not turnos:
                st.info("No tenés turnos programados.")
            else:
                for t in turnos:
                    st.write(f"🦷 {t.get('summary')} - {t.get('start', {}).get('dateTime')}")

# --- CHAT / HOME INTERNO DEL DOCTOR ---
def render_home_chat():
    st.title(f"Bienvenido, Dr/a. {st.session_state.odontologo_nombre}")
    # (Tu código original de render_home_chat...)
    st.info("Este es tu panel interno de consultas clínicas rápidas.")

if __name__ == "__main__":
    main()