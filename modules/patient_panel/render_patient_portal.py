import streamlit as st
import datetime
import os  # Importante para leer las variables del sistema
# Importamos load_dotenv para leer tu archivo .env
from dotenv import load_dotenv 

# Importamos la clase DentalAI que tiene el motor de visión
from Core.ai_engine import DentalAI

# Importamos la conexión a base de datos para guardar de verdad los turnos
from Core.database import supabase

# --- IMPORTAMOS MERCADO PAGO ---
import mercadopago

# Cargamos las variables de tu archivo .env al iniciar
load_dotenv()

def render_patient_portal():
    # --- LÓGICA DE PROCESAMIENTO DE PAGO ---
    query_params = st.query_params
    
    # Si volvemos de MP y el pago fue exitoso
    if query_params.get("pago") == "exitoso":
        if "pago_procesado" not in st.session_state:
            datos_pendientes = st.session_state.get("temp_turno_data")
            
            if datos_pendientes:
                with st.spinner("💳 ¡Pago verificado! Finalizando reserva..."):
                    try:
                        # 1. Guardar en la tabla 'turnos' de Supabase
                        from Core.database import guardar_turno
                        guardar_turno(datos_pendientes)
                        
                        # 2. Registrar en el Google Calendar del doctor
                        from Core.google_calendar import registrar_turno_en_google
                        
                        # Armamos el horario para Google (ISO Format)
                        inicio_iso = f"{datos_pendientes['fecha']}T{datos_pendientes['hora']}:00-03:00"
                        # Estimamos 1 hora de duración
                        hora_fin = int(datos_pendientes['hora'].split(':')[0]) + 1
                        fin_iso = f"{datos_pendientes['fecha']}T{hora_fin:02d}:00:00-03:00"
                        
                        link_google = registrar_turno_en_google(
                            resumen=f"Turno: {datos_pendientes['paciente_nombre']} ({datos_pendientes['motivo']})",
                            inicio_iso=inicio_iso,
                            fin_iso=fin_iso,
                            descripcion=f"DNI: {datos_pendientes['dni']} | Tel: {datos_pendientes['telefono']}"
                        )
                        
                        st.balloons()
                        st.success("✅ ¡Turno confirmado y agendado con éxito!")
                        st.session_state["pago_procesado"] = True
                        
                        # Limpiamos los datos temporales
                        del st.session_state["temp_turno_data"]
                    except Exception as e:
                        st.error(f"Hubo un error al registrar el turno: {e}")
    # --- FIN DE LÓGICA DE PAGO ---

    st.header("👥 Portal del Paciente")
    # ... (el resto de tu código igual)

def render_patient_portal():
    st.header("👥 Portal del Paciente")
    st.write("Espacio dedicado para que los pacientes puedan gestionar sus turnos, ver su historial y subir sus radiografías.")
    
    # 1. CARGA DINÁMICA DE PACIENTES DESDE SUPABASE
    pacientes_opciones = []
    pacientes_datos = {}
    
    try:
        # Traemos los pacientes reales de la base de datos
        q_pacientes = supabase.table("pacientes").select("*").execute()
        if q_pacientes.data:
            for p in q_pacientes.data:
                nombre_completo = f"{p['nombre']} {p['apellido']}"
                pacientes_opciones.append(nombre_completo)
                pacientes_datos[nombre_completo] = p
    except Exception as e:
        pass

    # Fallback por si la base está vacía o falla
    if not pacientes_opciones:
        pacientes_opciones = ["Guillermo Hernandez", "María Laura Sosa", "Carlos Pérez"]
        pacientes_datos = {
            "Guillermo Hernandez": {"id": "1", "nombre": "Guillermo", "apellido": "Hernandez", "dni": "45678912", "telefono": "1122334455", "obra social": "Particular", "historia clinica": "Tratamiento estético y preventivo.", "odontologo id": "1"},
            "María Laura Sosa": {"id": "2", "nombre": "María Laura", "apellido": "Sosa", "dni": "38456123", "telefono": "1165432109", "obra social": "OSDE 310", "historia clinica": "Ortodoncia activa.", "odontologo id": "1"},
            "Carlos Pérez": {"id": "3", "nombre": "Carlos", "apellido": "Pérez", "dni": "32789456", "telefono": "1198765432", "obra social": "SMG", "historia clinica": "Limpieza anual realizada.", "odontologo id": "1"}
        }

    paciente_simulado = st.selectbox("Seleccionar Paciente (Simulación de ingreso)", pacientes_opciones)
    paciente_actual = pacientes_datos[paciente_simulado]
    
    st.info(f"Sesión activa como: **{paciente_simulado}**")
    
    tab_perfil, tab_turnos_p, tab_analisis_ia = st.tabs([
        "📄 Mi Ficha Clínica", 
        "📅 Reservar Turno", 
        "🔍 Análisis de Caries con IA"
    ])
    
    # ==================== PESTAÑA 1: FICHA CLÍNICA ====================
    with tab_perfil:
        st.subheader("Historial Odontológico")
        # Usamos los campos con espacio de tu base de datos: 'historia clinica' y 'obra social'
        historia = paciente_actual.get("historia clinica", "Ninguna historia clínica cargada.")
        obrasocial = paciente_actual.get("obra social", "Particular")
        
        st.write(f"**Plan de tratamiento actual:** {historia}")
        st.write(f"**Obra Social / Cobertura:** {obrasocial}")
        st.write("**Próxima revisión recomendada:** Noviembre 2026")
        st.markdown(f"""
        * **Paciente:** {paciente_actual.get('nombre')} {paciente_actual.get('apellido')}
        * **DNI:** {paciente_actual.get('dni', 'No especificado')}
        * **Teléfono de contacto:** {paciente_actual.get('telefono', 'No especificado')}
        """)

# ==================== PESTAÑA 2: RESERVAR TURNO (CHAT IA PREMIUM) ====================
    with tab_turnos_p:
        st.subheader("🤖 Asistente de Turnos Virtual")
        st.write("Escribile a nuestra IA para consultar disponibilidad y agendar tu cita al instante.")

        # Inicializamos el chat en la sesión si no existe
        if "messages_turno" not in st.session_state:
            st.session_state.messages_turno = []

        # Mostramos el historial del chat
        for message in st.session_state.messages_turno:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Entrada del usuario
        if prompt := st.chat_input("Ej: Hola, quiero un turno para limpieza"):
            # 1. Guardamos el mensaje del usuario
            st.session_state.messages_turno.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # 2. La IA genera la respuesta usando el motor que ya conectamos a Google y Supabase
            with st.chat_message("assistant"):
                with st.spinner("Consultando agenda oficial..."):
                    ai_engine = DentalAI(supabase_client=supabase)
                    # Le pasamos los datos del odontólogo actual para que sepa de quién es la agenda
                    respuesta = ai_engine.get_response(
                        prompt, 
                        odontologo_nombre="Guillermo Hernandez", 
                        odontologo_id="1" # O el ID que corresponda
                    )
                    st.markdown(respuesta)
            
            # 3. Guardamos la respuesta de la IA
            st.session_state.messages_turno.append({"role": "assistant", "content": respuesta})
# ==================== BLOQUE DE PAGO (AGREGAR AL FINAL DE TAB_TURNOS_P) ====================
            st.markdown("---")
            st.subheader("💳 Confirmar y Reservar")
            st.write("Si ya acordaste el horario con la IA, seleccionalo abajo para pagar la seña y confirmar.")

            col_f, col_h = st.columns(2)
            with col_f:
                fecha_turno = st.date_input("Fecha del turno", datetime.date.today())
            with col_h:
                hora_turno = st.time_input("Hora del turno", datetime.time(9, 0))

            motivo_turno = st.text_input("Motivo breve (ej: Limpieza, Consulta)", "Consulta General")

            if st.button("Generar Pago de Seña", use_container_width=True):
                # 1. Cargamos la mochila con los datos del paciente y el turno
                st.session_state["temp_turno_data"] = {
                    "fecha": fecha_turno.strftime("%Y-%m-%d"),
                    "hora": hora_turno.strftime("%H:%M"),
                    "motivo": motivo_turno,
                    "paciente_nombre": paciente_simulado,
                    "dni": paciente_actual.get('dni'),
                    "telefono": paciente_actual.get('telefono')
                }

                # 2. Configuramos Mercado Pago (Usando tu Token del .env)
                sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))
                
                preference_data = {
                    "items": [
                        {
                            "title": f"Seña Turno Odontológico - {paciente_simulado}",
                            "quantity": 1,
                            "unit_price": 2000, # Podés cambiar el monto de la seña acá
                            "currency_id": "ARS"
                        }
                    ],
                    "back_urls": {
                        "success": "http://localhost:8501/?pago=exitoso", # Cambiá esto por tu URL de producción después
                        "failure": "http://localhost:8501/?pago=error",
                        "pending": "http://localhost:8501/?pago=pendiente"
                    },
                    "auto_return": "approved",
                }

                preference_response = sdk.preference().create(preference_data)
                url_pago = preference_response["response"]["init_point"]

                st.success("¡Preferencia de pago creada!")
                st.link_button("🚀 Pagar Seña con Mercado Pago", url_pago, type="primary", use_container_width=True)
    # ==================== PESTAÑA 3: ANÁLISIS DE CARIES CON IA ====================
    with tab_analisis_ia:
        st.subheader("Análisis Preventivo de Caries por Imagen")
        st.write("Subí una foto clara de tus dientes o una radiografía dental para que nuestro motor de Inteligencia Artificial haga una pre-evaluación automática.")
        
        # El cargador de archivos para el paciente
        archivo_imagen = st.file_uploader(
            "Cargá una foto o radiografía (Formatos permitidos: JPG, PNG)", 
            type=["jpg", "jpeg", "png"],
            key="portal_preview_uploader"
        )
        
        if archivo_imagen is not None:
            # Mostramos la foto que subió el usuario
            st.image(archivo_imagen, caption="Imagen cargada correctamente", use_container_width=True)
            
            # Botón para disparar la lógica de análisis real
            if st.button("Iniciar Escaneo Dental con IA", key="btn_preview_ia"):
                with st.spinner("La Inteligencia Artificial está analizando detalladamente la imagen... Por favor, aguardá un momento."):
                    try:
                        # Inicializamos el motor de la IA manejando la conexión de Supabase de forma segura
                        ai_engine = DentalAI(supabase_client=supabase) if supabase is not None else DentalAI()
                        
                        resultado_analisis = ai_engine.analizar_caries(archivo_imagen)
                        
                        # Mostramos el resultado en pantalla bien presentado
                        st.success("¡Análisis completado con éxito!")
                        st.markdown("### 📋 Informe del Asistente Dental IA")
                        st.write(resultado_analisis)
                        
                    except Exception as e:
                        st.error(f"Hubo un problema al conectar con el servidor de análisis: {str(e)}")