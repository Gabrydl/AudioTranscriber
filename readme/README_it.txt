AudioTranscriber 1.6.0 - trascrizione e traduzione vocale dal vivo
==================================================================

COSA FA
  Ascolta le app che scegli (come Discord), scrive quello che dice ogni persona e lo traduce dal vivo
  nella lingua che preferisci. Il riconoscimento vocale gira su questo PC. Anche la traduzione gira su
  questo PC, oppure online con Gemini se lo attivi. Nessun account, niente viene registrato su disco.

INSTALLAZIONE
  Avvia AudioTranscriber_Setup.exe. La prima schermata chiede la lingua dell'app (quella di Windows è
  già selezionata). L'installazione prepara tutto passo per passo (circa 8 GB, 10-20 minuti). Se trova
  una copia precedente, ne riusa modelli, impostazioni e voci. Poi apri AudioTranscriber dal desktop o
  dal menu Start. Puoi cambiare la lingua dell'app quando vuoi con il pulsante della bandiera nella
  barra a sinistra.

AVVIO
  1. Entra in una chiamata Discord. Discord appare sotto "ASCOLTA" (pallino verde = sta suonando audio).
  2. Premi Avvia. Ogni frase compare con chi l'ha detta, l'ora, la traduzione e cosa è stato sentito.
  3. L'onda mostra il volume. "Auto" segue il rumore di fondo di ogni persona; trascina la linea
     tratteggiata per regolarlo a mano.
  Il pulsante con le cuffie accanto ad Avvia cambia le lingue da riconoscere con un clic.

LA FINESTRA
  Barra a sinistra: Dal vivo, Persone, Parole da conoscere, Overlay, Blocca overlay, Svuota, bandiera
  della lingua, Impostazioni. A destra: ritardo, scheda video, memoria, righe e le persone in chiamata.
  Clicca un nome su una riga per rinominarlo, correggere la persona, unire due persone, ignorare
  qualcuno o fissare la lingua che parla sempre. Ogni correzione lo rende più preciso.
  "DEDOTTO DAL CONTESTO" = le parole non erano chiare e il traduttore ha dedotto il significato.
  Parole grigie = il riconoscitore non ne era sicuro.

IMPOSTAZIONI (categorie a sinistra, opzioni rare sotto "Avanzate")
  Riconoscimento  modello vocale e dove gira, lingue da riconoscere, rilevamento delle frasi,
                  parole da conoscere (nomi, termini di gioco, slang), termini di League of Legends.
  Traduzione      scheda video (in locale, offline), Online - Gemini (chiave gratis), o entrambi:
                  prima online, la scheda video come riserva. Il limite gratuito giornaliero di Gemini
                  si azzera alle 09:00 (ora italiana).
  Persone         riconosci chi parla, ricorda le voci, impara la lingua di ogni persona, elenco delle
                  persone conosciute (Ctrl/Maiusc + clic per sceglierne più di una, Canc per dimenticarle).
  Discord         nomi e chi parla direttamente dall'app Discord su questo PC (nessun bot), da
                  configurare una volta con "Come configurarlo" (circa 2 minuti); avvio/stop insieme
                  alle tue chiamate.
  Overlay e schermo  testo originale, testo dell'overlay, dimensione, opacità, scomparsa automatica,
                  tasti rapidi.
  App             lingua dell'app, avvio con Windows, affidabilità, esportazione, versione.

OVERLAY
  Un riquadro trasparente sopra il gioco (in finestra o senza bordi; non a schermo intero esclusivo).
  "Sposta l'overlay" lo sblocca per poterlo trascinare; si blocca di nuovo da solo quando lo lasci.
  Quando è bloccato i clic passano al gioco e sparisce dopo qualche secondo di silenzio.

TASTI RAPIDI (funzionano dentro i giochi)
  Ctrl+Alt+S avvia / ferma        Ctrl+Alt+P pausa / riprendi     Ctrl+Alt+C copia l'ultima traduzione
  Ctrl+Alt+O overlay sì / no      Ctrl+Alt+L blocca / sblocca l'overlay

AGGIORNAMENTI
  All'apertura l'app cerca una versione più recente, la scarica in silenzio e si riavvia con quella (se
  stai ascoltando, appena premi Ferma). Impostazioni, voci, accesso Discord e modelli restano.

RIPARAZIONE E DISINSTALLAZIONE
  Ripara: Impostazioni > App > AudioTranscriber > Modifica, oppure esegui di nuovo l'installazione e scegli
  Ripara. Scarica solo ciò che manca; impostazioni e voci restano.
  Disinstalla: Impostazioni > App > AudioTranscriber > Disinstalla. Chiede se eliminare anche i modelli
  e le impostazioni (circa 8 GB). Ollama è un programma a parte con il suo programma di disinstallazione.

PRIVACY
  Voci, nomi, impostazioni, chiavi e accesso Discord restano solo su questo PC. Con Gemini attivo, il
  testo di ogni frase (non l'audio) viene inviato a Google per essere tradotto.

FILE
  AudioTranscriber.exe  l'app                 Setup.exe     riparazione    Uninstall.exe  rimozione
  app\                  programma             models\       modelli vocali e delle voci
  ollama_models\        modelli del traduttore transcripts\  solo quando premi Esporta
  settings.json         le tue impostazioni   speakers.json voci salvate   setup.log      log installazione
