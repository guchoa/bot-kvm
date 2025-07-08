from flask import Flask
from threading import Thread
import os
from bot import grupos_ativos, CLASSES_EMOJIS  # importa os dados do seu bot.py

app = Flask('')

@app.route('/')
def home():
    return "Bot está vivo!"

@app.route('/painel')
def painel():
    html = "<h1 style='font-family:sans-serif;'>Grupos ativos</h1><ul>"
    for grupo_id, grupo in grupos_ativos.items():
        jogadores = ", ".join(f"{CLASSES_EMOJIS[j['classe']]} {j['nome']}" for j in grupo["jogadores"])
        html += f"<li><strong>PT {grupo['grupo']}</strong>: {jogadores or 'Sem jogadores'}</li>"
    html += "</ul>"
    return html

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
