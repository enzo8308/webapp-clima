from http.server import BaseHTTPRequestHandler
import json
import asyncio
import os
from pyhon import Hon

# Manteniamo in memoria sia il login (session) che il motore di rete (loop)
global_hon_session = None
global_loop = None

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        # Risposta rapida per lo svegliarino di cron-job
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'Server Vercel Attivo!'}).encode('utf-8'))

    def do_POST(self):
        global global_loop
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            command = data.get('command')
            temp = data.get('temperature')
            
            email = os.environ.get('HON_EMAIL')
            password = os.environ.get('HON_PASSWORD')
            
            if not email or not password:
                self.send_error_response("Credenziali mancanti su Vercel")
                return

            # MAGIA: Creiamo la "strada" di rete e la teniamo aperta per sempre
            if global_loop is None or global_loop.is_closed():
                global_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(global_loop)
            
            # Eseguiamo il comando usando la strada che rimane aperta
            success, message = global_loop.run_until_complete(self.control_ac(email, password, command, temp))
            
            if success:
                self.send_success_response(message)
            else:
                self.send_error_response(message)
                
        except Exception as e:
            self.send_error_response(f"Errore Python: {str(e)}")

    async def control_ac(self, email, password, command, temp):
        global global_hon_session
        
        try:
            # Login veloce usando la memoria
            if global_hon_session is None:
                global_hon_session = Hon(email, password)
                await global_hon_session.setup()
            
            for appliance in global_hon_session.appliances:
                mac = getattr(appliance, 'mac_address', '').replace(":", "-").upper()
                
                if mac == "AC-15-18-B7-93-70" or getattr(appliance, 'appliance_type', '') == "AC":
                    
                    if command == "on" or command == "cool":
                        if temp and "tempSel" in appliance.settings:
                            appliance.settings["tempSel"].value = str(temp)
                        
                        if "turn_on" in appliance.commands:
                            await appliance.commands["turn_on"].send()
                        elif "startProgram" in appliance.commands:
                            await appliance.commands["startProgram"].send()
                            
                        return True, f"Acceso a {temp}°C"
                        
                    elif command == "off":
                        if "turn_off" in appliance.commands:
                            await appliance.commands["turn_off"].send()
                        elif "stopProgram" in appliance.commands:
                            await appliance.commands["stopProgram"].send()
                            
                        return True, "Spento"
                        
            return False, "Nessun condizionatore trovato."
            
        except Exception as e:
            # Se la sessione scade misteriosamente, cancelliamo la memoria così al prossimo clic la rifà da zero
            global_hon_session = None 
            return False, f"Connessione interrotta, premi di nuovo per riavviare ({str(e)})"

    def send_success_response(self, message):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'success': True, 'message': message}).encode('utf-8'))

    def send_error_response(self, error_msg):
        self.send_response(500)
