from fastapi import FastAPI
from pydantic import BaseModel
import os
from pyhon import Hon

app = FastAPI()

# Variabile globale: tiene aperta la connessione tra un clic e l'altro!
global_hon = None

# Struttura dei dati in arrivo dalla tua Web App
class CommandReq(BaseModel):
    command: str
    temperature: int = None

@app.post("/api/hon")
async def control_ac(req: CommandReq):
    global global_hon
    
    email = os.environ.get('HON_EMAIL')
    password = os.environ.get('HON_PASSWORD')
    
    if not email or not password:
        return {"error": "Credenziali mancanti su Vercel"}

    try:
        # 1. Se è il primo clic, facciamo il login lento. 
        # Altrimenti, usiamo la sessione già aperta in memoria (Veloce!)
        if global_hon is None:
            print("Avvio nuova sessione hOn (lenta)...")
            global_hon = Hon(email, password)
            await global_hon.setup()
        else:
            print("Uso sessione hOn già attiva in memoria (veloce!)...")
            
        # 2. Cerchiamo il condizionatore e mandiamo il comando
        for appliance in global_hon.appliances:
            mac = getattr(appliance, 'mac_address', '').replace(":", "-").upper()
            
            if mac == "AC-15-18-B7-93-70" or getattr(appliance, 'appliance_type', '') == "AC":
                
                if req.command == "on" or req.command == "cool":
                    if req.temperature and "tempSel" in appliance.settings:
                        appliance.settings["tempSel"].value = str(req.temperature)
                    
                    if "turn_on" in appliance.commands:
                        await appliance.commands["turn_on"].send()
                    elif "startProgram" in appliance.commands:
                        await appliance.commands["startProgram"].send()
                        
                    return {"success": True, "message": f"Acceso a {req.temperature}°C"}
                    
                elif req.command == "off":
                    if "turn_off" in appliance.commands:
                        await appliance.commands["turn_off"].send()
                    elif "stopProgram" in appliance.commands:
                        await appliance.commands["stopProgram"].send()
                        
                    return {"success": True, "message": "Spento"}
                    
        return {"error": "Nessun condizionatore trovato."}
        
    except Exception as e:
        # Se qualcosa va storto (es. Haier disconnette la sessione), resettiamo
        global_hon = None 
        return {"error": f"Errore interno: {str(e)}"}
