from keep_alive import keep_alive

import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix='!', intents=intents)

CLASSES_EMOJIS = {
    'sacerdote': '🟡',
    'monge': '🟨',
    'cacador': '🟢',
    'bardo': '🟩',
    'odalisca': '🟩',
    'cavaleiro': '🔴',
    'templario': '🟥',
    'bruxo': '🔵',
    'sabio': '🟦',
    'ferreiro': '<:bolinha_ciano:1390774772903841893>',
    'alquimista': '<:quadrado_ciano:1390774774871097414>',
    'assassino': '🟣',
    'arruaceiro': '🟪'
}

# Armazena os jogadores por mensagem de grupo
grupos_ativos = {}  # {msg_id: {'grupo': 1, 'jogadores': [{'id': id, 'nome': nome, 'classe': classe}]}}

class GrupoView(discord.ui.View):
    def __init__(self, grupo_numero, mensagem=None):
        super().__init__(timeout=None)
        self.grupo_numero = grupo_numero
        self.mensagem = mensagem

        for classe, emoji_str in CLASSES_EMOJIS.items():
            if emoji_str.startswith('<:'):
                nome = emoji_str.split(':')[1]
                id = int(emoji_str.split(':')[2][:-1])
                emoji = discord.PartialEmoji(name=nome, id=id)
            else:
                emoji = emoji_str

            button = discord.ui.Button(
                label=classe.capitalize(),
                emoji=emoji,
                style=discord.ButtonStyle.secondary,  # Botões cinzas
                custom_id=classe
            )
            button.callback = self.gerar_callback(classe)
            self.add_item(button)

    def gerar_callback(self, classe):
        async def callback(interaction: discord.Interaction):
            msg_id = self.mensagem.id
            user = interaction.user
            nome = interaction.guild.get_member(user.id).display_name

            grupo = grupos_ativos.get(msg_id)
            if not grupo:
                await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
                return

            # Remove se já estava na lista
            grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user.id]

            # Adiciona nova entrada
            grupo['jogadores'].append({
                'id': user.id,
                'nome': nome,
                'classe': classe
            })

            # Recria o corpo da mensagem
            linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
            descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

            embed = discord.Embed(
                title=f"PT {grupo['grupo']}",
                description=descricao,
                color=0x2B2D31
            )
            await self.mensagem.edit(embed=embed, view=self)
            await interaction.response.send_message(f"Você entrou como **{classe.capitalize()}**!", ephemeral=True)

        return callback

@bot.command(name='criargrupo')
async def criar_grupo(ctx, numero: int):
    if not (1 <= numero <= 20):
        await ctx.send("Número de PT inválido. Use um número entre 1 e 20.")
        return

    embed = discord.Embed(
        title=f"PT {numero}",
        description="*Sem jogadores ainda.*",
        color=0x2B2D31
    )

    view = GrupoView(grupo_numero=numero)
    mensagem = await ctx.send(embed=embed, view=view)
    view.mensagem = mensagem  # associar a mensagem real à View

    # Registrar grupo
    grupos_ativos[mensagem.id] = {
        'grupo': numero,
        'jogadores': []
    }

@bot.event
async def on_ready():
    print(f'Bot está online! Logado como {bot.user} (ID: {bot.user.id})')
keep_alive()
bot.run('MTM5MDc2NDc0MzUzMDExOTQxMA.GQZiOz.aZN8Goo3edK_O2V80pVWJ-Hf1PyPwasnimsxyE')
