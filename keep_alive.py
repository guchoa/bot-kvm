from flask import Flask, jsonify
from threading import Thread
import os

app = Flask('')

# Essa função será definida pelo bot para acessar os dados dos grupos
get_grupos_ativos = None

@app.route('/')
def home():
    return "Bot está vivo!"

@app.route('/painel')
def painel():
    if get_grupos_ativos is None:
        return "<h1>Erro: dados do bot não disponíveis</h1>", 500

    grupos = get_grupos_ativos()

    html = """
    <!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>PTs KVM OBLIVION</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto+Mono&family=Roboto&display=swap" rel="stylesheet" />
<style>
  body {
    background: #fff;
    color: #000;
    font-family: 'Roboto', sans-serif;
    margin: 0; 
    padding: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 100vh;
  }
  header {
    font-family: 'Roboto Mono', monospace;
    font-size: 20px;
    color: #000;
    margin-bottom: 30px;
    font-weight: 500;
    text-align: center;
    width: 100%;
    max-width: 1000px;
    text-shadow: 0 0 4px rgba(0,0,0,0.05);
  }
  .cards-container {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
    justify-content: center;
    width: 100%;
    max-width: 1000px;
  }
  .card {
    background: #fff;
    border: 1.8px solid #333;
    border-radius: 10px;
    padding: 18px 24px;
    width: 260px;
    box-shadow: 0 1.5px 5px rgba(0,0,0,0.08);
    transition: box-shadow 0.3s ease, transform 0.3s ease;
    display: flex;
    flex-direction: column;
    cursor: default;
  }
  .card:hover {
    box-shadow: 0 6px 18px rgba(0,0,0,0.12);
    transform: translateY(-6px);
  }
  .card-title {
    font-family: 'Roboto Mono', monospace;
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 14px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 7px;
    text-align: center;
  }
  .player-list {
    font-family: 'Roboto', sans-serif;
    font-size: 13px;
    line-height: 1.4;
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .player {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
  }
  .player:last-child {
    margin-bottom: 0;
  }
  .player-emoji {
    width: 20px;
    height: 20px;
    margin-right: 10px;
    flex-shrink: 0;
    display: inline-flex;
    justify-content: center;
    align-items: center;
    font-size: 20px;
    line-height: 20px;
  }
  .player-emoji img {
    width: 20px;
    height: 20px;
    object-fit: contain;
    display: block;
  }
  .player-name {
    color: #222;
  }
  /* Responsividade básica */
  @media (max-width: 600px) {
    .cards-container {
      flex-direction: column;
      align-items: center;
    }
    .card {
      width: 90%;
      max-width: 320px;
    }
  }
</style>
</head>
<body>

<header>PTs KVM OBLIVION</header>

<div class="cards-container" id="cards-container">
  <!-- Cards vão aqui -->
</div>

<script>
  // Mapear as classes para emojis (incluindo custom emojis como URL)
  const CLASSES_EMOJIS = {
    sacerdote: '🟡',
    monge: '🟨',
    cacador: '🟢',
    bardo: '🟩',
    odalisca: '🟩',
    cavaleiro: '🔴',
    templario: '🟥',
    bruxo: '🔵',
    sabio: '🟦',
    ferreiro: 'custom:1391827989267878030',    // emoji custom: ID do Discord
    alquimista: 'custom:1391827991218225244',
    assassino: '🟣',
    arruaceiro: '🟪'
  };

  // Função que cria o elemento emoji (img para custom, span para unicode)
  function createEmojiElement(classe) {
    const emojiData = CLASSES_EMOJIS[classe.toLowerCase()];
    const container = document.createElement('span');
    container.className = 'player-emoji';

    if (!emojiData) {
      container.textContent = '?';  // fallback
      return container;
    }

    if (emojiData.startsWith('custom:')) {
      // emoji custom do Discord via URL
      const emojiId = emojiData.split(':')[1];
      const img = document.createElement('img');
      img.src = `https://cdn.discordapp.com/emojis/${emojiId}.png`;
      img.alt = classe;
      container.appendChild(img);
    } else {
      // emoji unicode simples
      const span = document.createElement('span');
      span.textContent = emojiData;
      container.appendChild(span);
    }

    return container;
  }

  // Função pra montar um card do grupo
  function montarCard(grupoNum, jogadores) {
    const card = document.createElement('div');
    card.className = 'card';
    card.setAttribute('tabindex', '0');

    const titulo = document.createElement('div');
    titulo.className = 'card-title';
    titulo.textContent = `PT ${grupoNum}`;
    card.appendChild(titulo);

    const lista = document.createElement('div');
    lista.className = 'player-list';

    if (!jogadores || jogadores.length === 0) {
      const vazio = document.createElement('div');
      vazio.textContent = '*Sem jogadores ainda.*';
      vazio.style.fontStyle = 'italic';
      lista.appendChild(vazio);
    } else {
      jogadores.forEach(jogador => {
        const linha = document.createElement('div');
        linha.className = 'player';

        const emojiEl = createEmojiElement(jogador.classe);
        linha.appendChild(emojiEl);

        const nomeEl = document.createElement('div');
        nomeEl.className = 'player-name';
        nomeEl.textContent = jogador.nome;

        linha.appendChild(nomeEl);
        lista.appendChild(linha);
      });
    }

    card.appendChild(lista);
    return card;
  }

  // Função para buscar os dados e atualizar a interface
  async function atualizarGrupos() {
    try {
      const resp = await fetch('/grupos_ativos');
      if (!resp.ok) throw new Error('Erro ao buscar dados');
      const dados = await resp.json();

      // dados = { mensagem_id: { grupo, jogadores, criador_id, canal_id } }
      // Queremos agrupar por grupo_numero (PT), e listar jogadores

      // Montar um Map: chave = grupo_numero, valor = array jogadores
      const gruposMap = new Map();

      for (const key in dados) {
        if (dados.hasOwnProperty(key)) {
          const grupoData = dados[key];
          const num = grupoData.grupo;
          const jogadores = grupoData.jogadores;

          if (!gruposMap.has(num)) {
            gruposMap.set(num, []);
          }
          // Append jogadores deste grupo
          gruposMap.get(num).push(...jogadores);
        }
      }

      // Ordenar grupos pelo número
      const gruposOrdenados = Array.from(gruposMap.entries()).sort((a,b) => a[0] - b[0]);

      const container = document.getElementById('cards-container');
      container.innerHTML = ''; // limpa

      for (const [num, jogadores] of gruposOrdenados) {
        const card = montarCard(num, jogadores);
        container.appendChild(card);
      }

      // Se nenhum grupo, mostrar mensagem
      if (gruposOrdenados.length === 0) {
        container.innerHTML = '<p style="font-style: italic; color:#555;">Nenhum grupo ativo no momento.</p>';
      }
    } catch(err) {
      console.error('Erro ao atualizar grupos:', err);
    }
  }

  // Atualiza ao carregar e a cada 5 segundos
  atualizarGrupos();
  setInterval(atualizarGrupos, 5000);
</script>

</body>
</html>
    """
    return html

@app.route('/grupos_ativos')
def grupos_ativos_api():
    if get_grupos_ativos is None:
        return jsonify({}), 500
    grupos = get_grupos_ativos()
    return jsonify(grupos)

def set_grupos_ativos_func(func):
    global get_grupos_ativos
    get_grupos_ativos = func

def run():
    port = int(os.environ['PORT'])
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
