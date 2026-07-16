from http.server import BaseHTTPRequestHandler
import json
import asyncio
import os
from pyhon import Hon

# LA VERA MEMORIA: Manteniamo in RAM l'oggetto senza chiudere mai il "motore"
global_hon_session = None
global_loop = asyncio.new_event_loop()
asyncio.set_event_loop(global_loop)

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        # Risposta rapida per lo Svegliarino di cron-job (bussa senza fare danni)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'Server Vercel Attivo'}).encode('utf-8'))

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
            
            if not email or not password:
                self.send_error_response("Credenziali mancanti")
                return

            # --- TENTATIVO PRINCIPALE ---
            try:
                # Se la memoria c'è, salta il login e ci mette 2 secondi
                success, message = global_loop.run_until_complete(self.control_ac(email, password, command, temp))
            
            except Exception as network_error:
                # --- AUTO-RIPARAZIONE INVISIBILE ---
                # Se Vercel ha rotto la connessione durante la pausa, il codice di prima 
                # mandava tutto in crash. Questo svuota la memoria e riparte all'istante da solo.
                print(f"Rete disconnessa, auto-riparazione: {network_error}")
                
                global_hon_session = None
                try:
                    success, message = global_loop.run_until_complete(self.control_ac(email, password, command, temp))
                except Exception as final_error:
                    success = False
                    message = f"Fallito ripristino: {str(final_error)}"
            
            if success:
                self.send_success_response(message)
            else:
                self.send_error_response(message)
                
        except Exception as e:
            self.send_error_response(f"Errore interno Vercel: {str(e)}")

    async def control_ac(self, email, password, command, temp):
        global global_hon_session
        
        # Se la memoria è vuota (primo clic della giornata o dopo auto-riparazione),
        # deve fare il login e scaricare i dispositivi (ci mette i famosi 15 secondi)
        if global_hon_session is None:
            global_hon_session = Hon(email, password)
            await global_hon_session.setup()
        
        # Scorriamo i dispositivi che ha salvato in memoria
        for appliance in global_hon_session.appliances:
            mac = getattr(appliance, 'mac_address', '').replace(":", "-").upper()
            if mac == "AC-15-18-B7-93-70" or getattr(appliance, 'appliance_type', '') == "AC":
                
                if command in ["on", "cool"]:
                    if temp and "tempSel" in appliance.settings:
                        appliance.settings["tempSel"].value = str(temp)
                    
                    # Invia il comando. Se la rete è morta, si ferma qui e fa scattare l'auto-riparazione sopra
                    await appliance.commands["turn_on"].send()
                    return True, f"Acceso a {temp}°C"
                    
                elif command == "off":
                    await appliance.commands["turn_off"].send()
                    return True, "Spento"
                    
        return False, "Nessun condizionatore trovato."

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
