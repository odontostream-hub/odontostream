import os
import base64
import mercadopago
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
# --- IMPORTAMOS TU LÓGICA DE GOOGLE ---
from Core.google_calendar import listar_proximos_eventos

load_dotenv()

class DentalAI:
    def __init__(self, supabase_client=None):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.text_model = "llama-3.1-8b-instant"
        self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.supabase = supabase_client
        
        self.mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        self.sdk = mercadopago.SDK(self.mp_access_token) if self.mp_access_token else None

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
        if not self.sdk: return None, 0.0
        
        # 1. Traemos el precio REAL que el odontólogo cargó en el Panel Admin
        precio_total = self.obtener_precio_odontologo(odontologo_id)
        
        # 2. Calculamos la comisión (El 5% que es para vos)
        # Podés cobrar el total o solo la seña, pero acá usamos el precio del doc
        try:
            preference_data = {
                "items": [
                    {
                        "title": f"Turno {motivo}: {paciente_nombre}",
                        "quantity": 1,
                        "unit_price": precio_total, # El precio que puso el Doc
                        "currency_id": "ARS"
                    }
                ],
                "back_urls": {
                    "success": "https://odontostream.com.ar/?pago=exitoso",
                    "failure": "https://odontostream.com.ar/?pago=fallido",
                    "pending": "https://odontostream.com.ar/?pago=pendiente"
                },
                "auto_return": "approved",
                # Aquí podrías configurar la división de pagos si usás Mercado Pago Marketplace
                # O simplemente recibir vos el total y después liquidar.
            }
            res = self.sdk.preference().create(preference_data)
            return res["response"].get("init_point"), precio_total
        except:
            return None, precio_total

    def get_response(self, user_input, odontologo_nombre="el especialista", odontologo_id=None, **kwargs):
        try:
            # 1. LEER GOOGLE CALENDAR REAL
            contexto_agenda = "Horarios ya ocupados en Google Calendar:\n"
            try:
                # Importamos acá por si las dudas
                from Core.google_calendar import listar_proximos_eventos
                eventos = listar_proximos_eventos(max_results=10)
                if eventos:
                    for ev in eventos:
                        inicio = ev['start'].get('dateTime', ev['start'].get('date'))
                        contexto_agenda += f"- {ev.get('summary')}: {inicio}\n"
                else:
                    contexto_agenda += "La agenda está libre.\n"
            except:
                contexto_agenda += "No pude acceder al calendario.\n"

            # 2. GENERAR LINK DE PAGO
            # Sacamos la localidad de kwargs (si no está, ponemos Buenos Aires o la que quieras)
            localidad = kwargs.get("localidad_paciente", "Buenos Aires")
            
            # ¡ACÁ ESTABA EL ERROR! Le faltaba pasar el odontologo_id
            # Si odontologo_id viene vacío, le mandamos un valor por defecto para que no explote
            id_final = odontologo_id if odontologo_id else "ID_GENERAL"
            
            link_pago, precio = self.crear_link_pago_turno("Consulta", "Paciente", id_final)

            # SYSTEM PROMPT MEJORADO
            system_prompt = (
                f"Eres la secretaria estrella de Odonto-Stream para el Dr/a. {odontologo_nombre}.\n"
                f"Ubicación del consultorio: {localidad}.\n\n"
                f"TU MISIÓN: Agendar turnos pidiendo DNI, Nombre y Teléfono.\n\n"
                f"ESTADO REAL DE LA AGENDA (No ofrezcas estos horarios):\n{contexto_agenda}\n"
                f"INSTRUCCIONES CRÍTICAS:\n"
                f"1. Pide DNI, Nombre y Teléfono si no los tienes.\n"
                f"2. Cuando el paciente elija un horario LIBRE, confírmalo y dile que debe pagar la seña de ${precio}.\n"
                f"3. ENTREGA ESTE LINK DE PAGO ÚNICAMENTE CUANDO EL PACIENTE ESTÉ LISTO PARA PAGAR: {link_pago}\n"
                f"4. Mantén el tono ejecutivo, profesional y muy cercano."
            )
            
            # 3. LLAMADA AL MODELO (Asegúrate de que self.client esté bien inicializado con la API KEY)
            chat = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt}, 
                    {"role": "user", "content": user_input}
                ],
                model=self.text_model,
                temperature=0.7
            )
            return chat.choices[0].message.content

        except Exception as e:
            # Esto te va a decir exactamente qué falló en la consola
            print(f"DEBUG ERROR: {str(e)}")
            return f"Lo siento, Mani, hubo un error en mi motor: {str(e)}"

    def analizar_caries(self, uploaded_file):
        try:
            if not uploaded_file: return "No hay imagen."
            base64_image = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
            vision_prompt = "Analiza esta imagen dental y busca caries o anomalías. Estructura: 1. Hallazgos, 2. Sospechas, 3. Especialista recomendado, 4. Consejo. Añade descargo legal."
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[{"role": "user", "content": [{"type": "text", "text": vision_prompt}, {"type": "image_url", "image_url": {"url": f"data:{uploaded_file.type};base64,{base64_image}"}}]}],
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error Visión: {str(e)}"