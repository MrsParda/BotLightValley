# Bot de RPG Escolar (Discord)

Um bot de Discord desenvolvido em Python usando `py-cord` para gerenciar um sistema de RPG de mesa focado em um ambiente escolar. Ele conta com sistemas de criação de fichas, atributos, gerenciamento de aulas, cronogramas automáticos, economia baseada em "estrelas" e uma loja interativa para compra de aptidões e habilidades.

## 🛠️ Tecnologias Utilizadas
* **Python 3.8+**
* **Py-cord** (Fork do `discord.py` com suporte a Slash Commands e UI)
* **SQLite3** (Banco de dados leve e embutido)
* **Python-dotenv** (Para gerenciamento de variáveis de ambiente)

## ⚙️ Instalação e Configuração

1. **Clone ou baixe o repositório** para a sua máquina local.

2. **Instale as dependências** executando o comando abaixo no seu terminal:
   ```bash
   pip install py-cord python-dotenv
   ```

3. **Configure as Variáveis de Ambiente**:
   Crie um arquivo chamado `.env` na raiz do projeto e adicione o token do seu bot do Discord:
   ```env
   DISCORD_TOKEN=seu_token_do_discord_aqui
   ```

4. **Configuração de Servidor (Guild ID)**:
   No arquivo `main.py`, o bot está configurado para atualizar os comandos instantaneamente em um servidor de testes específico (`debug_guilds=[1463713376210391103]`). 
   * **Recomendação**: Altere esse ID para o ID do seu próprio servidor para testar os comandos imediatamente.

5. **Inicie o bot**:
   ```bash
   python main.py
   ```
   *(O banco de dados `escola.db` será gerado automaticamente na primeira execução).*

## 📜 Funcionalidades e Comandos

O bot utiliza **Slash Commands** (`/`) e é dividido em diferentes módulos (Cogs):

### 👤 Cadastro (Fichas e Personagens)
* `/criar_personagem [@usuario]`: Abre o formulário interativo para criar a ficha de um aluno (Origem, Atributos Base e Aptidões).
* `/ficha [@usuario]`: Exibe a ficha do personagem com botões de navegação para ver Atributos, Habilidades, Aptidões e Boletim Acadêmico.
* `/deletar_personagem [id]`: [ADM] Remove um personagem do banco de dados.

### 📚 Aulas e Progressão
* `/criar_materia`, `/editar_materia`, `/deletar_materia`: [ADM] Gerencia a grade curricular e associa matérias aos canais do servidor.
* `/criar_topico`, `/editar_topico`, `/deletar_topico`: [ADM] Gerencia os tópicos (assuntos) estudados dentro de uma matéria.
* `/avaliar_aluno`: [ADM] Recompensa o aluno com estrelas (moeda) e aumenta seu domínio na matéria ao aprender um tópico novo na sala de aula.
* `/ver_materias`, `/ver_topicos`: Lista as opções cadastradas.

### ⏰ Cronograma (Eventos Automáticos)
* `/criar_horario`: [ADM] Agenda uma aula para um dia da semana e horário específicos.
* `/ver_cronograma`: [ADM] Mostra a grade escolar completa.
* **Sistema Automático**: A cada minuto, o bot verifica o cronograma. Se houver uma aula agendada para o horário atual, ele envia um aviso automático no canal da matéria informando que o professor chegou e os tópicos da aula.

### 🛒 Loja e Economia
* `/setup_loja`: [ADM] Instala botões interativos em um canal para os jogadores acessarem o balcão da loja (Atributos, Habilidades ou Aptidões).
* `/adquirir`: Comando manual para comprar conhecimentos.
* `/dar_estrelas`: [ADM] Dá (ou remove) estrelas do saldo de um personagem.
* **Sistema de UI**: A loja funciona via menus e botões no próprio Discord, deduzindo os custos em Estrelas ou Fichas de forma automática.

### 📖 Biblioteca (Base de Dados do RPG)
* `/criar_origem`, `/editar_origem`, `/deletar_origem`: [ADM] Gerencia as origens base (Humanídio, Sombrio, etc.) e seus bônus de atributo.
* `/criar_aptidao`, `/editar_aptidao`, `/deletar_aptidao`: [ADM] Gerencia as aptidões disponíveis para os jogadores comprarem.
* `/ver_origens`, `/ver_aptidoes`: Exibe as opções disponíveis no sistema.

## 📂 Estrutura de Arquivos

```text
/
├── main.py             # Arquivo principal que inicializa o bot
├── .env                # Variáveis de ambiente (não incluso no código fonte)
├── escola.db           # Banco de dados SQLite (gerado automaticamente)
└── cogs/               # Módulos do bot
    ├── aulas.py
    ├── biblioteca.py
    ├── cadastro.py
    ├── cronograma.py
    ├── economia.py
    └── loja.py
```