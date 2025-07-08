from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "Bot está vivo!"

@app.route('/painel')
def painel():
    return """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>PTs KVM OBLIVION</title>
        <style>
            body { background: #222; color: #eee; font-family: Arial, sans-serif; text-align: center; padding: 2rem;}
            h1 { color: #4CAF50; }
            p { font-size: 1.2rem; }
        </style>
    </head>
    <body>
        <h1>PTs KVM OBLIVION</h1>
        <p>Bem-vinda ao painel do bot! 🎮</p>
    </body>
    </html>
    """

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
