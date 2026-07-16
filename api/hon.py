from http.server import BaseHTTPRequestHandler
import json
import asyncio
import os
import threading
from pyhon import Hon

# 1. Variabili globali: teniamo in memoria sia la sessione che il motore di rete
global_hon_session = None
global_loop = asyncio.new_event_loop()

# 2. Questo è il trucco magico: avviamo il motore di rete in un "binario parallelo" (Thread)
# In questo modo Vercel NON POTRA' MAI chiuderlo tra un clic e l'altro!
def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=start_background_loop, args=(global_loop,), daemon=True).start()


class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        # Risposta rapida per lo Svegliarino di cron-job
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'Server Vercel Attivo'}).encode('utf-8'))

    def do_POST(self):
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

            # 3. Invece di accendere il motore, "passiamo" il comando al Thread in background
            future = asyncio.run_coroutine_threadsafe(
                self.control_ac(email, password, command, temp), 
                global_loop
            )
            
            # Aspettiamo il risultato (massimo 20 secondi per evitare blocchi)
            success, message = future.result(timeout=20)
            
            if success:
                self.send_success_response(message)
            else:
                self.send_error_response(message)
                
        except Exception as e:
            self.send_error_response(f"Errore di invio: {str(e)}")

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
            # Se per qualche motivo estremo cade la connessione, azzeriamo la memoria.
            # Il messaggio "Riprova ora" ti dirà di rifare clic, e lui ripartirà da zero perfetto.
            global_hon_session = None 
            return False, f"Connessione aggiornata, clicca di nuovo. ({str(e)})"

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
