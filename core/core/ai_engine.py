import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class DentalAI:
    def __init__(self):
        # Asegúrate de tener GROQ_API_KEY en tu .env
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama3-8b-8192"

    def get_response(self, user_input):
        try:
            # System Prompt para dar contexto odontológico
            system_prompt = (
                "Eres un asistente experto para un consultorio odontológico. "
                "Respondes dudas sobre tratamientos (limpiezas, implantes, ortodoncia) "
                "y das consejos de post-operatorio. Sé profesional, breve y amable. "
                "Si te preguntan por diagnósticos complejos, sugiere siempre la revisión física."
            )
            
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                model=self.model,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error de conexión con la IA: {str(e)}"
