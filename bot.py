import os
import logging
import asyncio
import time
import discord
from discord.ext import commands
from keep_alive import keep_alive, set_grupos_ativos_func

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    logging.error("ERRO: variável de ambiente DISCORD_BOT_TOKEN não encontrada.")
    exit(1)

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

        if not mensagem:
            logging.warning(f"GrupoView criado sem mensagem para PT {grupo_numero}")
        else:
            logging.info(f"GrupoView criado para PT {grupo_numero} com mensagem {mensagem.id}")

        classes = list(CLASSES_EMOJIS.items())

        # Cache para cooldown por usuário: {user_id: (classe, timestamp)}
        self._cooldown_cache = {}

        # Botões organizados em 3 linhas: 5 + 5 + 3
        for idx in range(5):
            classe, emoji_str = classes[idx]
            emoji = self._parse_emoji(emoji_str)
            btn = discord.ui.Button(
                label=classe.capitalize(),
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                row=0,
                custom_id=f"classe_{classe}_{grupo_numero}"
            )
            btn.callback = self.gerar_callback(classe)
            self.add_item(btn)

        for idx in range(5, 10):
            classe, emoji_str = classes[idx]
            emoji = self._parse_emoji(emoji_str)
            btn = discord.ui.Button(
                label=classe.capitalize(),
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                row=1,
                custom_id=f"classe_{classe}_{grupo_numero}"
            )
            btn.callback = self.gerar_callback(classe)
            self.add_item(btn)

        for idx in range(10, 13):
            classe, emoji_str = classes[idx]
            emoji = self._parse_emoji(emoji_str)
            btn = discord.ui.Button(
                label=classe.capitalize(),
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                row=2,
                custom_id=f"classe_{classe}_{grupo_numero}"
            )
            btn.callback = self.gerar_callback(classe)
            self.add_item(btn)

        # Botões extras na linha 3
        btn_sair = discord.ui.Button(label="❌ Sair do Grupo", style=discord.ButtonStyle.danger, row=3, custom_id=f"sair_{grupo_numero}")
        btn_fechar = discord.ui.Button(label="🔒 Fechar Grupo", style=discord.ButtonStyle.primary, row=3, custom_id=f"fechar_{grupo_numero}")
        btn_recriar = discord.ui.Button(label="♻️ Recriar Grupo", style=discord.ButtonStyle.secondary, row=3, custom_id=f"recriar_{grupo_numero}")
        btn_apagar = discord.ui.Button(label="🗑️ Apagar Grupo", style=discord.ButtonStyle.danger, row=3, custom_id=f"apagar_{grupo_numero}")

        btn_sair.callback = self.sair_callback
        btn_fechar.callback = self.fechar_callback
        btn_recriar.callback = self.recriar_callback
        btn_apagar.callback = self.apagar_callback

        self.add_item(btn_sair)
        self.add_item(btn_fechar)
        self.add_item(btn_recriar)
        self.add_item(btn_apagar)

    def _parse_emoji(self, emoji_str):
        if emoji_str.startswith('<:'):
            nome = emoji_str.split(':')[1]
            id = int(emoji_str.split(':')[2][:-1])
            return discord.PartialEmoji(name=nome, id=id, animated=False)
        else:
            return emoji_str

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        msg_id = self.mensagem.id if self.mensagem else None
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return False

        # Todos podem usar os botões de classe e sair, só criador pode os outros
        if any(custom_id.startswith(prefix) for prefix in ["classe_", "sair_"]):
            return True

        if user_id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return False

        return True

    def gerar_callback(self, classe):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            now = time.monotonic()

            # Cooldown simples: 3 segundos por usuário e mesma classe
            last = self._cooldown_cache.get(user_id)
            if last:
                last_classe, last_time = last
                if last_classe == classe and (now - last_time) < 3:
                    # Ignora cliques rápidos repetidos para mesma classe
                    await interaction.response.defer()
                    return
            self._cooldown_cache[user_id] = (classe, now)

            msg_id = self.mensagem.id
            user = interaction.user
            nome = interaction.guild.get_member(user.id).display_name if interaction.guild else user.name

            grupo = grupos_ativos.get(msg_id)
            if not grupo:
                await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
                return

            # Desabilita o botão clicado para evitar flood rápido
            btn_clicado = None
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id == f"classe_{classe}_{self.grupo_numero}":
                    btn_clicado = item
                    break
            if btn_clicado:
                btn_clicado.disabled = True
                try:
                    await self.mensagem.edit(view=self)
                except Exception as e:
                    logging.warning(f"Erro ao desabilitar botão temporariamente: {e}")

            # Remove jogador de outros grupos se estiver
            for g_id, g in grupos_ativos.items():
                if any(j['id'] == user.id for j in g['jogadores']):
                    if g_id != msg_id:
                        g['jogadores'] = [j for j in g['jogadores'] if j['id'] != user.id]
                        canal = bot.get_channel(g['canal_id'])
                        if canal:
                            try:
                                msg_antiga = await canal.fetch_message(g_id)
                                if msg_antiga:
                                    view_antiga = GrupoView(g['grupo'], g['criador_id'], msg_antiga)
                                    linhas_antigas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in g['jogadores']]
                                    desc_antiga = "\n".join(linhas_antigas) if linhas_antigas else "*Sem jogadores ainda.*"
                                    embed_antiga = discord.Embed(
                                        title=f"PT {g['grupo']}",
                                        description=desc_antiga,
                                        color=0x2B2D31
                                    )
                                    await msg_antiga.edit(embed=embed_antiga, view=view_antiga)
                            except Exception as e:
                                logging.warning(f"Erro ao atualizar mensagem antiga: {e}")

            # Limite 5 jogadores no grupo, exceto se já estiver nele
            if len(grupo['jogadores']) >= 5 and all(j['id'] != user.id for j in grupo['jogadores']):
                # Reabilita botão antes de responder
                if btn_clicado:
                    btn_clicado.disabled = False
                    try:
                        await self.mensagem.edit(view=self)
                    except Exception as e:
                        logging.warning(f"Erro ao reabilitar botão: {e}")
                await interaction.response.send_message("Este grupo já atingiu o limite de 5 jogadores.", ephemeral=True)
                return

            entrou = False
            for j in grupo['jogadores']:
                if j['id'] == user.id:
                    j['classe'] = classe
                    entrou = True
                    break

            if not entrou:
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
            try:
                await self.mensagem.edit(embed=embed, view=self)
            except Exception as e:
                logging.warning(f"Falha ao editar mensagem no callback da classe: {e}")

            # Reabilita o botão após edição
            if btn_clicado:
                btn_clicado.disabled = False
                try:
                    await self.mensagem.edit(view=self)
                except Exception as e:
                    logging.warning(f"Erro ao reabilitar botão após edição: {e}")

            await interaction.response.send_message(f"Você entrou como **{classe.capitalize()}**!", ephemeral=True)

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
            await interaction.response.send_message("Você não está nesse grupo.", ephemeral=True)
            return

        linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
        descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

        embed = discord.Embed(
            title=f"PT {grupo['grupo']}",
            description=descricao,
            color=0x2B2D31
        )
        try:
            await self.mensagem.edit(embed=embed, view=self)
        except Exception as e:
            logging.warning(f"Erro ao atualizar mensagem no sair_callback: {e}")

        await interaction.response.send_message("Você saiu do grupo.", ephemeral=True)

    # Seus outros callbacks (fechar_callback, recriar_callback, apagar_callback) seguem aqui, mantidos iguais

# Continue com seus comandos, eventos e keep_alive
# ...

keep_alive()
set_grupos_ativos_func(lambda g: grupos_ativos.update(g))
bot.run(TOKEN)
