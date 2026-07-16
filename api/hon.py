from http.server import BaseHTTPRequestHandler
import json
import asyncio
import os
from pyhon import Hon

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # 1. Leggiamo i dati inviati dalla tua Web App
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            command = data.get('command')
            temp = data.get('temperature')
            
            # 2. Recuperiamo le chiavi segrete da Vercel
            email = os.environ.get('HON_EMAIL')
            password = os.environ.get('HON_PASSWORD')
            
            if not email or not password:
                self.send_error_response("Credenziali HON_EMAIL o HON_PASSWORD mancanti su Vercel")
                return

            # 3. Avviamo la comunicazione con Haier
            success, message = asyncio.run(self.control_ac(email, password, command, temp))
            
            if success:
                self.send_success_response(message)
            else:
                self.send_error_response(message)
                
        except Exception as e:
            self.send_error_response(f"Errore interno: {str(e)}")

    async def control_ac(self, email, password, command, temp):
        try:
            # Login ai server Haier
            async with Hon(email, password) as hon:
                
                # Scorriamo la lista dei tuoi elettrodomestici (appliances)
                for appliance in hon.appliances:
                    
                    # Identifica esattamente il 5° Tundra (MAC: AC-15-18-B7-93-70)
                    mac = getattr(appliance, 'mac_address', '').replace(":", "-").upper()
                    
                    if mac == "AC-15-18-B7-93-70" or getattr(appliance, 'appliance_type', '') == "AC":
                        
                        if command == "on" or command == "cool":
                            # Imposta la temperatura (se passata e se presente nelle impostazioni)
                            if temp and "tempSel" in appliance.settings:
                                appliance.settings["tempSel"].value = str(temp)
                            
                            # Invia comando accensione
                            if "turn_on" in appliance.commands:
                                await appliance.commands["turn_on"].send()
                            elif "startProgram" in appliance.commands:
                                await appliance.commands["startProgram"].send()
                                
                            return True, f"Condizionatore acceso a {temp}°C"
                            
                        elif command == "off":
                            # Invia comando spegnimento
                            if "turn_off" in appliance.commands:
                                await appliance.commands["turn_off"].send()
                            elif "stopProgram" in appliance.commands:
                                await appliance.commands["stopProgram"].send()
                                
                            return True, "Condizionatore spento"
                            
                return False, "Nessun condizionatore trovato nel tuo account hOn."
                
        except Exception as e:
            return False, f"Errore di comunicazione: {str(e)}"

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
