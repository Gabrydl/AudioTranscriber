AudioTranscriber 1.6.0 - transcrição e tradução de voz ao vivo
==============================================================

O QUE ELE FAZ
  Ouve os apps que você escolher (como o Discord), escreve o que cada pessoa fala e traduz ao vivo para
  o idioma que você quiser. O reconhecimento de fala roda neste PC. A tradução também roda neste PC, ou
  online com o Gemini se você ativar. Sem conta, nada é gravado no disco.

INSTALAÇÃO
  Rode o Setup.exe. A primeira tela pergunta o idioma do app (o idioma do Windows já
  vem selecionado). A instalação prepara tudo passo a passo (cerca de 8 GB, 10 a 20 minutos). Se achar
  uma cópia anterior, reaproveita os modelos, as configurações e as vozes dela. Depois abra o
  AudioTranscriber pela área de trabalho ou pelo menu Iniciar. Você pode trocar o idioma do app quando
  quiser com o botão da bandeira na barra à esquerda.

COMEÇAR
  1. Entre numa chamada do Discord. O Discord aparece em "OUVIR" (ponto verde = tocando áudio).
  2. Clique em Iniciar. Cada frase aparece com quem falou, o horário, a tradução e o que foi ouvido.
  3. A onda mostra o volume. "Auto" acompanha o ruído de fundo de cada pessoa; arraste a linha
     tracejada para ajustar na mão.
  O botão com fones ao lado de Iniciar troca rápido os idiomas a reconhecer.

A JANELA
  Barra à esquerda: Ao vivo, Pessoas, Palavras para conhecer, Overlay, Travar overlay, Limpar, bandeira
  do idioma, Configurações. À direita: atraso, placa de vídeo, memória, linhas e as pessoas na chamada.
  Clique num nome em qualquer linha para renomear, corrigir a pessoa, juntar duas pessoas, ignorar
  alguém ou fixar o idioma que ela sempre fala. Cada correção deixa tudo mais preciso.
  "DEDUZIDO PELO CONTEXTO" = as palavras não estavam claras e o tradutor deduziu o sentido.
  Palavras cinzas = o reconhecedor não tinha certeza delas.

CONFIGURAÇÕES (categorias à esquerda, opções raras em "Avançado")
  Reconhecimento  modelo de fala e onde roda, idiomas para reconhecer, detecção de frases, palavras
                  para conhecer (nomes, termos de jogo, gírias), termos de League of Legends.
  Tradução        placa de vídeo (local, offline), Online - Gemini (chave grátis), ou as duas: primeiro
                  online, a placa de vídeo como reserva. O limite grátis do dia do Gemini zera às
                  09:00 (horário da Itália).
  Pessoas         reconhecer quem fala, lembrar as vozes, aprender o idioma de cada pessoa, lista das
                  pessoas conhecidas (Ctrl/Shift + clique para escolher várias, Delete para esquecer).
  Discord         nomes e quem está falando direto do app Discord neste PC (sem bot), configurado uma
                  vez com "Como configurar" (uns 2 minutos); inicia/para junto com suas chamadas.
  Overlay e tela  texto original, texto do overlay, tamanho, opacidade, sumir sozinho, atalhos.
  App             idioma do app, iniciar com o Windows, confiabilidade, exportar, versão.

OVERLAY
  Uma caixa transparente por cima do jogo (modo janela ou sem bordas; não em tela cheia exclusiva).
  Arraste com o mouse para mover; trave (cadeado ou Ctrl+Alt+L) antes de jogar.
  Travado, os cliques passam para o jogo e ele some depois de alguns segundos de silêncio.

ATALHOS (funcionam dentro dos jogos)
  Ctrl+Alt+S iniciar / parar      Ctrl+Alt+P pausar / continuar   Ctrl+Alt+C copiar a última tradução
  Ctrl+Alt+O overlay liga / desliga   Ctrl+Alt+L travar / destravar o overlay

ATUALIZAÇÕES
  Quando o app abre, ele procura uma versão mais nova, baixa em silêncio e reinicia nela (se você
  estiver ouvindo, assim que clicar em Parar). Configurações, vozes, login do Discord e modelos ficam.

REPARAR E DESINSTALAR
  Reparar: Configurações > Apps > AudioTranscriber > Modificar, ou rode a instalação de novo e escolha
  Reparar. Baixa só o que falta; configurações e vozes ficam.
  Desinstalar: Configurações > Apps > AudioTranscriber > Desinstalar. Pergunta se também apaga os
  modelos e as configurações (cerca de 8 GB). O Ollama é um programa separado com desinstalador próprio.

PRIVACIDADE
  Vozes, nomes, configurações, chaves e o login do Discord ficam só neste PC. Com o Gemini ativado, o
  texto de cada frase (não o áudio) é enviado ao Google para ser traduzido.

ARQUIVOS
  AudioTranscriber.exe  o app               Setup.exe     reparar        Uninstall.exe  remover
  app\                  programa            models\       modelos de fala e de voz
  ollama_models\        modelos de tradução transcripts\  só quando você clica em Exportar
  settings.json         suas configurações  speakers.json vozes salvas   setup.log      log da instalação
