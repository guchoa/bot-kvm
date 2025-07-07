import os
from keep_alive import keep_alive

import discord
from discord.ext import commands
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

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
    def __init__(self, grupo_numero, criador_id=None, mensagem=None):
        super().__init__(timeout=None)
        self.grupo_numero = grupo_numero
        self.criador_id = criador_id
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
        self.add_item(discord.ui.Button(label="🔒 Fechar Grupo", style=discord.ButtonStyle.primary, custom_id="fechar"))
        self.add_item(discord.ui.Button(label="♻️ Recriar Grupo", style=discord.ButtonStyle.secondary, custom_id="recriar"))
        self.add_item(discord.ui.Button(label="🗑️ Apagar Grupo", style=discord.ButtonStyle.danger, custom_id="apagar"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return False

        # Permitir que qualquer um saia a qualquer momento
        if custom_id == "sair":
            grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user_id]
            linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
            descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"
            embed = discord.Embed(title=f"PT {grupo['grupo']}", description=descricao, color=0x2B2D31)
            await self.mensagem.edit(embed=embed, view=self)
            await interaction.response.send_message("Você saiu do grupo.", ephemeral=True)
            return False

        # Demais ações só para o criador do grupo
        if grupo['criador_id'] != user_id:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return False

        if custom_id == "fechar":
            for item in self.children:
                item.disabled = True
            await self.mensagem.edit(view=self)
            await interaction.response.send_message(f"O grupo PT {grupo['grupo']} foi fechado para novas inscrições.", ephemeral=True)
            return False

        if custom_id == "apagar":
            await self.mensagem.delete()
            grupos_ativos.pop(msg_id, None)
            await interaction.response.send_message("Grupo apagado com sucesso.", ephemeral=True)
            return False

        if custom_id == "recriar":
            novo_embed = discord.Embed(title=f"PT {grupo['grupo']}", description="*Sem jogadores ainda.*", color=0x2B2D31)
            nova_view = GrupoView(grupo_numero=grupo['grupo'], criador_id=user_id)
            nova_msg = await self.mensagem.channel.send(embed=novo_embed, view=nova_view)
            nova_view.mensagem = nova_msg
            grupos_ativos[nova_msg.id] = {
                'grupo': grupo['grupo'],
                'jogadores': [],
                'criador_id': user_id,
                'mensagem': nova_msg
            }
            await interaction.response.send_message("Grupo recriado com sucesso.", ephemeral=True)
            return False

        return True

    def gerar_callback(self, classe):
        async def callback(interaction: discord.Interaction):
            # Defer pra evitar flood e timeout rápido
            await interaction.response.defer(ephemeral=True)

            msg_id = self.mensagem.id
            user = interaction.user
            membro = interaction.guild.get_member(user.id)
            nome = membro.display_name if membro else user.name

            grupo = grupos_ativos.get(msg_id)
            if not grupo:
                await interaction.followup.send("Erro: grupo não encontrado.", ephemeral=True)
                return

            # Se já estiver no grupo, remove antes de adicionar (trocar de classe)
            grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user.id]

            if len(grupo['jogadores']) >= 5:
                await interaction.followup.send("Este grupo já atingiu o limite de 5 jogadores.", ephemeral=True)
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
            await interaction.followup.send(f"Você entrou como **{classe.capitalize()}**!", ephemeral=True)

        return callback

@bot.command(name='criargrupo')
async def criar_grupo(ctx, intervalo: str):
    try:
        if '-' in intervalo:
            inicio, fim = map(int, intervalo.split('-'))
            if not (1 <= inicio <= 20 and 1 <= fim <= 20) or inicio > fim:
                await ctx.send("Intervalo inválido. Use números entre 1 e 20, como !criargrupo 1-5.")
                return
            numeros = range(inicio, fim + 1)
        else:
            numero = int(intervalo)
            if not (1 <= numero <= 20):
                await ctx.send("Número de PT inválido. Use um número entre 1 e 20.")
                return
            numeros = [numero]
    except ValueError:
        await ctx.send("Formato inválido. Use !criargrupo 1 ou !criargrupo 1-5.")
        return

    await ctx.message.delete()

    for numero in numeros:
        embed = discord.Embed(
            title=f"PT {numero}",
            description="*Sem jogadores ainda.*",
            color=0x2B2D31
        )
        view = GrupoView(grupo_numero=numero, criador_id=ctx.author.id)
        mensagem = await ctx.send(embed=embed, view=view)
        view.mensagem = mensagem

        grupos_ativos[mensagem.id] = {
            'grupo': numero,
            'jogadores': [],
            'criador_id': ctx.author.id,
            'mensagem': mensagem
        }
        await asyncio.sleep(1)  # pausa de 1 segundo para evitar flood

@bot.event
async def on_ready():
    print(f'Bot está online! Logado como {bot.user} (ID: {bot.user.id})')

# Mantém o Flask alive numa thread paralela
keep_alive()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    print("ERRO: variável de ambiente DISCORD_BOT_TOKEN não encontrada.")
    exit(1)

# Função com retry exponencial para evitar crash por 429 e outros erros
async def start_bot():
    retry_delay = 5
    max_delay = 300
    tentativas = 0
    max_tentativas = 10

    while tentativas < max_tentativas:
        try:
            print("Tentando conectar no Discord...")
            await bot.start(TOKEN)
        except Exception as e:
            logging.error(f"Erro ao conectar: {e}")
            print(f"Repetindo conexão em {retry_delay} segundos...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)
            tentativas += 1
        else:
            print("Bot desconectado normalmente.")
            break
    else:
        print("Número máximo de tentativas atingido. Saindo.")
        exit(1)

if __name__ == "__main__":
    asyncio.run(start_bot())
