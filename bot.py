import os
import logging
import discord
from discord.ext import commands
import asyncio
from keep_alive import keep_alive, set_grupos_ativos_func

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

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

        classes = list(CLASSES_EMOJIS.items())
        for idx in range(5):
            classe, emoji_str = classes[idx]
            self.add_item(self._criar_botao(classe, emoji_str, 0))
        for idx in range(5, 10):
            classe, emoji_str = classes[idx]
            self.add_item(self._criar_botao(classe, emoji_str, 1))
        for idx in range(10, 13):
            classe, emoji_str = classes[idx]
            self.add_item(self._criar_botao(classe, emoji_str, 2))

        self._add_botoes_admin()

    def _criar_botao(self, classe, emoji_str, row):
        emoji = self._parse_emoji(emoji_str)
        btn = discord.ui.Button(
            label=classe.capitalize(),
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            row=row,
            custom_id=f"classe_{classe}_{self.grupo_numero}"
        )
        btn.callback = self.gerar_callback(classe)
        return btn

    def _add_botoes_admin(self):
        botoes = [
            ("❌ Sair do Grupo", discord.ButtonStyle.danger, self.sair_callback),
            ("🔒 Fechar Grupo", discord.ButtonStyle.primary, self.fechar_callback),
            ("♻️ Recriar Grupo", discord.ButtonStyle.secondary, self.recriar_callback),
            ("🗑️ Apagar Grupo", discord.ButtonStyle.danger, self.apagar_callback)
        ]
        for i, (label, style, callback) in enumerate(botoes):
            btn = discord.ui.Button(label=label, style=style, row=3)
            btn.callback = callback
            self.add_item(btn)

    def _parse_emoji(self, emoji_str):
        if emoji_str.startswith('<:'):
            nome = emoji_str.split(':')[1]
            id = int(emoji_str.split(':')[2][:-1])
            return discord.PartialEmoji(name=nome, id=id, animated=False)
        return emoji_str

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        msg_id = self.mensagem.id if self.mensagem else None
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return False

        if any(custom_id.startswith(prefix) for prefix in ["classe_", "sair_"]):
            return True

        if user_id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return False

        return True

    def gerar_callback(self, classe):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            msg_id = self.mensagem.id
            user = interaction.user
            nome = interaction.guild.get_member(user.id).display_name

            grupo_atual = grupos_ativos.get(msg_id)
            if not grupo_atual:
                await interaction.followup.send("Erro: grupo não encontrado.", ephemeral=True)
                return

            # Remove jogador de outro grupo
            for g_id, g in grupos_ativos.items():
                if any(j['id'] == user.id for j in g['jogadores']) and g_id != msg_id:
                    g['jogadores'] = [j for j in g['jogadores'] if j['id'] != user.id]

            # Remove do grupo atual (caso esteja repetido)
            grupo_atual['jogadores'] = [j for j in grupo_atual['jogadores'] if j['id'] != user.id]

            if len(grupo_atual['jogadores']) >= 5:
                await interaction.followup.send("Este grupo já atingiu o limite de 5 jogadores.", ephemeral=True)
                return

            grupo_atual['jogadores'].append({
                'id': user.id,
                'nome': nome,
                'classe': classe
            })

            linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo_atual['jogadores']]
            descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

            embed = discord.Embed(
                title=f"PT {grupo_atual['grupo']}",
                description=descricao,
                color=0x2B2D31
            )
            await self.mensagem.edit(embed=embed, view=self)
            await interaction.followup.send(f"Você entrou como **{classe.capitalize()}**!", ephemeral=True)

        return callback

    async def sair_callback(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        jogadores_antes = len(grupo['jogadores'])
        grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user_id]

        if len(grupo['jogadores']) == jogadores_antes:
            await interaction.response.send_message("Você não estava nesse grupo.", ephemeral=True)
            return

        linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
        descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

        embed = discord.Embed(
            title=f"PT {grupo['grupo']}",
            description=descricao,
            color=0x2B2D31
        )
        await self.mensagem.edit(embed=embed, view=self)
        await interaction.response.send_message("Você saiu do grupo.", ephemeral=True)

    async def fechar_callback(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupos_ativos.pop(msg_id, None)
        await self.mensagem.delete()
        await interaction.response.send_message("Grupo fechado pelo criador.", ephemeral=True)

    async def recriar_callback(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)
        if grupo:
            grupo['jogadores'].clear()
            embed = discord.Embed(
                title=f"PT {grupo['grupo']} (Recriado)",
                description="*Sem jogadores ainda.*",
                color=0x2B2D31
            )
            await self.mensagem.edit(embed=embed, view=self)
            await interaction.response.send_message("Grupo recriado pelo criador.", ephemeral=True)

    async def apagar_callback(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupos_ativos.pop(msg_id, None)
        await self.mensagem.delete()
        await interaction.response.send_message("Grupo apagado pelo criador.", ephemeral=True)

@bot.command()
async def criargrupo(ctx, intervalo: str):
    try:
        partes = intervalo.split("-")
        inicio = int(partes[0])
        fim = int(partes[1])
    except Exception:
        await ctx.send("Uso correto: !criargrupo 1-3")
        return

    for num in range(inicio, fim + 1):
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
            'criador_id': ctx.author.id,
            'jogadores': []
        }
    await ctx.message.delete()

@bot.command()
@commands.has_permissions(manage_messages=True)
async def limpargrupos(ctx):
    canal = ctx.channel
    to_remove = []
    async for msg in canal.history(limit=100):
        if msg.id in grupos_ativos:
            try:
                await msg.delete()
                to_remove.append(msg.id)
            except Exception:
                pass
    for msg_id in to_remove:
        grupos_ativos.pop(msg_id, None)
    await ctx.send(f"🧹 Limpeza feita! {len(to_remove)} grupos apagados.", delete_after=10)

@bot.event
async def on_ready():
    logging.info(f'Bot está online! Logado como {bot.user} (ID: {bot.user.id})')

# Painel web com acesso a grupos_ativos
keep_alive()
set_grupos_ativos_func(lambda: grupos_ativos)

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    logging.error("ERRO: variável de ambiente DISCORD_BOT_TOKEN não encontrada.")
    exit(1)

async def start_bot():
    retry_delay = 5
    max_delay = 300
    tentativas = 0
    while tentativas < 10:
        try:
            logging.info("Tentando conectar no Discord...")
            await bot.start(TOKEN)
        except Exception as e:
            logging.error(f"Erro ao conectar: {e}")
            tentativas += 1
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)
        else:
            break
    else:
        logging.error("Número máximo de tentativas atingido. Encerrando o bot.")

if __name__ == "__main__":
    asyncio.run(start_bot())
