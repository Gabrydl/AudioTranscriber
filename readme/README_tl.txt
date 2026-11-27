AudioTranscriber 1.6.0 - live na transcription at pagsasalin ng boses
=====================================================================

ANO ANG GINAGAWA NITO
  Pinakikinggan nito ang mga app na pipiliin mo (tulad ng Discord), isinusulat ang sinasabi ng bawat
  tao at isinasalin ito nang live sa wikang gusto mo. Tumatakbo sa PC na ito ang pagkilala ng
  pananalita. Dito rin tumatakbo ang pagsasalin, o online gamit ang Gemini kung bubuksan mo. Walang
  account, walang nire-record sa disk.

PAG-INSTALL
  Patakbuhin ang AudioTranscriber_Setup.exe. Itatanong ng unang screen ang wika ng app (napili na ang
  wika ng Windows mo). Inihahanda ng Setup ang lahat nang hakbang-hakbang (mga 8 GB, 10-20 minuto).
  Kapag may nakitang mas lumang kopya, gagamitin ulit ang mga model, setting at boses nito. Pagkatapos,
  buksan ang AudioTranscriber mula sa desktop o sa Start menu. Mapapalitan mo anumang oras ang wika ng
  app gamit ang flag button sa kaliwang bar.

PAGSISIMULA
  1. Sumali sa tawag sa Discord. Lalabas ang Discord sa "PAKINGGAN" (berdeng tuldok = may audio).
  2. Pindutin ang Simulan. Lalabas ang bawat pangungusap kasama kung sino ang nagsabi, ang oras, ang
     salin at ang narinig.
  3. Ipinapakita ng alon ang lakas ng tunog. Sinusundan ng "Auto" ang ingay sa background ng bawat tao;
     i-drag ang putol-putol na linya para ikaw ang mag-ayos.
  Ang headphones button sa tabi ng Simulan ay mabilis na nagpapalit ng mga wikang kikilalanin.

ANG WINDOW
  Kaliwang bar: Live, Mga tao, Mga salita, Overlay, I-lock ang overlay, Linisin, flag ng wika, Mga Setting.
  Sa kanan: delay, graphics card, memory, mga linya at ang mga tao sa tawag.
  I-click ang pangalan sa kahit anong linya para palitan ito, itama ang tao, pagsamahin ang dalawang
  tao, balewalain ang isang tao o itakda ang wikang lagi niyang gamit. Bawat pagtama ay nagpapatumpak.
  "HINULAAN MULA SA KONTEKSTO" = malabo ang mga salita at hinulaan ng tagasalin ang kahulugan.
  Mga salitang kulay abo = hindi sigurado ang recognizer sa mga ito.

MGA SETTING (mga kategorya sa kaliwa, mga bihirang opsyon sa "Advanced")
  Pagkilala     speech model at kung saan tumatakbo, mga wikang kikilalanin, pagtukoy ng pangungusap,
                mga salitang dapat malaman (pangalan, termino sa laro, slang), mga termino ng League of Legends.
  Pagsasalin    graphics card (lokal, offline), Online - Gemini (libreng key), o pareho: online muna,
                graphics card bilang reserba. Nare-reset ang libreng limit ng Gemini bawat araw ng
                09:00 (oras sa Italy).
  Mga tao       kilalanin kung sino ang nagsasalita, tandaan ang mga boses, alamin ang wika ng bawat tao,
                listahan ng mga kilalang tao (Ctrl/Shift + click para pumili ng ilan, Delete para kalimutan).
  Discord       mga pangalan at kung sino ang nagsasalita diretso mula sa Discord app sa PC na ito (walang
                bot), isang beses lang i-set up gamit ang "Paano ito i-set up" (mga 2 minuto); magsisimula
                at hihinto kasabay ng mga tawag mo.
  Overlay at display  orihinal na teksto, teksto ng overlay, laki, opacity, kusang pagtago, mga hotkey.
  App           wika ng app, simulan kasabay ng Windows, pagiging maaasahan, export, bersyon.

OVERLAY
  Isang malinaw na kahon sa ibabaw ng laro (windowed o borderless; hindi sa exclusive full screen).
  Ina-unlock ito ng "Ilipat ang overlay" para ma-drag mo; kusa itong nagla-lock ulit pagbitaw mo.
  Kapag naka-lock, tumatagos sa laro ang mga click at naglalaho ito pagkalipas ng ilang segundong tahimik.

MGA HOTKEY (gumagana sa loob ng laro)
  Ctrl+Alt+S simulan / ihinto     Ctrl+Alt+P i-pause / ituloy     Ctrl+Alt+C kopyahin ang huling salin
  Ctrl+Alt+O overlay on / off     Ctrl+Alt+L i-lock / i-unlock ang overlay

MGA UPDATE
  Pagbukas ng app, hinahanap nito ang mas bagong bersyon, tahimik itong dina-download at nagre-restart
  dito (kung nakikinig ka, pagkapindot mo ng Ihinto). Nananatili ang mga setting, boses, login sa
  Discord at mga model.

PAG-AYOS AT PAG-UNINSTALL
  Ayusin: Settings > Apps > AudioTranscriber > Modify, o patakbuhin ulit ang setup at piliin ang
  Ayusin. Ang kulang lang ang dina-download; nananatili ang mga setting at boses.
  I-uninstall: Settings > Apps > AudioTranscriber > Uninstall. Itatanong kung buburahin din ang mga
  model at ang mga setting mo (mga 8 GB). Hiwalay na program ang Ollama na may sariling uninstaller.

PRIVACY
  Ang mga boses, pangalan, setting, key at login sa Discord ay nasa PC na ito lang. Kapag naka-on ang
  Gemini, ipinapadala sa Google ang teksto ng bawat pangungusap (hindi ang audio) para isalin.

MGA FILE
  AudioTranscriber.exe  ang app            Setup.exe     pag-ayos           Uninstall.exe  pag-alis
  app\                  program            models\       mga speech at voice model
  ollama_models\        mga translation model  transcripts\  kapag pinindot lang ang Export
  settings.json         mga setting mo     speakers.json naka-save na boses setup.log      log ng setup
