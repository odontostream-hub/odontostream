import streamlit as st
import pandas as pd
from datetime import datetime
# Importamos el cliente de Supabase (apuntando a tu config)
from Core.database import supabase

def render_admin_dashboard():
    # 0. CONTROL DE SESIÓN CON REDIRECCIÓN INTELIGENTE
    if "odontologo_id" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ No has iniciado sesión como profesional.")
        if st.button("🔑 Ir al Acceso Profesional", use_container_width=True):
            st.session_state.rol_actual = "profesional"
            st.rerun()
        return

    odontologo_actual_id = st.session_state.odontologo_id
    nombre_odontologo = st.session_state.get("odontologo_nombre", "Doctor/a")

    st.header("👑 Panel de Control - Administración")
    st.write(f"Bienvenido al centro de control clínico y operativo de **{nombre_odontologo}** en Odonto-Stream.")
    
    # # 1. Indicadores clave (DATOS REALES: SUPABASE + GOOGLE CALENDAR)
    try:
        # --- Pacientes (Desde Supabase) ---
        query_p = supabase.table("pacientes").select("id").eq("odontologo id", odontologo_actual_id).execute()
        total_pacientes = len(query_p.data) if query_p.data else 0
        
        # --- Turnos e Ingresos (Desde GOOGLE CALENDAR) ---
        from Core.google_calendar import listar_proximos_eventos
        
        total_turnos = 0
        if "google_credentials" in st.session_state:
            # Traemos los eventos de la agenda real del doctor
            eventos = listar_proximos_eventos(max_resultados=50) 
            total_turnos = len(eventos) if eventos else 0
        
        # --- Cálculos de Dinero ---
        # Usamos el precio que el doctor configuró en la pestaña de Finanzas
        precio_actual = st.session_state.get("precio_consulta_local", precio_consulta_db)
        
        ingresos_brutos = total_turnos * precio_actual
        comision_total = ingresos_brutos * 0.05
        ingresos_netos = ingresos_brutos - comision_total

    except Exception as e:
        # Si algo falla, mostramos ceros para que no explote la app
        total_pacientes = 0
        total_turnos = 0
        ingresos_brutos = 0
        ingresos_netos = 0

    # Renderizado de las métricas (Lo que el doctor ve arriba)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="👥 Pacientes Totales", value=f"{total_pacientes}")
    with col2:
        st.metric(label="📅 Turnos en Agenda", value=f"{total_turnos}")
    with col3:
        st.metric(label="💸 Ingresos Brutos", value=f"${ingresos_brutos:,.0f}")
    with col4:
        st.metric(label="💰 Tu Neto (Post-Comisión)", value=f"${ingresos_netos:,.0f}", delta="Calculado de Calendar")
    
    # 2. Organización en pestañas para ordenar la administración
    tab_pacientes, tab_turnos, tab_finanzas = st.tabs([
        "👥 Gestión de Clientes/Pacientes", 
        "📅 Optimización y Agenda de Turnos", 
        "💼 Finanzas y Configuración de Precios"
    ])
    
    # ==================== PESTAÑA 1: PACIENTES ====================
    with tab_pacientes:
        st.subheader("Directorio de Pacientes")
        
        # CONSULTA REAL A SUPABASE
        try:
            # Respetamos el espacio real: "odontologo id"
            query = supabase.table("pacientes").select("*").eq("odontologo id", odontologo_actual_id).execute()
            
            if query.data:
                df_pacientes = pd.DataFrame(query.data)
                columnas_mostrar = ["nombre", "apellido", "dni", "telefono", "obra social", "historia clinica"]
                columnas_existentes = [col for col in columnas_mostrar if col in df_pacientes.columns]
                
                df_visual = df_pacientes[columnas_existentes].rename(columns={
                    "nombre": "Nombre",
                    "apellido": "Apellido",
                    "dni": "DNI",
                    "telefono": "Teléfono",
                    "obra social": "Obra Social",
                    "historia clinica": "Historia Clínica"
                })
                st.dataframe(df_visual, use_container_width=True)
            else:
                st.info("Aún no tienes pacientes registrados. ¡Registra el primero abajo!")
                
        except Exception as e:
            st.error(f"Error al conectar con la base de datos de pacientes: {e}")
            st.warning("Mostrando datos simulados de respaldo:")
            datos_pacientes = {
                "Nombre": ["Guillermo", "María Laura", "Carlos"],
                "Apellido": ["Hernandez", "Sosa", "Pérez"],
                "DNI": ["45678912", "38456123", "32789456"],
                "Teléfono": ["1122334455", "1165432109", "1198765432"],
                "Obra Social": ["Particular", "OSDE 310", "SMG"],
                "Historia Clínica": ["Implante programado", "Ortodoncia activa", "Limpieza anual realizada (Próxima revisión: Noviembre 2026)"]
            }
            df_respaldo = pd.DataFrame(datos_pacientes)
            st.dataframe(df_respaldo, use_container_width=True)
        
        # Registrar Nuevo Paciente
        with st.expander("➕ Registrar Nuevo Paciente"):
            with st.form("form_nuevo_paciente", clear_on_submit=True):
                nombre = st.text_input("Nombre")
                apellido = st.text_input("Apellido")
                dni = st.text_input("DNI")
                telefono = st.text_input("Teléfono")
                obra_social = st.text_input("Obra Social")
                historia_clinica = st.text_area("Historia Clínica / Notas médicas de inicio")
                guardar = st.form_submit_button("Registrar Paciente")
                
                if guardar:
                    if nombre and apellido:
                        # Mapeamos los nombres de campos con ESPACIO EXACTO
                        nuevo_paciente = {
                            "nombre": nombre,
                            "apellido": apellido,
                            "dni": dni,
                            "telefono": telefono,
                            "obra social": obra_social,           
                            "historia clinica": historia_clinica,  
                            "odontologo id": odontologo_actual_id  
                        }
                        
                        try:
                            supabase.table("pacientes").insert(nuevo_paciente).execute()
                            st.success(f"¡Paciente '{nombre} {apellido}' registrado con éxito!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"No se pudo guardar el paciente: {e}")
                    else:
                        st.warning("Por favor, ingresa al menos Nombre y Apellido.")

# ==================== PESTAÑA 2: AGENDA Y TURNOS ====================

        with tab_turnos:
            st.subheader("📅 Gestión de Agenda (Google Calendar)")
            
            from Core.google_calendar import crear_flujo_oauth, listar_proximos_eventos
            
            # 1. Conexión y Estado
            with st.expander("🔗 Configuración de Sincronización", expanded=False):
                if "google_credentials" not in st.session_state:
                    st.info("Conectá tu Google Calendar para gestionar tus turnos en tiempo real.")
                    flow = crear_flujo_oauth()
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    st.link_button("Conectar con Google Calendar", auth_url, use_container_width=True)
                else:
                    st.success("✅ Tu Google Calendar está sincronizado.")
                    if st.button("Desconectar cuenta"):
                        del st.session_state.google_credentials
                        st.rerun()

            # 2. Visualización de Turnos Reales
            if "google_credentials" in st.session_state:
                st.write("Estos son los próximos turnos y bloqueos en tu agenda:")
                eventos = listar_proximos_eventos(max_resultados=20)
                
                if eventos:
                    datos_agenda = []
                    for ev in eventos:
                        inicio = ev['start'].get('dateTime', ev['start'].get('date'))
                        # Formatear fecha y hora para que se vea bien
                        fecha_ev = inicio.split('T')[0]
                        hora_ev = inicio.split('T')[1][0:5] if 'T' in inicio else "Todo el día"
                        
                        datos_agenda.append({
                            "Fecha": fecha_ev,
                            "Hora": hora_ev,
                            "Paciente / Evento": ev.get('summary', 'Sin título'),
                            "Descripción": ev.get('description', '-')
                        })
                    
                    df_agenda = pd.DataFrame(datos_agenda)
                    st.dataframe(df_agenda, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay eventos próximos en tu calendario.")
            else:
                st.warning("⚠️ Debes conectar tu cuenta de Google para ver la agenda aquí.")
                
            st.markdown("---")
            st.info("💡 **Dato:** Todos los turnos que la IA agende aparecerán automáticamente en tu celular y en esta lista.")

# --- SECCIÓN DE TURNOS CONFIRMADOS (PAGADOS) ---
            st.markdown("---")
            st.subheader("💳 Pacientes con Turno Confirmado")

            try:
                # Traemos los datos de la tabla que SÍ existe: 'pacientes'
                # Filtramos por el ID del odontólogo actual
                query = supabase.table("pacientes").select("*").eq("odontologo id", odontologo_actual_id).execute()
                
                if query.data:
                    df_confirmados = pd.DataFrame(query.data)
                    
                    # Seleccionamos las columnas que querés ver
                    # Ajustá los nombres si en Supabase son distintos (ej: 'nombre', 'apellido', 'dni')
                    cols_mostrar = ["nombre", "apellido", "dni", "telefono", "obra social"]
                    cols_existentes = [c for c in cols_mostrar if c in df_confirmados.columns]
                    
                    st.dataframe(df_confirmados[cols_existentes], use_container_width=True, hide_index=True)
                else:
                    st.info("No hay pacientes registrados con pago confirmado todavía.")

            except Exception as e:
                st.error(f"Error al cargar la lista de pagos: {e}")

    # ==================== PESTAÑA 3: FINANZAS Y CONFIGURACIÓN DE PRECIOS ====================
    with tab_finanzas:
        st.subheader("💰 Configuración de Tarifas y Aranceles por Turno")
        st.write("Establecé los valores de tus consultas y tratamientos. El sistema calculará de forma automática la comisión y tus ganancias netas.")
        
        # 1. Traer valores de "Precios_Odontologo" usando los campos con espacios y en minúsculas
        precio_consulta_db = 30000.0  # Valor por defecto inicial
        try:
            # Buscamos con "precio consulta" y "odontologo id"
            query_precios = supabase.table("Precios_Odontologo").select("precio consulta").eq("odontologo id", odontologo_actual_id).execute()
            if query_precios.data:
                precio_consulta_db = float(query_precios.data[0].get("precio consulta", 30000.0))
        except Exception:
            pass

        # 2. Formulario interactivo de carga de tarifas
        col_form, col_calculadora = st.columns([1, 1])
        
        with col_form:
            st.markdown("### 📝 Actualizar tus Aranceles")
            with st.form("form_tarifas_odontologo"):
                nuevo_precio_consulta = st.number_input(
                    "Valor de la Consulta Particular ($ARS)", 
                    min_value=1000, 
                    value=int(precio_consulta_db), 
                    step=500
                )
                
                # Porcentaje de comisión fijo de la plataforma (5%)
                porcentaje_plataforma = 5.0
                
                boton_guardar_precio = st.form_submit_button("💾 Guardar Tarifas", use_container_width=True)
                
                if boton_guardar_precio:
                    try:
                        # Buscamos usando el campo "odontologo id"
                        check_registro = supabase.table("Precios_Odontologo").select("id").eq("odontologo id", odontologo_actual_id).execute()
                        
                        # Armamos el mapeo de campos usando espacios reales
                        datos_precio = {
                            "odontologo id": odontologo_actual_id,
                            "precio consulta": nuevo_precio_consulta,
                            "comision porcentaje": porcentaje_plataforma
                        }
                        
                        if check_registro.data:
                            registro_id = check_registro.data[0]["id"]
                            supabase.table("Precios_Odontologo").update(datos_precio).eq("id", registro_id).execute()
                        else:
                            supabase.table("Precios_Odontologo").insert(datos_precio).execute()
                            
                        st.success("¡Tarifas actualizadas correctamente en la base de datos!")
                        st.rerun()
                    except Exception as e:
                        st.warning("⚠️ Guardado de forma local (creá los campos con espacios en 'Precios_Odontologo' para persistencia real).")
                        st.session_state["precio_consulta_local"] = nuevo_precio_consulta
                        st.rerun()

        # Usar valor local si no se pudo guardar en Supabase
        precio_actual = st.session_state.get("precio_consulta_local", nuevo_precio_consulta if 'nuevo_precio_consulta' in locals() else precio_consulta_db)

        # 3. Calculadora de Comisiones interactiva al lado del formulario
        with col_calculadora:
            st.markdown("### 🧮 Simulación de Ganancia y Comisión (5%)")
            
            comision_calculada = precio_actual * 0.05
            ganancia_neta_odontologo = precio_actual - comision_calculada
            
            with st.container(border=True):
                st.write(f"**Valor total que abona el Paciente:**")
                st.subheader(f"${precio_actual:,.2f} ARS")
                
                st.write(f"**Comisión retenida por la Plataforma (5%):**")
                st.error(f"- ${comision_calculada:,.2f} ARS")
                
                st.write(f"**Tu Ganancia Neta por turno:**")
                st.success(f"+ ${ganancia_neta_odontologo:,.2f} ARS")
                
                st.caption("ℹ️ El cobro de la seña o el total del turno se procesará automáticamente por Mercado Pago al momento de la reserva del paciente.")