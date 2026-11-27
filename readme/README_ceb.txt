AudioTranscriber 1.6.0 - live nga transcription ug paghubad sa tingog
=====================================================================

UNSA ANG BUHATON NIINI
  Paminawon niini ang mga app nga imong pilion (sama sa Discord), isulat ang gisulti sa matag tawo ug
  hubaron kini nga live sa pinulongan nga imong gusto. Nagdagan niini nga PC ang pag-ila sa
  sinultihan. Diri usab nagdagan ang paghubad, o online gamit ang Gemini kung imong i-on. Walay
  account, walay gi-record sa disk.

PAG-INSTALL
  Padagana ang Setup.exe. Pangutan-on sa unang screen ang pinulongan sa app (napili
  na ang pinulongan sa imong Windows). Andamon sa Setup ang tanan lakang-lakang (mga 8 GB, 10-20
  minutos). Kung adunay makit-ang daan nga kopya, gamiton pag-usab ang mga model, setting ug tingog
  niini. Human niana, ablihi ang AudioTranscriber gikan sa desktop o sa Start menu. Mausab nimo bisan
  kanus-a ang pinulongan sa app gamit ang flag button sa wala nga bar.

PAGSUGOD
  1. Apil sa tawag sa Discord. Mogawas ang Discord sa "PAMINAWA" (berde nga tuldok = adunay audio).
  2. Pindota ang Sugdi. Mogawas ang matag pulong uban kung kinsa ang nagsulti, ang oras, ang hubad ug
     ang nadungog.
  3. Ipakita sa balod ang kakusog sa tingog. Sundon sa "Auto" ang saba sa background sa matag tawo;
     i-drag ang putol-putol nga linya aron ikaw ang mohan-ay.
  Ang headphones button tupad sa Sugdi paspas nga mobalhin sa mga pinulongan nga ilhon.

ANG WINDOW
  Wala nga bar: Live, Mga tawo, Mga pulong, Overlay, I-lock ang overlay, Limpyohi, flag sa pinulongan,
  Mga Setting. Sa tuo: delay, graphics card, memory, mga linya ug ang mga tawo sa tawag.
  I-click ang ngalan sa bisan unsang linya aron usbon kini, tul-iron ang tawo, iusa ang duha ka tawo,
  balewalaon ang usa ka tawo o itakda ang pinulongan nga kanunay niyang gamiton. Ang matag pagtul-id
  mopatukma niini.
  "GITAG-AN GIKAN SA KONTEKSTO" = dili klaro ang mga pulong ug gitag-an sa translator ang kahulugan.
  Abuhon nga mga pulong = dili sigurado ang recognizer niini.

MGA SETTING (mga kategorya sa wala, talagsaon nga mga opsyon sa "Advanced")
  Pag-ila       speech model ug asa kini nagdagan, mga pinulongan nga ilhon, pag-ila sa mga pulong,
                mga pulong nga angay mahibal-an (ngalan, termino sa dula, slang), mga termino sa
                League of Legends.
  Paghubad      graphics card (lokal, offline), Online - Gemini (libre nga key), o pareho: online una,
                graphics card isip reserba. Ma-reset ang libre nga limit sa Gemini matag adlaw sa
                09:00 (oras sa Italy).
  Mga tawo      ilha kung kinsa ang nagsulti, hinumdomi ang mga tingog, kat-oni ang pinulongan sa matag
                tawo, lista sa mga nailhang tawo (Ctrl/Shift + click aron mopili og pipila, Delete aron
                kalimtan).
  Discord       mga ngalan ug kinsa ang nagsulti diretso gikan sa Discord app niini nga PC (walay bot),
                i-set up kausa ra gamit ang "Unsaon pag-set up" (mga 2 minutos); mosugod ug mohunong
                uban sa imong mga tawag.
  Overlay ug display  orihinal nga teksto, teksto sa overlay, gidak-on, opacity, kusang pagtago, mga hotkey.
  App           pinulongan sa app, sugdi uban sa Windows, kasaligan, export, bersyon.

OVERLAY
  Usa ka klaro nga kahon ibabaw sa dula (windowed o borderless; dili sa exclusive full screen).
  I-unlock kini sa "Ibalhin ang overlay" aron ma-drag nimo; kusa kining ma-lock pag-usab inig buhi nimo.
  Kung naka-lock, molusot sa dula ang mga click ug mawala kini human sa pipila ka segundo nga hilom.

MGA HOTKEY (mogana sulod sa dula)
  Ctrl+Alt+S sugdi / hunonga      Ctrl+Alt+P i-pause / ipadayon   Ctrl+Alt+C kopyaha ang katapusang hubad
  Ctrl+Alt+O overlay on / off     Ctrl+Alt+L i-lock / i-unlock ang overlay

MGA UPDATE
  Inig abli sa app, pangitaon niini ang mas bag-ong bersyon, hilom kining i-download ug mo-restart
  niini (kung namati ka, inig pindot nimo sa Hunonga). Magpabilin ang mga setting, tingog, login sa
  Discord ug mga model.

PAG-AYO UG PAG-UNINSTALL
  Ayoha: Settings > Apps > AudioTranscriber > Modify, o padagana pag-usab ang setup ug pilia ang Ayoha.
  Ang kulang ra ang i-download; magpabilin ang mga setting ug tingog.
  I-uninstall: Settings > Apps > AudioTranscriber > Uninstall. Pangutan-on kung papason usab ang mga
  model ug ang imong mga setting (mga 8 GB). Lahi nga program ang Ollama nga adunay kaugalingong
  uninstaller.

PRIVACY
  Ang mga tingog, ngalan, setting, key ug login sa Discord magpabilin niini nga PC ra. Kung naka-on ang
  Gemini, ipadala sa Google ang teksto sa matag pulong (dili ang audio) aron hubaron.

MGA FILE
  AudioTranscriber.exe  ang app            Setup.exe     pag-ayo            Uninstall.exe  pagtangtang
  app\                  program            models\       mga speech ug voice model
  ollama_models\        mga translation model  transcripts\  kung pindoton ra ang Export
  settings.json         imong mga setting  speakers.json naka-save nga tingog setup.log    log sa setup
