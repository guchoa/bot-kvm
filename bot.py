import os
import logging
from keep_alive import keep_alive

import discord
from discord.ext import commands
import asyncio

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
    'bruxo': '🔵',
    'sabio': '🟦',
    'ferreiro': '<:bolinha_ciano:1391827989267878030>',
    'alquimista': '<:quadrado_ciano:1391827991218225244>',
    'assassino': '🟣',
    'arruaceiro': '🟪'
}

grupos_ativos = {}

class GrupoView(discord.ui.View):
    def __init__(self, grupo_numero, criador_id, mensagem):
        super().__init__(timeout=None)
        self.grupo_numero = grupo_numero
        self.criador_id = criador_id
        self.mensagem = mensagem

        # Linha 0: botões das classes
        for classe, emoji_str in CLASSES_EMOJIS.items():
            if emoji_str.startswith('<:'):
                nome = emoji_str.split(':')[1]
                id = int(emoji_str.split(':')[2][:-1])
                emoji = discord.PartialEmoji(name=nome, id=id, animated=False)
            else:
                emoji = emoji_str

            button = discord.ui.Button(
                label=classe.capitalize(),
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                custom_id=f"classe_{classe}_{grupo_numero}"
            )
            button.callback = self.gerar_callback(classe)
            self.add_item(button)  # row=0 implícito

        # Linha 1: botões administrativos
        btn_sair = discord.ui.Button(label="❌ Sair do Grupo", style=discord.ButtonStyle.danger, row=1, custom_id=f"sair_{grupo_numero}")
        btn_fechar = discord.ui.Button(label="🔒 Fechar Grupo", style=discord.ButtonStyle.primary, row=1, custom_id=f"fechar_{grupo_numero}")
        btn_recriar = discord.ui.Button(label="♻️ Recriar Grupo", style=discord.ButtonStyle.secondary, row=1, custom_id=f"recriar_{grupo_numero}")
        btn_apagar = discord.ui.Button(label="🗑️ Apagar Grupo", style=discord.ButtonStyle.danger, row=1, custom_id=f"apagar_{grupo_numero}")

        btn_sair.callback = self.sair_callback
        btn_fechar.callback = self.fechar_callback
        btn_recriar.callback = self.recriar_callback
        btn_apagar.callback = self.apagar_callback

        self.add_item(btn_sair)
        self.add_item(btn_fechar)
        self.add_item(btn_recriar)
        self.add_item(btn_apagar)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        grupo = grupos_ativos.get(self.mensagem.id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return False

        # Botão sair liberado para todos
        if custom_id.startswith("sair_"):
            return True

        # Botões de classe liberados para todos
        if custom_id.startswith("classe_"):
            return True

        # Só o criador pode fechar, recriar, apagar
        if custom_id.startswith(("fechar_", "recriar_", "apagar_")):
            if user_id != grupo['criador_id']:
                await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
                return False
            return True

        return False

    def gerar_callback(self, classe):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            grupo = grupos_ativos.get(self.mensagem.id)
            if not grupo:
                await interaction.followup.send("Erro: grupo não encontrado.", ephemeral=True)
                return

            user = interaction.user
            nome = interaction.guild.get_member(user.id).display_name

            # Remove usuário de qualquer classe antes de adicionar novamente
            grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user.id]

            if len(grupo['jogadores']) >= 5:
                await interaction.followup.send("Este grupo já atingiu o limite de 5 jogadores.", ephemeral=True)
                return

            grupo['jogadores'].append({'id': user.id, 'nome': nome, 'classe': classe})

            linhas = [f"{CLASSES_EMOJIS[j['classe']]} {j['nome']}" for j in grupo['jogadores']]
            descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

            embed = discord.Embed(
                title=f"PT {grupo['grupo']}",
                description=descricao,
                color=0x2B2D31
            )
            await self.mensagem.edit(embed=embed, view=self)
            await interaction.followup.send(f"Você entrou como **{classe.capitalize()}**!", ephemeral=True)
        return callback

    async def sair_callback(self, interaction: discord.Interaction):
        grupo = grupos_ativos.get(self.mensagem.id)
        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        user_id = interaction.user.id
        jogadores_antes = len(grupo['jogadores'])
        grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user_id]

        if len(grupo['jogadores']) == jogadores_antes:
            await interaction.response.send_message("Você não estava nesse grupo.", ephemeral=True)
            return

        linhas = [f"{CLASSES_EMOJIS[j['classe']]} {j['nome']}" for j in grupo['jogadores']]
        descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

        embed = discord.Embed(
            title=f"PT {grupo['grupo']}",
            description=descricao,
            color=0x2B2D31
        )
        await self.mensagem.edit(embed=embed, view=self)
        await interaction.response.send_message("Você saiu do grupo.", ephemeral=True)

    async def fechar_callback(self, interaction: discord.Interaction):
        grupo = grupos_ativos.get(self.mensagem.id)
        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        if interaction.user.id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True
        await self.mensagem.edit(view=self)
        await interaction.response.send_message(f"O grupo PT {grupo['grupo']} foi fechado para novas inscrições.", ephemeral=True)

    async def recriar_callback(self, interaction: discord.Interaction):
        grupo = grupos_ativos.get(self.mensagem.id)
        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        if interaction.user.id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return

        novo_embed = discord.Embed(
            title=f"PT {grupo['grupo']}",
            description="*Sem jogadores ainda.*",
            color=0x2B2D31
        )
        nova_view = GrupoView(grupo_numero=grupo['grupo'], criador_id=interaction.user.id, mensagem=None)
        nova_msg = await self.mensagem.channel.send(embed=novo_embed, view=nova_view)
        nova_view.mensagem = nova_msg
        grupos_ativos[nova_msg.id] = {
            'grupo': grupo['grupo'],
            'jogadores': [],
            'criador_id': interaction.user.id,
            'mensagem': nova_msg
        }
        await interaction.response.send_message("Grupo recriado com sucesso.", ephemeral=True)

    async def apagar_callback(self, interaction: discord.Interaction):
        grupo = grupos_ativos.get(self.mensagem.id)
        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        if interaction.user.id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return

        await self.mensagem.delete()
        grupos_ativos.pop(self.mensagem.id, None)
        await interaction.response.send_message("Grupo apagado com sucesso.", ephemeral=True)


@bot.command()
async def criargrupo(ctx, intervalo: str):
    try:
        start, end = map(int, intervalo.split('-'))
    except Exception:
        await ctx.send("Formato inválido. Use: !criargrupo 1-3")
        return

    for num in range(start, end + 1):
        embed = discord.Embed(
            title=f"PT {num}",
            description="*Sem jogadores ainda.*",
            color=0x2B2D31
        )
        view = GrupoView(grupo_numero=num, criador_id=ctx.author.id, mensagem=None)
        mensagem = await ctx.send(embed=embed, view=view)
        view.mensagem = mensagem

        grupos_ativos[mensagem.id] = {
            'grupo': num,
            'jogadores': [],
            'criador_id': ctx.author.id,
            'mensagem': mensagem
        }
    await ctx.message.delete()


@bot.event
async def on_ready():
    logging.info(f'Bot está online! Logado como {bot.user} (ID: {bot.user.id})')


keep_alive()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    logging.error("ERRO: variável de ambiente DISCORD_BOT_TOKEN não encontrada.")
    exit(1)

async def start_bot():
    retry_delay = 5
    max_delay = 300
    tentativas = 0
    max_tentativas = 10
    while tentativas < max_tentativas:
        try:
            logging.info("Tentando conectar no Discord...")
            await bot.start(TOKEN)
        except Exception as e:
            logging.error(f"Erro ao conectar: {e}")
            tentativas += 1
            logging.info(f"Tentativa {tentativas}/{max_tentativas} - Repetindo conexão em {retry_delay} segundos...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)
        else:
            logging.info("Bot desconectado normalmente.")
            break
    else:
        logging.error("Número máximo de tentativas atingido. Encerrando o bot.")

if __name__ == "__main__":
    asyncio.run(start_bot())
