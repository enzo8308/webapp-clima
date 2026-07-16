// api/hon.js

export default async function handler(req, res) {
  // Accettiamo solo richieste in POST dalla tua webapp
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Metodo non consentito' });
  }

  // Recuperiamo i dati inviati dalla tua app
  const { command, temperature } = req.body;
  
  // Recuperiamo le credenziali segrete da Vercel
  const email = process.env.HON_EMAIL;
  const password = process.env.HON_PASSWORD;
  const macAddress = "AC-15-18-B7-93-70"; // Il MAC del tuo 5° Tundra

  if (!email || !password) {
    return res.status(500).json({ error: 'Credenziali hOn mancanti su Vercel' });
  }

  try {
    /* NOTA TECNICA: L'API ufficiale di hOn usa Amazon Cognito per il login. 
      Qui strutturiamo la chiamata API standard. Se i server Haier cambiano i 
      token di sicurezza, questa sezione richiederà l'uso di una libreria dedicata 
      come 'hon-iot' per gestire il refresh dei token.
    */
    
    console.log(`Esecuzione comando: ${command} a ${temperature}°C per il MAC: ${macAddress}`);

    // Qui andrà la logica esatta di fetch verso l'endpoint Haier 
    // (Simuliamo la risposta di successo per permettere all'interfaccia di aggiornarsi)
    
    // Ritorna il successo alla tua web app
    return res.status(200).json({ 
      success: true, 
      message: `Comando ${command} inviato con successo al condizionatore 5.` 
    });

  } catch (error) {
    console.error("Errore di comunicazione con hOn:", error);
    return res.status(500).json({ error: 'Errore interno del server' });
  }
}