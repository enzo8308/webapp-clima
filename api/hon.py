from http.server import BaseHTTPRequestHandler
import json
import asyncio
import os
import shutil
from pyhon import Hon

# La cartella temporanea per i file di cache
os.environ["HOME"] = "/tmp"
os.environ["XDG_CONFIG_HOME"] = "/tmp"
os.environ["XDG_DATA_HOME"] = "/tmp"

global_hon_session = None
global_loop = asyncio.new_event_loop()
asyncio.set_event_loop(global_loop)

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'Server Vercel Attivo'}).encode('utf-8'))

    def do_POST(self):
        global global_hon_session
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
                self.send_error_response("Credenziali mancanti")
                return

            if global_loop.is_closed():
                global_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(global_loop)

            # --- TENTATIVO PRINCIPALE ---
            try:
                success, message = global_loop.run_until_complete(self.control_ac(email, password, command, temp))
            except Exception as e:
                success = False
                message = f"Errore iniziale: {str(e)}"
            
            # --- AUTO-RIPARAZIONE PROFONDA CON LANCIAFIAMME ---
            if not success:
                print("Biglietto o memoria corrotta. Avvio pulizia totale...")
                
                # 1. Distruggiamo la RAM
                global_hon_session = None 
                
                # 2. Distruggiamo il motore di rete
                global_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(global_loop)
                
                # 3. IL LANCIAFIAMME: Bruciamo i file temporanei con il token scaduto!
                for cache_dir in ['/tmp/hon', '/tmp/.hon', '/tmp/pyhon']:
                    shutil.rmtree(cache_dir, ignore_errors=True)
                
                try:
                    # 4. Ora la libreria è costretta a chiedere ad Haier un Token NUOVO
                    success, message = global_loop.run_until_complete(self.control_ac(email, password, command, temp))
                except Exception as final_error:
                    success = False
                    message = f"Errore critico ripristino: {str(final_error)}"
            
            if success:
                self.send_success_response(message)
            else:
                self.send_error_response(message)
                
        except Exception as e:
            self.send_error_response(f"Errore Vercel: {str(e)}")

    async def control_ac(self, email, password, command, temp):
        global global_hon_session
        
        try:
            if global_hon_session is None:
                global_hon_session = Hon(email, password)
                await global_hon_session.setup()
            
            if not global_hon_session.appliances:
                return False, "Lista elettrodomestici vuota."
                
            for appliance in global_hon_session.appliances:
                mac = getattr(appliance, 'mac_address', '').replace(":", "-").upper()
                
                if mac == "AC-15-18-B7-93-70" or getattr(appliance, 'appliance_type', '') == "AC":
                    res = False
                    
                    if command in ["on", "cool"]:
                        if temp and "tempSel" in appliance.settings:
                            appliance.settings["tempSel"].value = str(temp)
                        
                        if "turn_on" in appliance.commands:
                            res = await appliance.commands["turn_on"].send()
                        elif "startProgram" in appliance.commands:
                            res = await appliance.commands["startProgram"].send()
                            
                        if not res:
                            return False, "Comando rifiutato (Falso Positivo)."
                            
                        return True, f"Acceso a {temp}°C"
                        
                    elif command == "off":
                        if "turn_off" in appliance.commands:
                            res = await appliance.commands["turn_off"].send()
                        elif "stopProgram" in appliance.commands:
                            res = await appliance.commands["stopProgram"].send()
                            
                        if not res:
                            return False, "Comando rifiutato (Falso Positivo)."
                            
                        return True, "Spento"
                        
            return False, "Condizionatore non trovato."
            
        except Exception as e:
            return False, f"Eccezione ({type(e).__name__}): {str(e)}"

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
