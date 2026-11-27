AudioTranscriber 1.6.0 - transcription et traduction vocales en direct
======================================================================

CE QU'IL FAIT
  Il écoute les applis que tu choisis (comme Discord), écrit ce que dit chaque personne et le traduit en
  direct dans la langue de ton choix. La reconnaissance vocale tourne sur ce PC. La traduction tourne
  aussi sur ce PC, ou en ligne avec Gemini si tu l'actives. Pas de compte, rien n'est enregistré sur
  le disque.

INSTALLATION
  Lance Setup.exe. Le premier écran demande la langue de l'appli (celle de Windows est
  déjà sélectionnée). L'installation prépare tout étape par étape (environ 8 Go, 10-20 minutes). Si une
  ancienne copie est trouvée, ses modèles, paramètres et voix sont réutilisés. Ouvre ensuite
  AudioTranscriber depuis le bureau ou le menu Démarrer. Tu peux changer la langue de l'appli à tout
  moment avec le bouton drapeau dans la barre de gauche.

DÉMARRER
  1. Rejoins un appel Discord. Discord apparaît sous "ÉCOUTER" (point vert = joue du son).
  2. Clique sur Démarrer. Chaque phrase apparaît avec qui l'a dite, l'heure, la traduction et ce qui a
     été entendu.
  3. L'onde montre le volume. "Auto" suit le bruit de fond de chaque personne ; fais glisser la ligne
     pointillée pour le régler à la main.
  Le bouton casque à côté de Démarrer change en un clic les langues à reconnaître.

LA FENÊTRE
  Barre de gauche : En direct, Personnes, Mots à connaître, Overlay, Verrouiller l'overlay, Vider,
  drapeau de langue, Paramètres. À droite : délai, carte graphique, mémoire, lignes et les gens de l'appel.
  Clique sur un nom dans une ligne pour le renommer, corriger la personne, fusionner deux personnes,
  ignorer quelqu'un ou fixer la langue qu'elle parle toujours. Chaque correction le rend plus précis.
  "DÉDUIT DU CONTEXTE" = les mots n'étaient pas clairs et le traducteur a deviné le sens.
  Mots en gris = la reconnaissance n'en était pas sûre.

PARAMÈTRES (catégories à gauche, options rares sous "Avancé")
  Reconnaissance  modèle de parole et où il tourne, langues à reconnaître, détection des phrases, mots
                  à connaître (noms, termes de jeu, argot), termes de League of Legends.
  Traduction      carte graphique (en local, hors ligne), En ligne - Gemini (clé gratuite), ou les deux :
                  d'abord en ligne, la carte graphique en secours. La limite gratuite quotidienne de
                  Gemini est remise à zéro à 09:00 (heure italienne).
  Personnes       reconnaître qui parle, se souvenir des voix, apprendre la langue de chaque personne,
                  liste des personnes connues (Ctrl/Maj + clic pour en choisir plusieurs, Suppr pour
                  les oublier).
  Discord         noms et qui parle directement depuis l'appli Discord sur ce PC (pas de bot), à
                  configurer une fois avec "Comment le configurer" (environ 2 minutes) ; démarrage et
                  arrêt avec tes appels.
  Overlay & affichage  texte original, texte de l'overlay, taille, opacité, masquage auto, raccourcis.
  Appli           langue de l'appli, démarrage avec Windows, fiabilité, export, version.

OVERLAY
  Une boîte transparente par-dessus le jeu (fenêtré ou sans bordure ; pas en plein écran exclusif).
  "Déplacer l'overlay" le déverrouille pour que tu le fasses glisser ; il se reverrouille tout seul
  quand tu le lâches. Verrouillé, les clics passent au jeu et il s'efface après quelques secondes
  de silence.

RACCOURCIS (marchent dans les jeux)
  Ctrl+Alt+S démarrer / arrêter   Ctrl+Alt+P pause / reprendre    Ctrl+Alt+C copier la dernière traduction
  Ctrl+Alt+O overlay oui / non    Ctrl+Alt+L verrouiller / déverrouiller l'overlay

MISES À JOUR
  À l'ouverture, l'appli cherche une version plus récente, la télécharge en silence et redémarre dessus
  (si tu écoutes, dès que tu cliques sur Arrêter). Paramètres, voix, connexion Discord et modèles sont
  gardés.

RÉPARER ET DÉSINSTALLER
  Réparer : Paramètres > Applications > AudioTranscriber > Modifier, ou relance l'installation et
  choisis Réparer. Elle ne télécharge que ce qui manque ; paramètres et voix sont gardés.
  Désinstaller : Paramètres > Applications > AudioTranscriber > Désinstaller. Elle demande s'il faut
  aussi supprimer les modèles et tes paramètres (environ 8 Go). Ollama est un programme à part avec son
  propre programme de désinstallation.

CONFIDENTIALITÉ
  Voix, noms, paramètres, clés et connexion Discord restent uniquement sur ce PC. Avec Gemini activé, le
  texte de chaque phrase (pas le son) est envoyé à Google pour être traduit.

FICHIERS
  AudioTranscriber.exe  l'appli               Setup.exe     réparer          Uninstall.exe  supprimer
  app\                  programme             models\       modèles de parole et de voix
  ollama_models\        modèles de traduction transcripts\  seulement quand tu exportes
  settings.json         tes paramètres        speakers.json voix enregistrées  setup.log    journal d'installation
