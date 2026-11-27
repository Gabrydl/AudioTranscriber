AudioTranscriber 1.6.0 - transcrição e tradução de voz em direto
================================================================

O QUE FAZ
  Ouve as aplicações que escolher (como o Discord), escreve o que cada pessoa diz e traduz em direto
  para a língua que preferir. O reconhecimento de fala corre neste PC. A tradução também corre neste
  PC, ou online com o Gemini se o ativar. Sem conta, nada é gravado no disco.

INSTALAÇÃO
  Execute o Setup.exe. O primeiro ecrã pergunta a língua da aplicação (a língua do
  Windows já vem selecionada). A instalação prepara tudo passo a passo (cerca de 8 GB, 10 a 20 minutos).
  Se encontrar uma cópia anterior, reutiliza os modelos, as definições e as vozes dela. Depois abra o
  AudioTranscriber a partir do ambiente de trabalho ou do menu Iniciar. Pode mudar a língua da aplicação
  quando quiser com o botão da bandeira na barra à esquerda.

COMEÇAR
  1. Entre numa chamada do Discord. O Discord aparece em "OUVIR" (ponto verde = a tocar áudio).
  2. Carregue em Iniciar. Cada frase aparece com quem a disse, a hora, a tradução e o que foi ouvido.
  3. A onda mostra o volume. "Auto" acompanha o ruído de fundo de cada pessoa; arraste a linha
     tracejada para o ajustar à mão.
  O botão de auscultadores ao lado de Iniciar alterna as línguas a reconhecer com um clique.

A JANELA
  Barra à esquerda: Em direto, Pessoas, Palavras a conhecer, Overlay, Bloquear overlay, Limpar, bandeira
  da língua, Definições. À direita: atraso, placa gráfica, memória, linhas e as pessoas na chamada.
  Clique num nome em qualquer linha para lhe mudar o nome, corrigir a pessoa, juntar duas pessoas,
  ignorar alguém ou fixar a língua que fala sempre. Cada correção torna tudo mais preciso.
  "DEDUZIDO DO CONTEXTO" = as palavras não estavam claras e o tradutor deduziu o sentido.
  Palavras a cinzento = o reconhecedor não tinha a certeza delas.

DEFINIÇÕES (categorias à esquerda, opções raras em "Avançado")
  Reconhecimento  modelo de fala e onde corre, línguas a reconhecer, deteção de frases, palavras a
                  conhecer (nomes, termos de jogo, calão), termos de League of Legends.
  Tradução        placa gráfica (local, offline), Online - Gemini (chave gratuita), ou as duas:
                  primeiro online, a placa gráfica como reserva. O limite gratuito diário do Gemini
                  repõe-se às 09:00 (hora de Itália).
  Pessoas         reconhecer quem fala, lembrar as vozes, aprender a língua de cada pessoa, lista das
                  pessoas conhecidas (Ctrl/Shift + clique para escolher várias, Delete para as esquecer).
  Discord         nomes e quem está a falar diretamente da aplicação Discord neste PC (sem bot),
                  configurado uma vez com "Como configurar" (cerca de 2 minutos); inicia/para junto
                  com as suas chamadas.
  Overlay e ecrã  texto original, texto do overlay, tamanho, opacidade, desaparecer sozinho, atalhos.
  Aplicação       língua da aplicação, iniciar com o Windows, fiabilidade, exportar, versão.

OVERLAY
  Uma caixa transparente por cima do jogo (modo janela ou sem margens; não em ecrã inteiro exclusivo).
  "Mover o overlay" desbloqueia-o para o poder arrastar; volta a bloquear-se sozinho quando o larga.
  Bloqueado, os cliques passam para o jogo e desaparece após alguns segundos de silêncio.

ATALHOS (funcionam dentro dos jogos)
  Ctrl+Alt+S iniciar / parar      Ctrl+Alt+P pausar / retomar    Ctrl+Alt+C copiar a última tradução
  Ctrl+Alt+O overlay sim / não    Ctrl+Alt+L bloquear / desbloquear o overlay

ATUALIZAÇÕES
  Quando a aplicação abre, procura uma versão mais recente, transfere-a em silêncio e reinicia com ela
  (se estiver a ouvir, assim que carregar em Parar). Definições, vozes, sessão do Discord e modelos
  mantêm-se.

REPARAR E DESINSTALAR
  Reparar: Definições > Aplicações > AudioTranscriber > Modificar, ou execute de novo a instalação e
  escolha Reparar. Transfere só o que falta; definições e vozes mantêm-se.
  Desinstalar: Definições > Aplicações > AudioTranscriber > Desinstalar. Pergunta se apaga também os
  modelos e as definições (cerca de 8 GB). O Ollama é um programa à parte com o seu próprio desinstalador.

PRIVACIDADE
  Vozes, nomes, definições, chaves e a sessão do Discord ficam só neste PC. Com o Gemini ativado, o
  texto de cada frase (não o áudio) é enviado à Google para ser traduzido.

FICHEIROS
  AudioTranscriber.exe  a aplicação         Setup.exe     reparar          Uninstall.exe  remover
  app\                  programa            models\       modelos de fala e de voz
  ollama_models\        modelos de tradução transcripts\  só quando carrega em Exportar
  settings.json         as suas definições  speakers.json vozes guardadas  setup.log      registo da instalação
