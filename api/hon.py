from http.server import BaseHTTPRequestHandler
import json
import asyncio
import os
from pyhon import Hon

# 1. INDISPENSABILE SU VERCEL: Diciamo alla libreria di usare l'unica cartella scrivibile
os.environ["HOME"] = "/tmp"
os.environ["XDG_CONFIG_HOME"] = "/tmp"
os.environ["XDG_DATA_HOME"] = "/tmp"

# 2. LA VERA MEMORIA: Manteniamo in RAM la sessione e la lista dei clima senza chiudere il motore
global_hon_session = None
global_loop = asyncio.new_event_loop()
asyncio.set_event_loop(global_loop)

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        # Lo svegliarino di cron-job.org bussa qui e riceve subito risposta
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
                success, message = global_loop.run_until_complete(self.control_ac(email, password, command, temp))
            except Exception as network_error:
                # --- AUTO-RIPARAZIONE INVISIBILE ---
                # Se la rete di Vercel si è addormentata, cancella la memoria e riparte da zero da solo
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
        
        # Al primo clic della giornata scarica i dati da Haier (ci mette 15-20 secondi)
        if global_hon_session is None:
            global_hon_session = Hon(email, password)
            await global_hon_session.setup()
        
        # Scorriamo la lista che ora rimane magicamente salvata in memoria!
        for appliance in global_hon_session.appliances:
            mac = getattr(appliance, 'mac_address', '').replace(":", "-").upper()
            
            # Identifichiamo il tuo Tundra
            if mac == "AC-15-18-B7-93-70" or getattr(appliance, 'appliance_type', '') == "AC":
                
                if command in ["on", "cool"]:
                    if temp and "tempSel" in appliance.settings:
                        appliance.settings["tempSel"].value = str(temp)
                    
                    # Usiamo i comandi sicuri con le alternative (startProgram)
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
