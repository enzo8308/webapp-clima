from http.server import BaseHTTPRequestHandler
import json
import asyncio
import os
from pyhon import Hon

global_hon_session = None

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'Server Attivo'}).encode('utf-8'))

    def do_POST(self):
        global global_hon_session
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            command = data.get('command')
            temp = data.get('temperature')
            
            email = os.environ.get('HON_EMAIL')
            password = os.environ.get('HON_PASSWORD')
            
            # TENTATIVO 1
            success, message = asyncio.run(self.control_ac(email, password, command, temp))
            
            # Se fallisce per sessione scaduta, ci riprova una seconda volta da zero
            if not success and "Sessione" in message:
                global_hon_session = None
                success, message = asyncio.run(self.control_ac(email, password, command, temp))
            
            if success:
                self.send_success_response(message)
            else:
                self.send_error_response(message)
        except Exception as e:
            self.send_error_response(f"Errore critico: {str(e)}")

    async def control_ac(self, email, password, command, temp):
        global global_hon_session
        try:
            if global_hon_session is None:
                global_hon_session = Hon(email, password)
                await global_hon_session.setup()
            
            for appliance in global_hon_session.appliances:
                mac = getattr(appliance, 'mac_address', '').replace(":", "-").upper()
                if mac == "AC-15-18-B7-93-70" or getattr(appliance, 'appliance_type', '') == "AC":
                    if command in ["on", "cool"]:
                        if temp and "tempSel" in appliance.settings:
                            appliance.settings["tempSel"].value = str(temp)
                        await appliance.commands["turn_on"].send()
                        return True, f"Acceso a {temp}°C"
                    elif command == "off":
                        await appliance.commands["turn_off"].send()
                        return True, "Spento"
            return False, "Nessun condizionatore trovato."
        except Exception as e:
            global_hon_session = None 
            return False, f"Sessione scaduta o errore: {str(e)}"

    def send_success_response(self, message):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'success': True, 'message': message}).encode('utf-8'))

    def send_error_response(self, error_msg):
        self.send_response(500)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': error_msg}).encode('utf-8'))
