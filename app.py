from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = 'minha_senha_secreta'

# Conexão com banco
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='13122015',
    database='catalogo'
)

# Upload config
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('usuario_id') != 1:
            return redirect(url_for('acesso_negado'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------------ CARRINHO ------------------------
@app.route('/carrinho/adicionar', methods=['POST'])
def adicionar_carrinho():
    if 'usuario_id' not in session:
        return jsonify(success=False, message='Não autenticado'), 401

    data = request.get_json()
    produto_id = data.get('produto_id')

    if not produto_id:
        return jsonify(success=False, message='Produto inválido'), 400

    usuario_id = session['usuario_id']
    cursor = conn.cursor(dictionary=True)

    # Verifica ou recria o carrinho do usuário
    cursor.execute("SELECT id FROM Carrinhos WHERE identificador_cliente = %s", (str(usuario_id),))
    carrinho = cursor.fetchone()

    if not carrinho:
        cursor.execute("INSERT INTO Carrinhos (identificador_cliente) VALUES (%s)", (str(usuario_id),))
        conn.commit()
        carrinho_id = cursor.lastrowid
    else:
        carrinho_id = carrinho['id']

    # Garante que o carrinho existe mesmo após deletar tudo
    if not carrinho_id:
        return jsonify(success=False, message='Erro ao criar carrinho'), 500

    # Verifica se o produto já está no carrinho
    cursor.execute("SELECT id FROM Carrinho_Produtos WHERE carrinho_id = %s AND produto_id = %s", (carrinho_id, produto_id))
    item = cursor.fetchone()

    if item:
        cursor.execute("UPDATE Carrinho_Produtos SET quantidade = quantidade + 1 WHERE id = %s", (item['id'],))
    else:
        cursor.execute(
            "INSERT INTO Carrinho_Produtos (carrinho_id, produto_id, quantidade) VALUES (%s, %s, 1)",
            (carrinho_id, produto_id)
        )

    conn.commit()
    return jsonify(success=True)

@app.route('/carrinho/itens')
def carrinho_itens():
    if 'usuario_id' not in session:
        return jsonify({'itens': []})

    try:
        # Verifica se conexão ainda está ativa
        if not conn.is_connected():
            conn.reconnect()

        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM Carrinhos WHERE identificador_cliente = %s", (str(session['usuario_id']),))
        carrinho = cursor.fetchone()

        if not carrinho:
            return jsonify({'itens': []})

        cursor.execute("""
            SELECT p.id, p.nome, cp.quantidade
            FROM Carrinho_Produtos cp
            JOIN Produtos p ON cp.produto_id = p.id
            WHERE cp.carrinho_id = %s
        """, (carrinho['id'],))
        itens = cursor.fetchall()

        return jsonify({'itens': itens})

    except mysql.connector.Error as err:
        print("Erro no MySQL:", err)
        return jsonify({'itens': []}), 500

    finally:
        try:
            cursor.close()
        except:
            pass  # previne erro caso cursor já tenha sido fechado

@app.route('/carrinho/quantidade')
def carrinho_quantidade():
    if 'usuario_id' not in session:
        return jsonify({'quantidade': 0})

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM Carrinhos WHERE identificador_cliente = %s", (str(session['usuario_id']),))
        carrinho = cursor.fetchone()

        if not carrinho:
            return jsonify({'quantidade': 0})

        cursor.execute("SELECT SUM(quantidade) AS total FROM Carrinho_Produtos WHERE carrinho_id = %s", (carrinho['id'],))
        resultado = cursor.fetchone()
        total = resultado['total'] if resultado['total'] else 0

        return jsonify({'quantidade': total})
    finally:
        cursor.close()

@app.route('/carrinho/limpar', methods=['POST'])
def limpar_carrinho():
    if 'usuario_id' not in session:
        return jsonify({'status': 'erro', 'mensagem': 'Não autenticado'}), 401

    cursor = conn.cursor(dictionary=True)
    usuario_id = session['usuario_id']

    # Busca o carrinho do usuário
    cursor.execute("SELECT id FROM Carrinhos WHERE identificador_cliente = %s", (str(usuario_id),))
    carrinho = cursor.fetchone()

    if carrinho:
        carrinho_id = carrinho['id']
        # Remove os produtos do carrinho
        cursor.execute("DELETE FROM Carrinho_Produtos WHERE carrinho_id = %s", (carrinho_id,))
        # Remove o carrinho em si
        cursor.execute("DELETE FROM Carrinhos WHERE id = %s", (carrinho_id,))
        conn.commit()

        return jsonify({'status': 'ok', 'mensagem': 'Carrinho limpo com sucesso'})
    else:
        return jsonify({'status': 'ok', 'mensagem': 'Carrinho já está limpo'})
    
@app.route('/carrinho/remover', methods=['POST'])
def remover_item_carrinho():
    if 'usuario_id' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401

    data = request.get_json()
    produto_id = data.get('produto_id')

    if not produto_id:
        return jsonify({'success': False, 'message': 'Produto inválido'}), 400

    cursor = conn.cursor(dictionary=True)
    usuario_id = session['usuario_id']

    cursor.execute("SELECT id FROM Carrinhos WHERE identificador_cliente = %s", (str(usuario_id),))
    carrinho = cursor.fetchone()

    if not carrinho:
        return jsonify({'success': False, 'message': 'Carrinho não encontrado'}), 404

    carrinho_id = carrinho['id']
    cursor.execute("SELECT id, quantidade FROM Carrinho_Produtos WHERE carrinho_id = %s AND produto_id = %s", (carrinho_id, produto_id))
    item = cursor.fetchone()

    if not item:
        return jsonify({'success': False, 'message': 'Produto não está no carrinho'}), 404

    if item['quantidade'] > 1:
        cursor.execute("UPDATE Carrinho_Produtos SET quantidade = quantidade - 1 WHERE id = %s", (item['id'],))
    else:
        cursor.execute("DELETE FROM Carrinho_Produtos WHERE id = %s", (item['id'],))

    # Verifica se ainda restam itens no carrinho
    cursor.execute("SELECT COUNT(*) AS total FROM Carrinho_Produtos WHERE carrinho_id = %s", (carrinho_id,))
    total_restante = cursor.fetchone()['total']

    if total_restante == 0:
        cursor.execute("DELETE FROM Carrinhos WHERE id = %s", (carrinho_id,))

    conn.commit()
    return jsonify({'success': True, 'carrinho_vazio': total_restante == 0})

@app.route('/finalizar-compra', methods=['POST'])
def finalizar_compra():
    if 'usuario_id' not in session:
        return jsonify(success=False, message="Não autenticado"), 401

    cursor = conn.cursor(dictionary=True)
    usuario_id = session['usuario_id']

    # Buscar nome do usuário (usando o campo "usuario")
    cursor.execute("SELECT usuario FROM Usuarios WHERE id = %s", (usuario_id,))
    usuario = cursor.fetchone()
    nome_usuario = usuario['usuario'] if usuario else "Cliente"

    # Buscar carrinho
    cursor.execute("SELECT id FROM Carrinhos WHERE identificador_cliente = %s", (str(usuario_id),))
    carrinho = cursor.fetchone()

    if not carrinho:
        return jsonify(success=False, message="Carrinho não encontrado")

    carrinho_id = carrinho['id']

    # Buscar produtos do carrinho
    cursor.execute("""
        SELECT p.nome, cp.quantidade
        FROM Carrinho_Produtos cp
        JOIN Produtos p ON cp.produto_id = p.id
        WHERE cp.carrinho_id = %s
    """, (carrinho_id,))
    itens = cursor.fetchall()

    if not itens:
        return jsonify(success=False, message="Carrinho vazio")

    # Adicionar data/hora
    data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M")

    # Monta a mensagem formatada com emojis
    mensagem = f"🛒 *Pedido de Compra*\n"
    mensagem += f"🕒 *Data/Hora:* {data_hora}\n"
    mensagem += f"👤 *Cliente:* {nome_usuario}\n\n"
    mensagem += "📦 *Produtos:*\n"
    for item in itens:
        mensagem += f"• {item['nome']} (x{item['quantidade']})\n"
    mensagem += "\n✅ Aguardo confirmação!"

    # Codifica a mensagem para a URL do WhatsApp
    mensagem_url = quote(mensagem, safe='', encoding='utf-8')
    whatsapp_url = f"https://wa.me/556484590117?text={mensagem_url}"

    # Limpar carrinho
    cursor.execute("DELETE FROM Carrinho_Produtos WHERE carrinho_id = %s", (carrinho_id,))
    cursor.execute("DELETE FROM Carrinhos WHERE id = %s", (carrinho_id,))
    conn.commit()

    return jsonify(success=True, whatsapp_url=whatsapp_url)

# ------------------------ AUTENTICAÇÃO ------------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Usuarios WHERE usuario = %s", (usuario,))
        resultado = cursor.fetchone()

        if resultado and check_password_hash(resultado['senha'], senha):
            session['usuario'] = usuario
            session['usuario_id'] = resultado['id']
            return redirect(url_for('produtos'))

        return redirect(url_for('login', msg='erro_login'))

    return render_template('login.html', msg=request.args.get('msg'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        if len(senha) < 6:
            return redirect(url_for('cadastro', msg='senha_curta'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Usuarios WHERE usuario = %s", (usuario,))
        if cursor.fetchone():
            return redirect(url_for('cadastro', msg='usuario_existe'))

        senha_hash = generate_password_hash(senha)
        cursor.execute("INSERT INTO Usuarios (usuario, senha) VALUES (%s, %s)", (usuario, senha_hash))
        conn.commit()

        return redirect(url_for('cadastro', msg='sucesso'))

    return render_template('login.html', msg=request.args.get('msg'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/acesso-negado')
def acesso_negado():
    return render_template('acesso_negado.html')

# ------------------------ PRODUTOS ------------------------
@app.route('/produtos')
def produtos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Produtos")
    produtos = cursor.fetchall()
    return render_template('index.html', produtos=produtos)

@app.route('/admin/produtos')
@admin_required
def crud_produtos():
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Produtos")
    produtos = cursor.fetchall()
    return render_template('crud_produtos.html', produtos=produtos)

@app.route('/admin/produtos/salvar', methods=['POST'])
def salvar_produto():
    cursor = conn.cursor(dictionary=True)
    id = request.form.get('id')
    nome = request.form['nome']
    descricao = request.form['descricao']
    imagem_file = request.files.get('imagem')
    nome_arquivo = None

    if imagem_file and allowed_file(imagem_file.filename):
        nome_arquivo = secure_filename(imagem_file.filename)
        caminho = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)
        imagem_file.save(caminho)

    if id:
        if nome_arquivo:
            cursor.execute("UPDATE Produtos SET nome=%s, descricao=%s, imagem=%s WHERE id=%s", (nome, descricao, nome_arquivo, id))
        else:
            cursor.execute("UPDATE Produtos SET nome=%s, descricao=%s WHERE id=%s", (nome, descricao, id))
    else:
        cursor.execute("INSERT INTO Produtos (nome, imagem, descricao) VALUES (%s, %s, %s)", (nome, nome_arquivo, descricao))

    conn.commit()
    return redirect(url_for('crud_produtos'))

@app.route('/admin/produtos/excluir/<int:id>')
def excluir_produto(id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM Produtos WHERE id = %s", (id,))
    conn.commit()
    return redirect(url_for('crud_produtos'))

# ------------------------ USUÁRIOS ------------------------
@app.route('/admin/usuarios')
@admin_required
def crud_usuarios():
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Usuarios")
    usuarios = cursor.fetchall()
    return render_template('crud_usuarios.html', usuarios=usuarios)

@app.route('/admin/usuarios/salvar', methods=['POST'])
def salvar_usuario():
    cursor = conn.cursor(dictionary=True)
    id = request.form.get('id')
    usuario = request.form['usuario']
    senha = request.form['senha']

    if not usuario:
        return redirect(url_for('crud_usuarios', msg='erro'))

    if id:
        if senha.strip():
            senha_hash = generate_password_hash(senha)
            cursor.execute("UPDATE Usuarios SET usuario=%s, senha=%s WHERE id=%s", (usuario, senha_hash, id))
        else:
            cursor.execute("UPDATE Usuarios SET usuario=%s WHERE id=%s", (usuario, id))
    else:
        if not senha.strip():
            return redirect(url_for('crud_usuarios', msg='erro'))

        cursor.execute("SELECT * FROM Usuarios WHERE usuario = %s", (usuario,))
        if cursor.fetchone():
            return redirect(url_for('crud_usuarios', msg='existe'))

        senha_hash = generate_password_hash(senha)
        cursor.execute("INSERT INTO Usuarios (usuario, senha) VALUES (%s, %s)", (usuario, senha_hash))

    conn.commit()
    return redirect(url_for('crud_usuarios'))

@app.route('/admin/usuarios/excluir/<int:id>')
def excluir_usuario(id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM Usuarios WHERE id = %s", (id,))
    conn.commit()
    return redirect(url_for('crud_usuarios'))

# ----------------------------------------------------------
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)