AudioTranscriber 1.6.0 - puheen litterointi ja käännös reaaliajassa
===================================================================

MITÄ SE TEKEE
  Se kuuntelee valitsemiasi sovelluksia (kuten Discordia), kirjoittaa ylös, mitä kukin sanoo, ja
  kääntää sen reaaliajassa valitsemallesi kielelle. Puheentunnistus toimii tällä koneella. Myös
  käännös toimii tällä koneella tai verkossa Geminillä, jos otat sen käyttöön. Ei vaadi tiliä, mitään ei
  tallenneta levylle.

ASENNUS
  Suorita Setup.exe. Ensimmäisessä näytössä kysytään sovelluksen kieltä (Windowsin kieli on
  jo valittuna). Asennus valmistelee kaiken vaihe vaiheelta (noin 8 Gt, 10–20 minuuttia). Jos aiempi
  kopio löytyy, sen mallit, asetukset ja äänet käytetään uudelleen. Avaa sitten AudioTranscriber
  työpöydältä tai Käynnistä-valikosta. Sovelluksen kielen voi vaihtaa milloin tahansa vasemman
  palkin lippupainikkeesta.

ALOITUS
  1. Liity Discord-puheluun. Discord näkyy kohdassa "KUUNTELE" (vihreä piste = toistaa ääntä).
  2. Napsauta Käynnistä. Jokainen lause näkyy puhujan, kellonajan, käännöksen ja kuullun kanssa.
  3. Aaltomuoto näyttää äänenvoimakkuuden. "Auto" seuraa jokaisen henkilön taustakohinaa; vedä
     katkoviivaa säätääksesi sen itse.
  Käynnistä-painikkeen vieressä oleva kuulokepainike vaihtaa tunnistettavat kielet yhdellä napsautuksella.

IKKUNA
  Vasen palkki: Livenä, Henkilöt, Sanat, Peittokuva, Lukitse peittokuva, Tyhjennä, kielen lippu,
  Asetukset. Oikealla: viive, näytönohjain, muisti, rivit ja puhelun henkilöt.
  Napsauta nimeä millä tahansa rivillä nimetäksesi sen uudelleen, korjataksesi henkilön,
  yhdistääksesi kaksi henkilöä, ohittaaksesi jonkun tai asettaaksesi kielen, jota hän aina puhuu.
  Jokainen korjaus parantaa tarkkuutta.
  "ARVATTU ASIAYHTEYDESTÄ" = sanat olivat epäselviä ja kääntäjä arvasi merkityksen.
  Harmaat sanat = tunnistin ei ollut niistä varma.

ASETUKSET (luokat vasemmalla, harvinaiset valinnat kohdassa "Lisäasetukset")
  Tunnistus     puhemalli ja missä se toimii, tunnistettavat kielet, lauseiden tunnistus,
                tunnettavat sanat (nimet, pelitermit, slangi), League of Legends -termit.
  Käännös       näytönohjain (paikallinen, ilman verkkoa), Verkossa - Gemini (ilmainen avain) tai
                molemmat: ensin verkossa, näytönohjain varalla. Geminin päivittäinen ilmaisraja
                nollautuu klo 09:00 (Italian aikaa).
  Henkilöt      tunnista kuka puhuu, muista äänet, opettele jokaisen kieli, tunnettujen henkilöiden
                luettelo (Ctrl/Vaihto + napsautus valitsee useita, Delete unohtaa ne).
  Discord       nimet ja puhuja suoraan tämän koneen Discord-sovelluksesta (ei bottia), otetaan
                käyttöön kerran kohdasta "Näin otat sen käyttöön" (noin 2 minuuttia); käynnistyy ja
                pysähtyy puheluidesi mukana.
  Peittokuva ja näyttö  alkuperäinen teksti, peittokuvan teksti, koko, peittävyys, automaattinen
                piilotus, pikanäppäimet.
  Sovellus      sovelluksen kieli, käynnistys Windowsin mukana, luotettavuus, vienti, versio.

PEITTOKUVA
  Läpinäkyvä laatikko pelin päällä (ikkuna- tai reunaton tila; ei yksinomainen koko näyttö).
  Siirrä sitä vetämällä hiirellä; lukitse se ennen pelaamista (lukko tai Ctrl+Alt+L).
  Lukittuna napsautukset menevät peliin ja se häviää muutaman hiljaisen sekunnin jälkeen.

PIKANÄPPÄIMET (toimivat peleissä)
  Ctrl+Alt+S käynnistä / pysäytä  Ctrl+Alt+P tauko / jatka       Ctrl+Alt+C kopioi viimeisin käännös
  Ctrl+Alt+O peittokuva päälle / pois   Ctrl+Alt+L lukitse / avaa peittokuva

PÄIVITYKSET
  Avautuessaan sovellus etsii uudemman version, lataa sen hiljaa ja käynnistyy sillä uudelleen (jos
  kuuntelet, heti kun napsautat Pysäytä). Asetukset, äänet, Discord-kirjautuminen ja mallit säilyvät.

KORJAUS JA POISTO
  Korjaus: Asetukset > Sovellukset > AudioTranscriber > Muokkaa tai suorita asennus uudelleen ja
  valitse Korjaa. Se lataa vain puuttuvat tiedostot; asetukset ja äänet säilyvät.
  Poisto: Asetukset > Sovellukset > AudioTranscriber > Poista asennus. Kysyy, poistetaanko myös mallit
  ja asetuksesi (noin 8 Gt). Ollama on erillinen ohjelma, jolla on oma poisto-ohjelmansa.

YKSITYISYYS
  Äänet, nimet, asetukset, avaimet ja Discord-kirjautuminen pysyvät vain tällä koneella. Kun Gemini on
  käytössä, jokaisen lauseen teksti (ei ääni) lähetetään Googlelle käännettäväksi.

TIEDOSTOT
  AudioTranscriber.exe  sovellus          Setup.exe     korjaus          Uninstall.exe  poisto
  app\                  ohjelma           models\       puhe- ja äänimallit
  ollama_models\        käännösmallit     transcripts\  vain kun napsautat Vie
  settings.json         asetuksesi        speakers.json tallennetut äänet  setup.log    asennusloki
