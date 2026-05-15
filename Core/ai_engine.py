import os
import base64
import mercadopago
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
# --- IMPORTAMOS TU LÓGICA DE GOOGLE ---
from Core.google_calendar import listar_proximos_eventos
# --- IMPORTAMOS TU NUEVA LÓGICA DE ENTORNO ---
from Config.entorno import obtener_back_urls

load_dotenv()

class DentalAI:
    def __init__(self, supabase_client=None):
        # 1. Busca la llave principal en el .env (Local) o Secrets (Nube)
        self.key1 = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
        
        # 2. Busca la llave de RESPALDO en el secrets.toml (Ya no está a la vista acá)
        self.key2 = st.secrets.get("GROQ_API_KEY_2")
        
        # Cliente principal
        self.client = Groq(api_key=self.key1)
        
        # TUS MODELOS ORIGINALES (Intactos)
        self.text_model = "llama-3.1-8b-instant"
        self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"
        
        self.supabase = supabase_client
        self.mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        self.sdk = mercadopago.SDK(self.mp_access_token) if self.mp_access_token else None

    def _request_with_failover(self, model, messages, temperature):
        """ESTE ES EL RESPALDO: Si falla la primera, usa la segunda API automáticamente"""
        try:
            return self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
        except Exception as e:
            print(f"⚠️ Falló API 1: {e}. Saltando al tanque de reserva...")
            # Si key2 existe en secrets, lo usa. Si no, tirará el error correspondiente.
            backup_client = Groq(api_key=self.key2)
            return backup_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )

    def obtener_token_odontologo(self, odontologo_id):
        if not self.supabase or not odontologo_id:
            return st.secrets.get("MP_ACCESS_TOKEN")
        try:
            res = self.supabase.table("credenciales_mercadopago").select("access_token").eq("user_id", odontologo_id).execute()
            if res.data:
                return res.data[0]["access_token"]
        except Exception as e:
            print(f"Error: {e}")
        return st.secrets.get("MP_ACCESS_TOKEN")

    def obtener_precio_odontologo(self, odontologo_id):
        precio_default = 1000.0 
        if not self.supabase or not odontologo_id:
            return precio_default
        try:
            query = self.supabase.table("Precios_Odontologo").select("precio consulta").eq("odontologo id", odontologo_id).execute()
            if query.data:
                return float(query.data[0].get("precio consulta", precio_default))
        except:
            pass
        return precio_default

    def registrar_o_obtener_paciente(self, nombre, apellido, dni, telefono):
        if not self.supabase: return None
        try:
            res = self.supabase.table("pacientes").select("*").eq("dni", dni).execute()
            if res.data:
                return res.data[0]
            else:
                nuevo = {"nombre": nombre, "apellido": apellido, "dni": dni, "telefono": telefono}
                ins = self.supabase.table("pacientes").insert(nuevo).execute()
                return ins.data[0] if ins.data else None
        except Exception as e:
            print(f"Error Supabase Paciente: {e}")
            return None

    def crear_link_pago_turno(self, motivo, paciente_nombre, odontologo_id):
        token_doc = self.obtener_token_odontologo(odontologo_id)
        sdk_dinamico = mercadopago.SDK(token_doc) 
        precio_total = self.obtener_precio_odontologo(odontologo_id)
        mi_comision = precio_total * 0.05
        
        # USAMOS LAS URLS DINÁMICAS SEGÚN EL ENTORNO
        urls_dinamicas = obtener_back_urls()
        
        try:
            preference_data = {
                "items": [
                    {
                        "title": f"Turno {motivo}: {paciente_nombre}",
                        "quantity": 1,
                        "unit_price": precio_total, 
                        "currency_id": "ARS"
                    }
                ],
                "marketplace_fee": mi_comision,
                "back_urls": urls_dinamicas,
                "auto_return": "approved",
            }
            res = sdk_dinamico.preference().create(preference_data)
            return res["response"].get("init_point"), precio_total
        except:
            return None, precio_total

    def get_response(self, user_input, odontologo_nombre="el especialista", odontologo_id=None, **kwargs):
        try:
            # 1. LEER GOOGLE CALENDAR REAL
            contexto_agenda = "Horarios ya ocupados en Google Calendar:\n"
            try:
                eventos = listar_proximos_eventos(max_results=10)
                if eventos:
                    for ev in eventos:
                        inicio = ev['start'].get('dateTime', ev['start'].get('date'))
                        contexto_agenda += f"- {ev.get('summary')}: {inicio}\n"
                else:
                    contexto_agenda += "La agenda está libre.\n"
            except:
                contexto_agenda += "No pude acceder al calendario.\n"

            # 2. GENERAR LINK DE PAGO DINÁMICO
            id_final = odontologo_id or st.session_state.get("odontologo_id", "ID_GENERAL")
            
            try:
                monto_turno = self.obtener_precio_odontologo(id_final)
                token_del_doc = self.obtener_token_odontologo(id_final)
                mi_comision = monto_turno * 0.05
                sdk_dinamico = mercadopago.SDK(token_del_doc) if token_del_doc else self.sdk
                
                # USAMOS LAS URLS DINÁMICAS ACÁ TAMBIÉN
                urls_dinamicas = obtener_back_urls()
                
                preference_data = {
                    "items": [{"title": f"Seña de Consulta - {odontologo_nombre}", "quantity": 1, "unit_price": float(monto_turno), "currency_id": "ARS"}],
                    "marketplace_fee": mi_comision, 
                    "back_urls": urls_dinamicas, 
                    "auto_return": "approved",
                }
                preference_response = sdk_dinamico.preference().create(preference_data)
                link_pago = preference_response["response"].get("init_point", "Error link")
            except Exception as e:
                print(f"Error Mercado Pago: {e}")
                link_pago = "Error al generar link"
            
            # 3. LLAMADA AL MODELO CON RESPALDO
            messages = [
                {"role": "system", "content": f"Sos un asistente dental experto de {odontologo_nombre}. Link de pago: {link_pago}"}, 
                {"role": "user", "content": user_input}
            ]
            
            chat = self._request_with_failover(self.text_model, messages, 0.7)

            st.session_state["datos_turno_pendiente"] = {"paciente_nombre": "Paciente Temporal", "motivo": "Consulta"}
            st.session_state["odontologo_id_actual"] = id_final
            
            return chat.choices[0].message.content

        except Exception as e:
            print(f"DEBUG ERROR: {str(e)}")
            return f"Error en mi motor: {str(e)}"

    def analizar_caries(self, uploaded_file):
        try:
            if not uploaded_file: return "No hay imagen."
            base64_image = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
            vision_prompt = "Analiza esta imagen dental y busca caries."
            messages = [{"role": "user", "content": [{"type": "text", "text": vision_prompt}, {"type": "image_url", "image_url": {"url": f"data:{uploaded_file.type};base64,{base64_image}"}}]} ]
            
            # LLAMADA A VISIÓN CON RESPALDO
            response = self._request_with_failover(self.vision_model, messages, 0.2)
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error Visión: {str(e)}"