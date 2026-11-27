AudioTranscriber 1.6.0 - kõne transkriptsioon ja tõlge reaalajas
================================================================

MIDA SEE TEEB
  See kuulab sinu valitud rakendusi (näiteks Discordi), kirjutab üles, mida iga inimene ütleb, ja
  tõlgib selle reaalajas sinu valitud keelde. Kõnetuvastus töötab selles arvutis. Ka tõlge töötab
  selles arvutis või, kui lülitad selle sisse, võrgus Geminiga. Kontot pole vaja, kettale ei
  salvestata midagi.

PAIGALDAMINE
  Käivita AudioTranscriber_Setup.exe. Esimene ekraan küsib rakenduse keelt (Windowsi keel on juba
  valitud). Paigaldus valmistab kõik samm-sammult ette (umbes 8 GB, 10–20 minutit). Kui leitakse
  varasem koopia, kasutatakse selle mudeleid, seadeid ja hääli uuesti. Seejärel ava AudioTranscriber
  töölaualt või menüüst Start. Rakenduse keelt saad igal ajal muuta vasaku riba lipunupust.

ALUSTAMINE
  1. Liitu Discordi kõnega. Discord ilmub jaotisse "KUULA" (roheline täpp = esitab heli).
  2. Klõpsa Alusta. Iga lause ilmub koos ütleja, kellaaja, tõlke ja kuulduga.
  3. Lainekuju näitab helitugevust. "Auto" jälgib iga inimese taustamüra; lohista punktiirjoont, et
     seda ise sättida.
  Alusta-nupu kõrval olev kõrvaklappide nupp vahetab kiiresti kuulatavaid keeli.

AKEN
  Vasak riba: Otse, Inimesed, Sõnad, Ülekate, Lukusta ülekate, Tühjenda, keele lipp, Seaded.
  Paremal: viivitus, graafikakaart, mälu, read ja kõnes olevad inimesed.
  Klõpsa mis tahes rea nimel, et see ümber nimetada, inimest parandada, kaks inimest liita, kedagi
  eirata või määrata keel, mida ta alati räägib. Iga parandus muudab täpsemaks.
  "KONTEKSTIST ARVATUD" = sõnad olid ebaselged ja tõlkija arvas tähenduse.
  Hallid sõnad = tuvastaja polnud neis kindel.

SEADED (kategooriad vasakul, harvad valikud jaotises "Täpsemalt")
  Tuvastus      kõnemudel ja kus see töötab, tuvastatavad keeled, lausete tuvastus, teada olevad
                sõnad (nimed, mänguterminid, släng), League of Legendsi terminid.
  Tõlge         graafikakaart (kohalik, võrguta), Võrgus - Gemini (tasuta võti) või mõlemad:
                kõigepealt võrgus, graafikakaart varuks. Gemini tasuta päevapiirang lähtestub
                kell 09:00 (Itaalia aja järgi).
  Inimesed      tuvasta, kes räägib, jäta hääled meelde, õpi iga inimese keel, tuntud inimeste
                loend (Ctrl/Shift + klõps mitme valimiseks, Delete nende unustamiseks).
  Discord       nimed ja kõneleja otse selle arvuti Discordi rakendusest (ilma botita), seadistatakse
                üks kord jaotisest "Kuidas seadistada" (umbes 2 minutit); käivitub ja peatub koos
                sinu kõnedega.
  Ülekate ja kuva  originaaltekst, ülekatte tekst, suurus, läbipaistmatus, automaatne peitmine,
                kiirklahvid.
  Rakendus      rakenduse keel, käivitus koos Windowsiga, töökindlus, eksport, versioon.

ÜLEKATE
  Läbipaistev kast mängu peal (aknas või ääristeta režiim; mitte ainuõigusega täisekraan).
  "Liiguta ülekatet" avab luku, et saaksid seda lohistada; lahti lastes lukustub see ise uuesti.
  Lukus olles lähevad klõpsud mängu ja see kaob pärast mõnda vaikset sekundit.

KIIRKLAHVID (töötavad mängudes)
  Ctrl+Alt+S alusta / peata      Ctrl+Alt+P paus / jätka         Ctrl+Alt+C kopeeri viimane tõlge
  Ctrl+Alt+O ülekate sisse / välja   Ctrl+Alt+L lukusta / ava ülekate

UUENDUSED
  Avamisel otsib rakendus uuemat versiooni, laadib selle vaikselt alla ja taaskäivitub sellega (kui
  parajasti kuulad, siis kohe, kui klõpsad Peata). Seaded, hääled, Discordi sisselogimine ja mudelid
  jäävad alles.

PARANDAMINE JA EEMALDAMINE
  Parandamine: Sätted > Rakendused > AudioTranscriber > Muuda või käivita paigaldus uuesti ja vali
  Paranda. Laadib alla ainult puuduva; seaded ja hääled jäävad alles.
  Eemaldamine: Sätted > Rakendused > AudioTranscriber > Desinstalli. Küsib, kas kustutada ka mudelid ja
  sinu seaded (umbes 8 GB). Ollama on eraldi programm oma desinstalliprogrammiga.

PRIVAATSUS
  Hääled, nimed, seaded, võtmed ja Discordi sisselogimine jäävad ainult sellesse arvutisse. Kui Gemini
  on sees, saadetakse iga lause tekst (mitte heli) tõlkimiseks Google'ile.

FAILID
  AudioTranscriber.exe  rakendus          Setup.exe     parandamine      Uninstall.exe  eemaldamine
  app\                  programm          models\       kõne- ja häälemudelid
  ollama_models\        tõlkemudelid      transcripts\  ainult eksportimisel
  settings.json         sinu seaded       speakers.json salvestatud hääled  setup.log   paigalduslogi
