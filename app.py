from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)

#  Configuração da sessão
app.secret_key = 'minha_senha_secreta'

#  Simulando um banco de dados de usuários
USUARIOS = {"admin": "123"}

#  Simulando produtos disponíveis
PRODUTOS = [
    {"id": 1, "nome": "Iphone 14 Pro", "imagem": "iphone.jpg"},
    {"id": 2, "nome": "Motorola Edge", "imagem": "motorola.jpg"},
    {"id": 3, "nome": "Poco X7 Pro", "imagem": "poco.jpg"},
    {"id": 4, "nome": "Redmi 10C", "imagem": "redmi.jpg"},
    {"id": 5, "nome": "Sansung A04", "imagem": "sansung.jpg"},
]

#  Tela de Login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        if usuario in USUARIOS and USUARIOS[usuario] == senha:
            session['usuario'] = usuario  # Salva o usuário na sessão
            return redirect(url_for('produtos'))

        return "Login falhou! Verifique usuário e senha."

    return render_template('login.html')

#  Tela de Cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        if usuario not in USUARIOS:
            USUARIOS[usuario] = senha  # Adiciona o usuário ao "banco de dados"
            return redirect(url_for('login'))  # Redireciona para login após cadastro
        else:
            return "Usuário já existe!"

    return render_template('cadastro.html')

#  Tela de Produtos (Só acessa se estiver logado)
@app.route('/produtos')
def produtos():
    if 'usuario' not in session:
        return redirect(url_for('login'))  # Se não estiver logado, volta para login

    return render_template('index.html', produtos=PRODUTOS)

#  Rota de Logout (Sair)
@app.route('/logout')
def logout():
    session.pop('usuario', None)  # Remove usuário da sessão
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
