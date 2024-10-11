from flask import Flask, render_template, redirect, request, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import ClientFlag, Error
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from functools import wraps
from datetime import timedelta


app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'supersecretkey')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Define o tempo de permanencia de login
app.permanent_session_lifetime = timedelta(minutes=10)

#Configura a parte do diretório de upload de imagens
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#Configurações do formulário de envio de email
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'cscjuniorletalsite@gmail.com'
app.config['MAIL_PASSWORD'] = 'cpys lvuz gcrg htyy'

mail = Mail(app)

#Faz a segurança das rotas que exigem login, não deixando alguem entrar pela URL sem logar
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loginStatus' not in session or not session.get('loginStatus'):
            flash("Você precisa estar logado para acessar essa página.", "error")
            return redirect(url_for('/'))
        return f(*args, **kwargs)
    return decorated_function

#Conexão ao bando de dados
def iniciaConexao():
    try:
        conexaoBanco = mysql.connector.connect(
            host=os.environ.get('DB_HOST', '127.0.0.1'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', 'P@ssAlun0'),
            database=os.environ.get('DB_NAME', 'CSCJL'),
            client_flags=[ClientFlag.PLUGIN_AUTH]
        )
        return conexaoBanco
    except Error as err:
        print(f"Erro ao conectar ao banco de dados: {err}")
        return None

#Rota de eventos
@app.route('/eventos')
def eventos():
    eventos_publicos = read_eventos_publicos()
    return render_template('eventos.html', eventos=eventos_publicos)

#Rota principal/index
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/horarios')
def horarios():
    return render_template('horarios.html')

@app.route('/create_horarios', methods=['POST'])
@login_required
def create_horarios():
    tipo_consulta = request.form.get('tipo_consulta')
    data_hora = request.form.get('data_hora')
    disponivel = request.form.get('disponivel')

    if not tipo_consulta or not data_hora:
        flash("Todos os campos são obrigatórios", "error")
        return redirect(url_for('horarios'))

    conexao = iniciaConexao()
    if conexao:
        try:
            cursor = conexao.cursor()
            comando = "INSERT INTO horarios (tipo_consulta, data_hora, disponivel) VALUES (%s, %s, %s)"
            cursor.execute(comando, (tipo_consulta, data_hora, disponivel))
            conexao.commit()
            flash("Horário criado com sucesso!", "success")
            return redirect(url_for('horarios'))
        except Error as err:
            print(f"Erro ao criar horário: {err}")
            flash("Erro ao criar horário.", "error")
        finally:
            cursor.close()
            conexao.close()
    return redirect(url_for('horarios'))

@app.route('/agendar_consulta', methods=['POST'])
@login_required
def agendar_consulta():
    tipo_consulta = request.form.get('tipo-consulta')
    data_hora = request.form.get('data_hora')

    if not tipo_consulta or not data_hora:
        flash("Todos os campos são obrigatórios", "error")
        return redirect(url_for('agendar'))

    conexao = iniciaConexao()
    if conexao:
        try:
            cursor = conexao.cursor()
            # Verifique se o horário está disponível
            comando = "SELECT disponivel FROM horarios WHERE data_hora = %s"
            cursor.execute(comando, (data_hora,))
            resultado = cursor.fetchone()

            if resultado and resultado[0] == False:
                flash("Horário não disponível", "error")
                return redirect(url_for('agendar'))

            comando = "INSERT INTO consulta (paciente_login, tipo_consulta, data_hora) VALUES (%s, %s, %s)"
            cursor.execute(comando, (session['login'], tipo_consulta, data_hora))
            conexao.commit()

            # Atualize o status do horário no banco de dados
            comando = "UPDATE horarios SET disponivel = False WHERE data_hora = %s"
            cursor.execute(comando, (data_hora,))
            conexao.commit()

            flash("Consulta agendada com sucesso!", "success")
        except Error as err:
            print(f"Erro ao agendar consulta: {err}")
            flash("Erro ao agendar consulta.", "error")
        finally:
            cursor.close()
            conexao.close()
    return redirect(url_for('agendar'))

@app.route('/agendar')
@login_required
def agendar():
    nome_usuario = session.get('login', 'Usuário')  # Já está buscando o nome do usuário
    conexao = iniciaConexao()

    if conexao:
        try:
            cursor = conexao.cursor()
            # Busque a imagem do usuário a partir do banco de dados
            cursor.execute("SELECT foto FROM Paciente WHERE login = %s", (nome_usuario,))
            resultado = cursor.fetchone()
            
            # Verifique se o resultado existe e se a foto não é None ou vazia
            if resultado and resultado[0]:
                foto_usuario = resultado[0]
            else:
                foto_usuario = 'default.png'  # Caminho da imagem padrão se não tiver foto
            
            # Busque as consultas agendadas do usuário
            cursor.execute("SELECT * FROM consulta WHERE paciente_login = %s", (nome_usuario,))
            consultas_agendadas = cursor.fetchall()
            
            # Busque os tipos de consulta disponíveis
            cursor.execute("SELECT tipo_consulta FROM horarios WHERE disponivel = True")
            tipos_consulta = [row[0] for row in cursor.fetchall()]
            
            # Busque as datas/horas disponíveis para cada tipo de consulta
            datas_horas = {}
            for tipo in tipos_consulta:
                cursor.execute("SELECT data_hora FROM horarios WHERE tipo_consulta = %s AND disponivel = True", (tipo,))
                datas_horas[tipo] = [row[0] for row in cursor.fetchall()]
        
        except Error as err:
            print(f"Erro ao buscar imagem do usuário: {err}")
            foto_usuario = 'default.png'  # Em caso de erro, também use uma imagem padrão
            consultas_agendadas = []
            tipos_consulta = []
            datas_horas = {}
        
        finally:
            cursor.close()
            conexao.close()
    
    return render_template('agendar.html', nome_usuario=nome_usuario, foto_usuario=foto_usuario, consultas_agendadas=consultas_agendadas, tipos_consulta=tipos_consulta, datas_horas=datas_horas)

@app.route('/upload_photo', methods=['POST'])
@login_required
def upload_photo():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})

    if file and allowed_file(file.filename):  # Adicione uma função allowed_file para verificar a extensão
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Atualiza a foto do usuário no banco de dados
        conexao = iniciaConexao()
        if conexao:
            try:
                cursor = conexao.cursor()
                cursor.execute("UPDATE Paciente SET foto = %s WHERE login = %s", (filename, session['login']))
                conexao.commit()
            except Error as err:
                return jsonify({'success': False, 'message': f'Erro ao atualizar imagem no banco de dados: {err}'})
            finally:
                cursor.close()
                conexao.close()

        return jsonify({'success': True, 'new_image_url': url_for('static', filename='uploads/' + filename)})
    
    return jsonify({'success': False, 'message': 'Arquivo inválido'})

#Rota de login para agendamentos
@app.route('/logar', methods=['GET', 'POST'])
def logar():
    if request.method == 'POST':
        nome = request.form.get('nome')
        senha = request.form.get('senha')
        
        #Verificação de conexão ao bando de dados
        conexao = iniciaConexao()
        if conexao:
            try:
                cursor = conexao.cursor()
                cursor.execute("SELECT * FROM paciente WHERE login = %s AND senha = %s", (nome, senha))
                paciente = cursor.fetchone()

                if paciente:
                    session['loginStatus'] = True
                    session['login'] = nome  
                    session.permanent = True  
                    flash("Login realizado com sucesso!", "success")
                    return redirect(url_for('agendar'))  
                else:
                    flash("Login ou senha inválidos.", "error")
            except Error as err:
                print(f"Erro ao validar login: {err}")
                flash("Erro ao validar login.", "error")
            finally:
                cursor.close()
                conexao.close()
        else:
            flash("Erro ao conectar ao banco de dados.", "error")
    return render_template('login.html')

#Rota da pagina de cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        senha = request.form.get('senha')
        data_nascimento = request.form.get('data_nascimento')
        
        # Adicione aqui a lógica para inserir os dados no banco de dados
        conexao = iniciaConexao()
        if conexao:
            try:
                cursor = conexao.cursor()
                comando = "INSERT INTO Paciente (login, senha, data_nascimento) VALUES (%s, %s, %s)"
                cursor.execute(comando, (nome, senha, data_nascimento))
                conexao.commit()
                flash("Paciente cadastrado com sucesso!", "success")
                return redirect(url_for('logar'))  # Redirecionar após o cadastro
            except Error as err:
                print(f"Erro ao cadastrar paciente: {err}")
                flash("Erro ao cadastrar paciente.", "error")
            finally:
                cursor.close()
                conexao.close()
        else:
            flash("Erro ao conectar ao banco de dados.", "error")
    
    return render_template('cadastro.html')

#Rota de fale-conosco
@app.route('/fale_conosco')
def fale_conosco():
    return render_template('contate-nos.html')

#Rota de agendamentos
@app.route('/agendamentos')
def agendamentos():
    return render_template('agendamentos.html')

#Rota do instagram oficial
@app.route('/instagram')
def instagram():
    return redirect('https://www.instagram.com/cscjuniorletal')

#Rota do CRUD de eventos
@app.route('/eventosadm', methods=['GET', 'POST'])
@login_required
def eventosadm():
    if request.method == 'POST':
        if 'create' in request.form:
            if create_event():
                flash("Evento criado com sucesso!", "success")
            else:
                flash("Erro ao criar evento.", "error")
        elif 'update' in request.form:
            if update_event():
                flash("Evento atualizado com sucesso!", "success")
            else:
                flash("Erro ao atualizar evento.", "error")
        elif 'delete' in request.form:
            if delete_event():
                flash("Evento excluído com sucesso!", "success")
            else:
                flash("Erro ao excluir evento.", "error")

    eventos = read_eventos()
    return render_template('eventosadm.html', eventos=eventos)

#Rota referente a alteração de login e senha de adm
@app.route('/alterar', methods=['GET', 'POST'])
@login_required
def alterar():
    if request.method == 'POST':
        novo_login = request.form.get('novo_login')
        nova_senha = request.form.get('nova_senha')

        if novo_login and nova_senha:
            conexao = iniciaConexao()
            if conexao:
                try:
                    cursor = conexao.cursor()
                    comando = "UPDATE Administrador SET login = %s, senha = %s WHERE login = %s"
                    cursor.execute(comando, (novo_login, nova_senha, session.get('login')))
                    conexao.commit()
                    
                    session['login'] = novo_login
                    flash("Login e senha alterados com sucesso!", "success")
                    
                    session.pop('loginStatus', None)
                    session.pop('login', None)
                    flash("Por favor, faça login novamente com suas novas credenciais.", "info")
                    return redirect(url_for('login'))  
                except Error as err:
                    flash(f"Erro ao alterar login ou senha: {err}", "error")
                finally:
                    cursor.close()
                    conexao.close()
            else:
                flash("Erro ao conectar ao banco de dados.", "error")
        else:
            flash("Os campos de login e senha não podem ser vazios.", "error")
    
    return render_template('alterar.html')

#Rota de login de adm
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('nome')
        senha = request.form.get('senha')
        
        conexao = iniciaConexao()
        if conexao:
            try:
                cursor = conexao.cursor()
                cursor.execute("SELECT * FROM Administrador WHERE login = %s AND senha = %s", (login, senha))
                administrador = cursor.fetchone()

                if administrador:
                    session['loginStatus'] = True
                    session['login'] = login  
                    session.permanent = True  
                    flash("Login realizado com sucesso!", "success")
                    return redirect(url_for('eventosadm'))  
                else:
                    flash("Login ou senha inválidos.", "error")
            except Error as err:
                print(f"Erro ao validar login: {err}")
                flash("Erro ao validar login.", "error")
            finally:
                cursor.close()
                conexao.close()
        else:
            flash("Erro ao conectar ao banco de dados.", "error")
    
    return render_template('adm.html')

#Rota para confirmação de login e senha para alteração de login de adm
@app.route('/confirmar', methods=['GET', 'POST'])
def confirmar():
    if request.method == 'POST':
        nome = request.form.get('nome')
        senha = request.form.get('senha')
        
        #Verificação de conexão ao banco de dados
        conexao = iniciaConexao()
        if conexao:
            try:
                cursor = conexao.cursor()
                cursor.execute("SELECT * FROM Administrador WHERE login = %s AND senha = %s", (nome, senha))
                administrador = cursor.fetchone()

                if administrador:
                    session['loginStatus'] = True
                    session['login'] = nome  
                    session.permanent = True  
                    flash("Login realizado com sucesso!", "success")
                    return redirect(url_for('alterar'))  
                else:
                    flash("Login ou senha inválidos.", "error")
            except Error as err:
                print(f"Erro ao validar login: {err}")
                flash("Erro ao validar login.", "error")
            finally:
                cursor.close()
                conexao.close()
        else:
            flash("Erro ao conectar ao banco de dados.", "error")
    return render_template('confirmar.html')

#Criação de eventos
def create_event():
    nome = request.form.get('nome')
    descricao = request.form.get('descricao')
    dia = request.form.get('dia')
    imagem = request.files.get('imagem')

    if not nome or not descricao or not dia or not imagem:
        return False

    filename = secure_filename(imagem.filename)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    imagem.save(image_path)

    conexao = iniciaConexao()
    if conexao:
        try:
            cursor = conexao.cursor()
            comando = "INSERT INTO Evento (nome, descricao, dia, imagem) VALUES (%s, %s, %s, %s)"
            cursor.execute(comando, (nome, descricao, dia, image_path))
            conexao.commit()
            return True
        except Error as err:
            print(f"Erro ao criar evento: {err}")
            return False
        finally:
            cursor.close()
            conexao.close()
    return False

#Exclusão de eventos
def delete_event():
    id = request.form.get('id')
    
    if not id:
        return False

    conexao = iniciaConexao()
    if conexao:
        try:
            cursor = conexao.cursor()
            comando = "DELETE FROM Evento WHERE id = %s"
            cursor.execute(comando, (id,))
            conexao.commit()
            return True
        except Error as err:
            print(f"Erro ao excluir evento: {err}")
            return False
        finally:
            cursor.close()
            conexao.close()
    return False

#Atualização de eventos
def update_event():
    id = request.form.get('id')
    nome = request.form.get('nome')
    descricao = request.form.get('descricao')
    dia = request.form.get('dia')
    imagem = request.files.get('imagem')

    if not id or not nome or not descricao or not dia:
        return False

    conexao = iniciaConexao()
    if conexao:
        try:
            cursor = conexao.cursor()

            if imagem and imagem.filename != '':
                filename = secure_filename(imagem.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                imagem.save(image_path)

                comando = "UPDATE Evento SET nome=%s, descricao=%s, dia=%s, imagem=%s WHERE id=%s"
                cursor.execute(comando, (nome, descricao, dia, image_path, id))
            else:
                comando = "UPDATE Evento SET nome=%s, descricao=%s, dia=%s WHERE id=%s"
                cursor.execute(comando, (nome, descricao, dia, id))

            conexao.commit()
            return True
        except Error as err:
            print(f"Erro ao atualizar evento: {err}")
            return False
        finally:
            cursor.close()
            conexao.close()
    return False

#Visualização de eventos
def read_eventos_publicos():
    conexao = iniciaConexao()
    if conexao:
        try:
            cursor = conexao.cursor()
            cursor.execute("SELECT nome, descricao, dia, imagem FROM Evento ORDER BY dia ASC;")
            eventos_publicos = cursor.fetchall()
            return eventos_publicos
        except Error as err:
            print(f"Erro ao ler eventos: {err}")
            return []
        finally:
            cursor.close()
            conexao.close()
    return []

#Visualização de eventos
def read_eventos():
    conexao = iniciaConexao()
    if conexao:
        try:
            cursor = conexao.cursor()
            cursor.execute("SELECT * FROM Evento;")
            eventos = cursor.fetchall()
            return eventos
        except Error as err:
            print(f"Erro ao ler eventos: {err}")
            return []
        finally:
            cursor.close()
            conexao.close()
    return []

#fale-conosco
#Rota de envio de email
@app.route('/send_email', methods=['POST'])
def send_email():
    nome = request.form.get('nome')
    email = request.form.get('email')
    mensagem = request.form.get('mensagem')

    if not nome or not email or not mensagem:
        flash("Todos os campos são obrigatórios", "error")
        return redirect(url_for('fale_conosco'))

    try:
        msg = Message(subject=f"Contato de {nome}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[app.config['MAIL_USERNAME']],
                      body=f"Nome: {nome}\nE-mail: {email}\n\nMensagem:\n{mensagem}")
        mail.send(msg)
        flash("E-mail enviado com sucesso!", "success")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        flash("Erro ao enviar e-mail. Tente novamente mais tarde.", "error")

    return redirect(url_for('fale_conosco'))

if __name__ == '__main__':
    app.run(debug=True)