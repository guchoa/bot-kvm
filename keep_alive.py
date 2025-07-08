from flask import Flask
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
    <html lang="pt-br">
    <head>
    <meta charset="UTF-8" />
    <title>PTs KVM OBLIVION</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
      body {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        padding: 20px;
      }
      h1 {
        color: #58a6ff;
        text-align: center;
        margin-bottom: 30px;
        font-weight: 700;
        text-shadow: 0 0 5px #58a6ff;
      }
      .card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 0 10px #23863680;
        transition: transform 0.2s;
      }
      .card:hover {
        transform: scale(1.03);
        box-shadow: 0 0 20px #58a6ff;
      }
      .card-title {
        color: #58a6ff;
        font-weight: 700;
        font-size: 1.5rem;
        margin-bottom: 15px;
        text-align: center;
        text-shadow: 0 0 8px #58a6ff;
      }
      ul.jogadores {
        list-style-type: none;
        padding-left: 0;
        font-size: 1.1rem;
      }
      ul.jogadores li {
        padding: 5px 10px;
        border-bottom: 1px solid #30363d;
        display: flex;
        align-items: center;
        gap: 10px;
      }
      ul.jogadores li:last-child {
        border-bottom: none;
      }
      .emoji {
        font-size: 1.4rem;
      }
      .container-cards {
        max-width: 900px;
        margin: 0 auto;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 20px;
      }
    </style>
    </head>
    <body>
      <h1>PTs KVM OBLIVION</h1>
      <div class="container-cards">
    """

    emojis = {
        'sacerdote': '🟡',
        'monge': '🟨',
        'cacador': '🟢',
        'bardo': '🟩',
        'odalisca': '🟩',
        'cavaleiro': '🔴',
        'templario': '🟥',
        'bruxo': '🔵',
        'sabio': '🟦',
        'ferreiro': '🔵',
        'alquimista': '🔵',
        'assassino': '🟣',
        'arruaceiro': '🟪'
    }

    for grupo_id, info in grupos.items():
        html += f'<div class="card">'
        html += f'<div class="card-body">'
        html += f'<h2 class="card-title">PT {info["grupo"]}</h2>'
        html += '<ul class="jogadores">'
        if info['jogadores']:
            for jogador in info['jogadores']:
                emoji = emojis.get(jogador['classe'].lower(), '❓')
                nome = jogador['nome']
                classe = jogador['classe'].capitalize()
                html += f'<li><span class="emoji">{emoji}</span> {nome} <small style="color:#8b949e;">({classe})</small></li>'
        else:
            html += '<li><i>Sem jogadores ainda.</i></li>'
        html += '</ul></div></div>'

    html += """
      </div>
    </body>
    </html>
    """
    return html

def set_grupos_ativos_func(func):
    global get_grupos_ativos
    get_grupos_ativos = func

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
