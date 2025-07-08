from flask import Flask, jsonify
from threading import Thread
import os

app = Flask('')

# Essa função vai ser atribuída pelo bot para que Flask consiga acessar os dados
get_grupos_ativos = None

@app.route('/')
def home():
    return "Bot está vivo!"

@app.route('/painel')
def painel():
    if get_grupos_ativos is None:
        return "<h1>Erro: dados do bot não disponíveis</h1>", 500

    grupos = get_grupos_ativos()
    # Monta uma tabela simples em HTML com os grupos e jogadores
    html = """
    <html lang="pt-br">
    <head>
    <meta charset="UTF-8" />
    <title>PTs KVM OBLIVION</title>
    <style>
    body { background: #222; color: #eee; font-family: Arial, sans-serif; padding: 1rem; }
    h1 { color: #4CAF50; text-align: center; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { border: 1px solid #555; padding: 0.5rem; text-align: left; }
    th { background: #444; }
    tr:nth-child(even) { background: #333; }
    </style>
    </head>
    <body>
    <h1>PTs KVM OBLIVION</h1>
    <table>
    <thead><tr><th>Grupo</th><th>Criador (ID)</th><th>Jogadores</th></tr></thead>
    <tbody>
    """

    for grupo_id, info in grupos.items():
        jogadores_html = "<br>".join(
            f"{j['nome']} ({j['classe'].capitalize()})" for j in info['jogadores']
        ) or "<i>Sem jogadores</i>"
        html += f"<tr><td>PT {info['grupo']}</td><td>{info['criador_id']}</td><td>{jogadores_html}</td></tr>"

    html += "</tbody></table></body></html>"

    return html

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
