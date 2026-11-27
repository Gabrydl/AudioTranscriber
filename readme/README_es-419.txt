AudioTranscriber 1.6.0 - transcripción y traducción de voz en vivo
==================================================================

QUÉ HACE
  Escucha las apps que elijas (como Discord), escribe lo que dice cada persona y lo traduce en vivo al
  idioma que quieras. El reconocimiento de voz funciona en esta PC. La traducción también funciona en
  esta PC, o en línea con Gemini si lo activas. Sin cuenta, no se graba nada en el disco.

INSTALACIÓN
  Ejecuta AudioTranscriber_Setup.exe. La primera pantalla pregunta el idioma de la app (el de Windows ya
  está seleccionado). La instalación prepara todo paso a paso (unos 8 GB, 10-20 minutos). Si encuentra
  una copia anterior, reutiliza sus modelos, su configuración y sus voces. Después abre AudioTranscriber
  desde el escritorio o el menú Inicio. Puedes cambiar el idioma de la app cuando quieras con el botón
  de la bandera de la barra izquierda.

EMPEZAR
  1. Entra a una llamada de Discord. Discord aparece en "ESCUCHAR" (punto verde = reproduce audio).
  2. Presiona Iniciar. Cada frase aparece con quién la dijo, la hora, la traducción y lo que se oyó.
  3. La onda muestra el volumen. "Auto" sigue el ruido de fondo de cada persona; arrastra la línea
     punteada para ajustarlo a mano.
  El botón de los audífonos junto a Iniciar cambia rápido los idiomas a reconocer.

LA VENTANA
  Barra izquierda: En vivo, Personas, Palabras que conocer, Overlay, Bloquear overlay, Borrar, bandera
  del idioma, Configuración. A la derecha: demora, tarjeta de video, memoria, líneas y la gente de la
  llamada. Haz clic en un nombre de cualquier línea para renombrarlo, corregir a la persona, unir a dos
  personas, ignorar a alguien o fijar el idioma que habla siempre. Cada corrección lo hace más preciso.
  "DEDUCIDO DEL CONTEXTO" = las palabras no estaban claras y el traductor dedujo el sentido.
  Palabras grises = el reconocedor no estaba seguro de ellas.

CONFIGURACIÓN (categorías a la izquierda, opciones poco usadas en "Avanzado")
  Reconocimiento  modelo de voz y dónde funciona, idiomas a reconocer, detección de frases, palabras
                  que conocer (nombres, términos de juego, jerga), términos de League of Legends.
  Traducción      tarjeta de video (local, sin conexión), Online - Gemini (clave gratis), o las dos:
                  primero online, la tarjeta de video de reserva. El límite gratuito diario de Gemini se
                  reinicia a las 09:00 (hora de Italia).
  Personas        reconocer quién habla, recordar las voces, aprender el idioma de cada persona, lista
                  de personas conocidas (Ctrl/Shift + clic para elegir varias, Supr para olvidarlas).
  Discord         nombres y quién habla directamente desde la app de Discord de esta PC (sin bot), se
                  configura una vez con "Cómo configurarlo" (unos 2 minutos); empieza y para con tus
                  llamadas.
  Overlay y pantalla  texto original, texto del overlay, tamaño, opacidad, ocultamiento automático, atajos.
  App             idioma de la app, iniciar con Windows, fiabilidad, exportar, versión.

OVERLAY
  Un recuadro transparente encima del juego (modo ventana o sin bordes; no en pantalla completa
  exclusiva). "Mover el overlay" lo desbloquea para arrastrarlo; se vuelve a bloquear solo al soltarlo.
  Bloqueado, los clics pasan al juego y se desvanece tras unos segundos de silencio.

ATAJOS (funcionan dentro de los juegos)
  Ctrl+Alt+S iniciar / parar      Ctrl+Alt+P pausa / seguir       Ctrl+Alt+C copiar la última traducción
  Ctrl+Alt+O overlay sí / no      Ctrl+Alt+L bloquear / desbloquear el overlay

ACTUALIZACIONES
  Al abrirse, la app busca una versión más nueva, la descarga en silencio y se reinicia con ella (si
  estás escuchando, en cuanto presiones Parar). Configuración, voces, sesión de Discord y modelos se
  mantienen.

REPARAR Y DESINSTALAR
  Reparar: Configuración > Aplicaciones > AudioTranscriber > Modificar, o vuelve a ejecutar la
  instalación y elige Reparar. Solo descarga lo que falta; la configuración y las voces se mantienen.
  Desinstalar: Configuración > Aplicaciones > AudioTranscriber > Desinstalar. Pregunta si borrar también
  los modelos y la configuración (unos 8 GB). Ollama es un programa aparte con su propio desinstalador.

PRIVACIDAD
  Voces, nombres, configuración, claves y la sesión de Discord se quedan solo en esta PC. Con Gemini
  activado, el texto de cada frase (no el audio) se envía a Google para traducirlo.

ARCHIVOS
  AudioTranscriber.exe  la app               Setup.exe     reparar          Uninstall.exe  quitar
  app\                  programa             models\       modelos de habla y de voz
  ollama_models\        modelos de traducción transcripts\ solo al presionar Exportar
  settings.json         tu configuración     speakers.json voces guardadas  setup.log      registro de instalación
