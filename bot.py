import os
from keep_alive import keep_alive

import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

CLASSES_EMOJIS = {
    'sacerdote': '🟡',
    'monge': '🟨',
    'cacador': '🟢',
    'bardo': '🟩',
    'odalisca': '🟩',
    'cavaleiro': '🔴',
    'templario': '🟥',
    'bruxo': '🔸',
    'sabio': '🟦',
    'ferreiro': '<:bolinha_ciano:1390774772903841893>',
    'alquimista': '<:quadrado_ciano:1390774774871097414>',
    'assassino': '🟣',
    'arruaceiro': '🟪'
}

grupos_ativos = {}  # {msg_id: {'grupo': 1, 'jogadores': [], 'criador_id': id, 'mensagem': mensagem}}

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
                style=discord.ButtonStyle.secondary,
                custom_id=classe
            )
            button.callback = self.gerar_callback(classe)
            self.add_item(button)

        self.add_item(discord.ui.Button(label="❌ Sair do Grupo", style=discord.ButtonStyle.danger, custom_id="sair"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data.get("custom_id") == "sair":
            msg_id = self.mensagem.id
            grupo = grupos_ativos.get(msg_id)
            if not grupo:
                await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
                return False
            user_id = interaction.user.id
            grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user_id]
            linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
            descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"
            embed = discord.Embed(
                title=f"PT {grupo['grupo']}",
                description=descricao,
                color=0x2B2D31
            )
            await self.mensagem.edit(embed=embed, view=self)
            await interaction.response.send_message("Você saiu do grupo.", ephemeral=True)
            return False
        return True

    def gerar_callback(self, classe):
        async def callback(interaction: discord.Interaction):
            msg_id = self.mensagem.id
            user = interaction.user
            nome = interaction.guild.get_member(user.id).display_name

            grupo = grupos_ativos.get(msg_id)
            if not grupo:
                await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
                return

            grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user.id]

            if len(grupo['jogadores']) >= 5:
                await interaction.response.send_message("Este grupo já está cheio!", ephemeral=True)
                return

            grupo['jogadores'].append({
                'id': user.id,
                'nome': nome,
                'classe': classe
            })

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

class ControlesGerais(discord.ui.View):
    def __init__(self, autor_id):
        super().__init__(timeout=None)
        self.autor_id = autor_id

    @discord.ui.button(label="🩹 Apagar todos os grupos", style=discord.ButtonStyle.danger)
    async def apagar_grupos(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message("Apenas quem criou os grupos pode apagá-los.", ephemeral=True)
            return

        for msg_id in list(grupos_ativos):
            try:
                mensagem = await interaction.channel.fetch_message(msg_id)
                await mensagem.delete()
            except:
                pass
            del grupos_ativos[msg_id]

        await interaction.response.send_message("Todos os grupos foram apagados.", ephemeral=True)

    @discord.ui.button(label="📋 Listar jogadores", style=discord.ButtonStyle.primary)
    async def listar_jogadores(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not grupos_ativos:
            await interaction.response.send_message("Nenhum grupo ativo.", ephemeral=True)
            return

        linhas = []
        for grupo in sorted(grupos_ativos.values(), key=lambda x: x['grupo']):
            jogadores = grupo['jogadores']
            membros = "\n".join([f"{CLASSES_EMOJIS[j['classe']]} {j['nome']}" for j in jogadores]) or "*Sem jogadores ainda.*"
            linhas.append(f"**PT {grupo['grupo']}**\n{membros}\n")

        embed = discord.Embed(title="Resumo dos Grupos", description="\n".join(linhas), color=0x2B2D31)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔒 Fechar inscrições", style=discord.ButtonStyle.secondary)
    async def fechar_inscricoes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message("Apenas quem criou os grupos pode fechá-los.", ephemeral=True)
            return

        for grupo in grupos_ativos.values():
            if grupo['criador_id'] == self.autor_id:
                grupo['mensagem'].view.stop()

        await interaction.response.send_message("Inscrições encerradas para todos os grupos.", ephemeral=True)

    @discord.ui.button(label="🔄 Recriar grupos", style=discord.ButtonStyle.success)
    async def recriar_grupos(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message("Apenas quem criou os grupos pode recriá-los.", ephemeral=True)
            return

        novos_ids = []
        for msg_id in list(grupos_ativos):
            grupo = grupos_ativos[msg_id]
            if grupo['criador_id'] != self.autor_id:
                continue

            embed = discord.Embed(
                title=f"PT {grupo['grupo']}",
                description="*Sem jogadores ainda.*",
                color=0x2B2D31
            )
            view = GrupoView(grupo_numero=grupo['grupo'])
            mensagem = await interaction.channel.send(embed=embed, view=view)
            view.mensagem = mensagem

            novos_ids.append(mensagem.id)
            del grupos_ativos[msg_id]
            grupos_ativos[mensagem.id] = {
                'grupo': grupo['grupo'],
                'jogadores': [],
                'criador_id': self.autor_id,
                'mensagem': mensagem
            }

        await interaction.response.send_message(f"{len(novos_ids)} grupos foram recriados.", ephemeral=True)

@bot.command(name='criargrupo')
async def criar_grupo(ctx, intervalo: str):
    try:
        await ctx.message.delete()
    except:
        pass

    if '-' in intervalo:
        partes = intervalo.split('-')
        try:
            inicio = int(partes[0])
            fim = int(partes[1])
        except ValueError:
            await ctx.send("Formato inválido. Use por exemplo: !criargrupo 1-5")
            return
    else:
        try:
            inicio = fim = int(intervalo)
        except ValueError:
            await ctx.send("Formato inválido. Use por exemplo: !criargrupo 1-5")
            return

    if inicio < 1 or fim > 20 or inicio > fim:
        await ctx.send("Intervalo inválido. Use números entre 1 e 20.")
        return

    for numero in range(inicio, fim + 1):
        embed = discord.Embed(
            title=f"PT {numero}",
            description="*Sem jogadores ainda.*",
            color=0x2B2D31
        )
        view = GrupoView(grupo_numero=numero)
        mensagem = await ctx.send(embed=embed, view=view)
        view.mensagem = mensagem

        grupos_ativos[mensagem.id] = {
            'grupo': numero,
            'jogadores': [],
            'criador_id': ctx.author.id,
            'mensagem': mensagem
        }

    await ctx.send("Grupos criados com sucesso!", view=ControlesGerais(autor_id=ctx.author.id))

@bot.event
async def on_ready():
    print(f'Bot está online! Logado como {bot.user} (ID: {bot.user.id})')

keep_alive()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    print("ERRO: variável de ambiente DISCORD_BOT_TOKEN não encontrada.")
    exit(1)

bot.run(TOKEN)
