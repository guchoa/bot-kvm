from flask import Flask, request
from threading import Thread
import os
from bot import grupos_ativos, CLASSES_EMOJIS

app = Flask('')

@app.route('/')
def home():
    return "Bot está vivo! Acesse <a href='/painel'>/painel</a> para ver os grupos ativos."

@app.route('/painel')
def painel():
    html = """
    <html>
    <head>
        <title>PTs KVM OBLIVION</title>
        <style>
            body {
                font-family: 'Segoe UI', sans-serif;
                background-color: #1e1e2f;
                color: #ffffff;
                padding: 2rem;
            }
            h1 {
                color: #00d9ff;
                margin-bottom: 1rem;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 1rem;
                background-color: #2c2f4a;
                border-radius: 8px;
                overflow: hidden;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #3a3d5c;
            }
            th {
                background-color: #383c5d;
            }
            tr:hover {
                background-color: #3a3d5c;
            }
            .classe {
                font-weight: bold;
                white-space: nowrap;
            }
            .vazio {
                font-style: italic;
                color: #888;
            }
        </style>
    </head>
    <body>
        <h1>🛡️ PTs KVM OBLIVION</h1>
        <table>
            <tr>
                <th>Grupo</th>
                <th>Jogadores</th>
            </tr>
    """

    for grupo_id, grupo in grupos_ativos.items():
        if grupo['jogadores']:
            jogadores = "<br>".join(
                f"<span class='classe'>{CLASSES_EMOJIS.get(j['classe'], '')} {j['nome']}</span>"
                for j in grupo["jogadores"]
            )
        else:
            jogadores = "<span class='vazio'>Sem jogadores ainda.</span>"

        html += f"""
            <tr>
                <td><strong>PT {grupo['grupo']}</strong></td>
                <td>{jogadores}</td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """
    return html

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
