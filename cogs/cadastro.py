import discord
from discord.ext import commands
import sqlite3

class DropdownAbas(discord.ui.Select):
    def __init__(self, view_perfil):
        options = [
            discord.SelectOption(label="Geral", description="Atributos e informações", emoji="👤", value="Geral"),
            discord.SelectOption(label="Habilidades", description="Conhecimentos de combate", emoji="⚔️", value="Habilidades"),
            discord.SelectOption(label="Aptidões", description="Capacidades passivas", emoji="🌿", value="Aptidões"),
            discord.SelectOption(label="Conhecimentos", description="Conhecimentos", emoji="⭐", value="Conhecimento")
        ]
        super().__init__(placeholder="📜 Navegar pela ficha...", options=options, row=1)
        self.v = view_perfil

    async def callback(self, interaction: discord.Interaction):
        self.v.aba_atual = self.values[0]
        self.v.item_index = 0
        
        for opt in self.options:
            opt.default = (opt.value == self.v.aba_atual)
            
        self.v.atualizar_botoes()
        await interaction.response.edit_message(embed=self.v.gerar_embed(), view=self.v)
class PaginaPerfil(discord.ui.View):
    def __init__(self, personagens, usuario_alvo, cursor):
        super().__init__(timeout=1000)
        self.personagens = personagens
        self.usuario = usuario_alvo
        self.cursor = cursor
        
        self.char_index = 0
        self.item_index = 0 
        self.aba_atual = "Geral"

        self.habilidades_char = []
        self.aptidoes_char = []

        self.boletim_char = {}
        self.materias_lista = []
        
        self.carregar_conhecimentos()
        self.add_item(DropdownAbas(self))
        self.atualizar_botoes()

    def carregar_conhecimentos(self):
        aluno_id = self.personagens[self.char_index][0]
        self.cursor.execute('''
            SELECT b.nome, b.descricao, b.tipo, b.custo_folego
            FROM posses p 
            JOIN biblioteca b ON p.conhecimento_id = b.id 
            WHERE p.aluno_id = ?
        ''', (aluno_id,))
        todos = self.cursor.fetchall()
        
        self.habilidades_char = [item for item in todos if item[2] == 'Habilidade']
        self.aptidoes_char = [item for item in todos if item[2] == 'Aptidão']

        self.cursor.execute('''
            SELECT m.nome, t.nome
            FROM boletim b
            JOIN topicos t ON b.topico_id = t.id
            JOIN materias m ON t.materia_id = m.id
            WHERE b.aluno_id = ?
        ''', (aluno_id,))
        boletim_bruto = self.cursor.fetchall()
        
        self.boletim_char = {}
        for materia, topico in boletim_bruto:
            if materia not in self.boletim_char:
                self.boletim_char[materia] = []
            self.boletim_char[materia].append(topico)
            
        self.materias_lista = list(self.boletim_char.keys())
    
    def gerar_embed(self):
        char = self.personagens[self.char_index]
        embed = discord.Embed(color=0x2b2d31)
        embed.title = f"Ficha: {char[1]}"

        linha = "━━━━━━━━━━━━━━━━━━━━━"

        corpo, mente, coracao = char[5], char[6], char[7]
        attr_folego = char[8] if len(char) > 8 else 'corpo'
        folego_treino = char[9] if len(char) > 9 else 0
        folego_atual = char[10] if len(char) > 10 else 130
        fichas_apt = char[11] if len(char) > 12 else 0
        fichas_hab = char[12] if len(char) > 11 else 3

        total = len(self.personagens)

        valor_base = corpo if attr_folego == 'corpo' else (mente if attr_folego == 'mente' else coracao)
        f_maximo = 100 + (valor_base * 10) + folego_treino
        folego_txt = f"**Fôlego:** {folego_atual}/{f_maximo}"
        total_chars = len(self.personagens)

        if self.aba_atual == "Geral":
            status = f"💪 **{corpo}** \u2003 🧠 **{mente}** \u2003 ❤️ **{coracao}**"

            embed.description = f"**Player:** {self.usuario.mention}\n**Origem:** {char[4]}"
            embed.add_field(name="Atributos", value=status, inline=False)
            embed.add_field(name="Registro", value=f"🆔 `#{char[0]}`", inline=True)
            embed.set_footer(text=f"[{self.char_index + 1}/{total}]")
        
        elif self.aba_atual == "Habilidades":
            if not self.habilidades_char:
                embed.description = f"{folego_txt}\n{linha}\n\nEste personagem não possui habilidades.\nVá até a loja e use suas 🎫 **Fichas de Habilidade**"
                embed.set_footer(text="Habilidade [0/0]")
            else:
                hab = self.habilidades_char[self.item_index]
                embed.description = f"{folego_txt}\n{linha}\n\n**{hab[0]}**\n> {hab[1]}"
                embed.set_footer(text=f"Habilidade [{self.item_index + 1}/{len(self.habilidades_char)}]")

        elif self.aba_atual == "Aptidões":
            if not self.aptidoes_char:
                embed.description = "Este personagem não possui aptidões."
                embed.set_footer(text="Aptidão [0/0]")
            else:
                apt = self.aptidoes_char[self.item_index]
                embed.description = f"**{apt[0]}**\n> {apt[1]}"
                embed.set_footer(text=f"Aptidão [{self.item_index + 1}/{len(self.aptidoes_char)}]")
        
        elif self.aba_atual == "Conhecimento":
            if self.item_index == 0:
                embed.add_field(name="Economia", value=f"> ⭐ **Estrelas:** {char[3]}", inline=False)
                embed.add_field(name="Fichas", value=f"> 🎫 **Fichas de Habilidade:** {fichas_hab}\n> 🌿 **Fichas de Aptidão:** {fichas_apt}", inline=False)
                embed.set_footer(text=f"Conhecimentos [{self.char_index + 1}/{total}]")

                if not self.materias_lista:
                    embed.add_field(name="Boletim Acadêmico", value="*Nenhuma matéria estudada ainda.*", inline=False)
                else:
                    texto_boletim = ""
                    for mat in self.materias_lista:
                        pct = min(len(self.boletim_char[mat]) * 10, 100)
                        barras = "█" * (pct // 10) + "░" * (10 - (pct // 10))
                        texto_boletim += f"**{mat}:** `[{barras}]` {pct}%\n"
                    embed.add_field(name="Boletim Acadêmico", value=texto_boletim, inline=False)
                
                embed.set_footer(text="Página Principal | Use as setas para ver os tópicos aprendidos")
            else:
                mat_atual = self.materias_lista[self.item_index - 1]
                topicos_estudados = self.boletim_char[mat_atual]
                pct = min(len(topicos_estudados) * 10, 100)
                barras = "█" * (pct // 10) + "░" * (10 - (pct // 10))
                
                lista_topicos = "\n".join([f"✔️ {t}" for t in topicos_estudados])
                
                embed.add_field(
                    name=f"📚 Matéria: {mat_atual}", 
                    value=f"**Domínio:** `[{barras}]` {pct}%\n\n**Tópicos Aprendidos:**\n{lista_topicos}", 
                    inline=False
                )
                embed.set_footer(text=f"Matéria [{self.item_index}/{len(self.materias_lista)}]")

        return embed

    def atualizar_botoes(self):
        if self.aba_atual == "Geral":
            self.anterior.disabled = (self.char_index == 0)
            self.proximo.disabled = (self.char_index == len(self.personagens) - 1)
        elif self.aba_atual == "Conhecimento":
            self.anterior.disabled = (self.item_index == 0)
            self.proximo.disabled = (self.item_index == len(self.materias_lista))
        elif self.aba_atual == "Habilidades":
            self.anterior.disabled = (self.item_index == 0)
            self.proximo.disabled = (len(self.habilidades_char) <= 1 or self.item_index == len(self.habilidades_char) - 1)
        elif self.aba_atual == "Aptidões":
            self.anterior.disabled = (self.item_index == 0)
            self.proximo.disabled = (len(self.aptidoes_char) <= 1 or self.item_index == len(self.aptidoes_char) - 1)

    @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.gray)
    async def anterior(self, button, interaction):
        if self.aba_atual == "Geral" and self.char_index > 0:
            self.char_index -= 1
            self.item_index = 0
            self.carregar_conhecimentos()
        elif self.aba_atual != "Geral" and self.item_index > 0:
            self.item_index -= 1
            
        self.atualizar_botoes()
        await interaction.response.edit_message(embed=self.gerar_embed(), view=self)

    @discord.ui.button(label="Próximo ➡️", style=discord.ButtonStyle.gray)
    async def proximo(self, button, interaction):
        if self.aba_atual == "Geral" and self.char_index < len(self.personagens) - 1:
            self.char_index += 1
            self.item_index = 0
            self.carregar_conhecimentos()
        elif self.aba_atual == "Conhecimento" and self.item_index < len(self.materias_lista):
            self.item_index += 1
        elif self.aba_atual == "Habilidades" and self.item_index < len(self.habilidades_char) - 1:
            self.item_index += 1
        elif self.aba_atual == "Aptidões" and self.item_index < len(self.aptidoes_char) - 1:
            self.item_index += 1

        self.atualizar_botoes()
        await interaction.response.edit_message(embed=self.gerar_embed(), view=self)

class ModalNome(discord.ui.Modal):
    def __init__(self, bot, cursor, conn, alvo):
        super().__init__(title="Passo 1: Nome do Personagem")
        self.bot, self.cursor, self.conn, self.alvo = bot, cursor, conn, alvo
        self.add_item(discord.ui.InputText(label="Nome do Personagem", placeholder="Ex: Elrian Montenegro"))

    async def callback(self, interaction: discord.Interaction):
        dados_ficha = {
            'alvo': self.alvo, 'nome': self.children[0].value, 
            'origem_data': None, 'pontos': {"corpo": 0, "mente": 0, "coracao": 0}, 
            'aptidoes': [], 'atributo_folego': None
        }
        view = ViewOrigem(self.bot, self.cursor, self.conn, dados_ficha)
        await interaction.response.send_message(f"✨ Criando **{dados_ficha['nome']}**\n\n**Passo 2:** Selecione a Origem do seu personagem.", view=view, ephemeral=True)
class ViewOrigem(discord.ui.View):
    def __init__(self, bot, cursor, conn, dados_ficha):
        super().__init__(timeout=600)
        self.bot, self.cursor, self.conn, self.df = bot, cursor, conn, dados_ficha
        
        self.cursor.execute("SELECT nome, categoria, atributo_bonus, descricao FROM origens")
        origens = self.cursor.fetchall()
        if origens:
            options = [discord.SelectOption(label=o[0], description=f"{o[1]} | Bônus: {o[2]}") for o in origens]
            sel = discord.ui.Select(placeholder="Escolha sua Origem...", options=options)
            sel.callback = self.selecionar
            self.add_item(sel)

    async def selecionar(self, interaction: discord.Interaction):
        nome_origem = interaction.data['values'][0]
        self.cursor.execute("SELECT * FROM origens WHERE nome = ?", (nome_origem,))
        self.df['origem_data'] = self.cursor.fetchone()
        await interaction.response.defer()

    @discord.ui.button(label="Próximo Passo ➡️", style=discord.ButtonStyle.success, row=1)
    async def proximo(self, button, interaction):
        if not self.df['origem_data']:
            return await interaction.response.send_message("❌ Selecione uma origem primeiro!", ephemeral=True)
        
        view = ViewAtributos(self.bot, self.cursor, self.conn, self.df)
        await interaction.response.edit_message(content=view.gerar_texto(), view=view)
class ViewAtributos(discord.ui.View):
    def __init__(self, bot, cursor, conn, dados_ficha):
        super().__init__(timeout=600)
        self.bot, self.cursor, self.conn, self.df = bot, cursor, conn, dados_ficha
        self.total = 0

        opcoes = [
            discord.SelectOption(label="Corpo", emoji="💪", description="Fôlego baseado no físico"),
            discord.SelectOption(label="Mente", emoji="🧠", description="Fôlego baseado no foco"),
            discord.SelectOption(label="Coração", emoji="❤️", description="Fôlego baseado na emoção")
        ]
        self.sel_folego = discord.ui.Select(placeholder="Escolha o Atributo Base do Fôlego...", options=opcoes, row=2)
        self.sel_folego.callback = self.selecionar_folego
        self.add_item(self.sel_folego)

    def gerar_texto(self):
        coracao, mente, cora = 3 + self.df['pontos']['corpo'], 3 + self.df['pontos']['mente'], 3 + self.df['pontos']['coracao']
        attr_bonus = self.df['origem_data'][4]
        if attr_bonus == "corpo": coracao += 3
        elif attr_bonus == "mente": mente += 3
        elif attr_bonus == "coracao": cora += 3

        escolha = f"**{self.df['atributo_folego'].capitalize()}**" if self.df.get('atributo_folego') else "Nenhum"

        return f"✨ Criação de **{self.df['nome']}**\n**Passo 3:** Distribua 3 pontos extras.\n\n💪 Corpo: **{coracao}**\n🧠 Mente: **{mente}**\n❤️ Coração: **{cora}**\n\nPontos usados: **{self.total}/3**\n💨 Base do Fôlego: {escolha}"

    async def selecionar_folego(self, interaction: discord.Interaction):
        self.df['atributo_folego'] = interaction.data['values'][0].lower()
        for opt in self.sel_folego.options:
            opt.default = (opt.label.lower() == self.df['atributo_folego'])
        await interaction.response.edit_message(content=self.gerar_texto(), view=self)

    async def distribuir(self, interaction, attr):
        if self.total < 3:
            self.df['pontos'][attr] += 1
            self.total += 1
            await interaction.response.edit_message(content=self.gerar_texto(), view=self)
        else:
            await interaction.response.send_message("❌ Máximo de 3 pontos atingido!", ephemeral=True)

    @discord.ui.button(label="+1 Corpo", style=discord.ButtonStyle.secondary, row=0)
    async def btn_c(self, b, i): await self.distribuir(i, "corpo")
    @discord.ui.button(label="+1 Mente", style=discord.ButtonStyle.secondary, row=0)
    async def btn_m(self, b, i): await self.distribuir(i, "mente")
    @discord.ui.button(label="+1 Coração", style=discord.ButtonStyle.secondary, row=0)
    async def btn_co(self, b, i): await self.distribuir(i, "coracao")
    
    @discord.ui.button(label="🔄 Resetar", style=discord.ButtonStyle.danger, row=1)
    async def reset(self, button, interaction):
        self.df['pontos'] = {"corpo": 0, "mente": 0, "coracao": 0}
        self.total = 0
        await interaction.response.edit_message(content=self.gerar_texto(), view=self)
    @discord.ui.button(label="Próximo Passo ➡️", style=discord.ButtonStyle.success, row=1)
    async def proximo(self, button, interaction):
        if self.total < 3:
            return await interaction.response.send_message("❌ Distribua todos os 3 pontos!", ephemeral=True)
        view = ViewAptidao(self.bot, self.cursor, self.conn, self.df)
        await interaction.response.edit_message(content=f"✨ Criação de **{self.df['nome']}**\n\n**Passo 4:** Escolha 2 Aptidões da biblioteca.", view=view)
class ViewAptidao(discord.ui.View):
    def __init__(self, bot, cursor, conn, dados_ficha):
        super().__init__(timeout=600)
        self.bot, self.cursor, self.conn, self.df = bot, cursor, conn, dados_ficha
        
        self.df['aptidoes'] = [] 
        self.tem_aptidoes = False

        self.cursor.execute("SELECT nome FROM biblioteca WHERE tipo = 'Aptidão'")
        aptidoes = self.cursor.fetchall()

        if aptidoes and len(aptidoes) >= 2:
            self.tem_aptidoes = True
            options = [discord.SelectOption(label=a[0]) for a in aptidoes]
            sel = discord.ui.Select(placeholder="Escolha 2 Aptidões... (Opcional)", min_values=0, max_values=2, options=options)
            sel.callback = self.selecionar
            self.add_item(sel)

    async def selecionar(self, interaction: discord.Interaction):
        self.df['aptidoes'] = interaction.data['values']
        await interaction.response.defer()

    @discord.ui.button(label="Próximo Passo ➡️", style=discord.ButtonStyle.success, row=1)
    async def finalizar(self, button, interaction):
        attr_b = self.df['origem_data'][4]
        coracao = 3 + (3 if attr_b == "corpo" else 0) + self.df['pontos']['corpo']
        mente = 3 + (3 if attr_b == "mente" else 0) + self.df['pontos']['mente']
        corpo = 3 + (3 if attr_b == "coracao" else 0) + self.df['pontos']['coracao']

        attr_folego = self.df['atributo_folego']
        valor_base = coracao if attr_folego == 'corpo' else (mente if attr_folego == 'mente' else corpo)
        folego_maximo = 100 + (valor_base * 10)

        aptidoes_escolhidas = self.df.get('aptidoes', [])
        fichas_aptidao = 2 - len(aptidoes_escolhidas)
        fichas_habilidade = 3
        
        self.cursor.execute('''
            INSERT INTO alunos (nome_personagem, owner_id, origem, corpo, mente, coracao, 
                                atributo_folego, folego_treino, folego_atual, 
                                fichas_habilidade, fichas_aptidao) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (self.df['nome'], self.df['alvo'].id, self.df['origem_data'][1], corpo, mente, coracao, 
              attr_folego, 0, folego_maximo, fichas_habilidade, fichas_aptidao))
        aluno_id = self.cursor.lastrowid

        for a in aptidoes_escolhidas:
            self.cursor.execute("SELECT id FROM biblioteca WHERE nome = ?", (a,))
            aid = self.cursor.fetchone()
            if aid: 
                self.cursor.execute("INSERT INTO posses (aluno_id, conhecimento_id) VALUES (?, ?)", (aluno_id, aid[0]))

        self.conn.commit()

        msg_final = f"🎉 A ficha de **{self.df['nome']}** foi finalizada com sucesso!\n\n"
        msg_final += f"*(Você tem **{fichas_habilidade} Ficha(s) de Habilidade**"
        if fichas_aptidao > 0:
            msg_final += f" e **{fichas_aptidao} Ficha(s) de Aptidão**"
        msg_final += " para gastar mais tarde!)*"
        
        await interaction.response.edit_message(content=msg_final, view=None)
 

class Cadastro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('escola.db')
        self.cursor = self.conn.cursor()

        self.cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS alunos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_personagem TEXT,
                owner_id INTEGER,
                origem TEXT,
                corpo INTEGER DEFAULT 3,
                mente INTEGER DEFAULT 3,
                coracao INTEGER DEFAULT 3,
                estrelas INTEGER DEFAULT 0,
                atributo_folego TEXT,
                folego_treino INTEGER DEFAULT 0,
                folego_atual INTEGER DEFAULT 100,
                fichas_habilidade INTEGER DEFAULT 3,
                fichas_aptidao INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS biblioteca (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE,
                descricao TEXT,
                tipo TEXT,
                custo INTEGER,
                custo_folego INTEGER DEFAULT 0
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS posses (
                aluno_id INTEGER,
                conhecimento_id INTEGER,
                FOREIGN KEY(aluno_id) REFERENCES alunos(id),
                FOREIGN KEY(conhecimento_id) REFERENCES biblioteca(id)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS origens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE,
                descricao TEXT,
                categoria TEXT,
                atributo_bonus TEXT
            )
        ''')
        self.conn.commit()

    @discord.slash_command(name="criar_personagem", description="Registra um personagem e seu player")
    @commands.has_permissions(administrator=True)
    async def criar_personagem(
        self, ctx, 
        usuario: discord.Member = discord.Option(discord.Member, description="Dono da ficha", default=None)
    ):
        alvo = ctx.author

        if usuario and usuario != ctx.author:
            if not ctx.author.guild_permissions.administrator:
                return await ctx.respond("❌ Apenas administradores podem criar fichas para outros jogadores.", ephemeral=True)
            alvo = usuario

        if not ctx.author.guild_permissions.administrator:
            self.cursor.execute("SELECT COUNT(*) FROM alunos WHERE owner_id = ?", (alvo.id,))
            count = self.cursor.fetchone()[0]
            if count >= 2:
                return await ctx.respond("❌ Você já atingiu o limite de 2 personagens!", ephemeral=True)

        modal = ModalNome(self.bot, self.cursor, self.conn, alvo)
        await ctx.send_modal(modal)
    
    @discord.slash_command(name="deletar_personagem", description="[ADM] Remove uma ficha permanentemente")
    @commands.has_permissions(administrator=True)
    async def deletar_personagem(self, ctx, id_ficha: int):
        self.cursor.execute('SELECT nome_personagem FROM alunos WHERE id = ?', (id_ficha,))
        personagem = self.cursor.fetchone()

        if not personagem:
            return await ctx.respond(f"❌ Nenhuma ficha encontrada com o ID `#{id_ficha}`.", ephemeral=True)

        nome_char = personagem[0]

        try:
            self.cursor.execute('DELETE FROM alunos WHERE id = ?', (id_ficha,))
            
            self.cursor.execute('DELETE FROM posses WHERE aluno_id = ?', (id_ficha,))
            
            self.conn.commit()
            
            await ctx.respond(f"🗑️ A ficha de **{nome_char}** (ID `#{id_ficha}`) foi deletada com sucesso!")
        except Exception as e:
            await ctx.respond(f"❌ Erro ao deletar do banco de dados: {e}", ephemeral=True)

   
    @discord.slash_command(name="ficha", description="Mostra o personagem do usuário")
    async def ficha(self, ctx, usuario: discord.Member = discord.Option(discord.Member, "selecione um player", default=None)):
        target = usuario or ctx.author
        
        if target.id != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.respond("❌ Você não tem permissão para ver o perfil de outros alunos! Use somente */ficha*", ephemeral=True)
        
        self.cursor.execute('SELECT * FROM alunos WHERE owner_id = ?', (target.id,))
        resultados = self.cursor.fetchall()
        
        if not resultados:
            return await ctx.respond(f"❓ {target.display_name} não possui personagens cadastrados.", ephemeral=True)

        view = PaginaPerfil(resultados, target, self.cursor)
        await ctx.respond(embed=view.gerar_embed(), view=view, ephemeral=True)
    
def setup(bot):
    bot.add_cog(Cadastro(bot))