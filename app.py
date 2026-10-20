from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave_secreta_campus_start'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus_start.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# --- MODELOS DA BASE DE DADOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    faculdade = db.Column(db.String(150), nullable=False)
    curso = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    projetos = db.relationship('Project', backref='autor', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    problema = db.Column(db.Text, nullable=False)
    solucao = db.Column(db.Text, nullable=False)
    competencias = db.Column(db.String(300), nullable=False)
    etapa = db.Column(db.String(50), default='Ideia') # Ideia, Planeamento, Equipa Formada, Protótipo, Desenvolvimento, Concluído
    autor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comentarios = db.relationship('Comment', backref='projeto', lazy=True)
    pedidos = db.relationship('Colaboracao', backref='projeto', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    texto = db.Column(db.Text, nullable=False)
    autor_nome = db.Column(db.String(150), nullable=False)
    projeto_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

class Colaboracao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50), default='Pendente') # Pendente, Aceite, Recusado
    area_contribuicao = db.Column(db.String(150), nullable=False)
    usuario_nome = db.Column(db.String(150), nullable=False)
    projeto_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROTAS ---
@app.route('/')
def index():
    projetos = Project.query.all()
    return render_template('index.html', projetos=projetos)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        password = request.form.get('password')
        faculdade = request.form.get('faculdade')
        curso = request.form.get('curso')

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('E-mail já registado.', 'error')
            return redirect(url_for('register'))

        novo_user = User(nome=nome, email=email, password=generate_password_hash(password, method='pbkdf2:sha256'), faculdade=faculdade, curso=curso)
        db.session.add(novo_user)
        db.session.commit()
        flash('Conta criada com sucesso! Faz login.', 'success')
        return redirect(url_for('login'))
    
    # Cursos do Piloto (conforme combinado)
    faculdades_cursos = {
        "Faculdade de Engenharias e Tecnologias": ["Ciências da Computação", "Informática", "Educação Visual"],
        "Faculdade de Economia e Administração": ["Marketing de Produção e Inovação", "Administração Pública", "Gestão de Recursos Humanos", "Economia"],
        "Faculdade de Letras e Humanidades": ["Português", "Inglês Aplicado ao Turismo", "Secretariado Executivo"],
        "Faculdade de Educação e Psicologia": ["Psicologia", "Ensino Básico", "Ciências de Educação"],
        "Faculdade de Ciências Naturais e Exactas": ["Estatística"],
        "Faculdade de Ciências da Terra": ["Geografia", "Gestão de Riscos"],
        "Escola Superior de Ciências Agrárias": ["Produção Agrícola"]
    }
    return render_template('register.html', faculdades_cursos=faculdades_cursos)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Credenciais inválidas. Tenta novamente.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/criar_projeto', methods=['GET', 'POST'])
@login_required
def criar_projeto():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        problema = request.form.get('problema')
        solucao = request.form.get('solucao')
        competencias_list = request.form.getlist('competencias')
        competencias = ", ".join(competencias_list)
        
        novo_projeto = Project(titulo=titulo, problema=problema, solucao=solucao, competencias=competencias, autor_id=current_user.id)
        db.session.add(novo_projeto)
        db.session.commit()
        flash('Projeto submetido com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('criar_projeto.html')

@app.route('/projeto/<int:id>', methods=['GET', 'POST'])
def projeto(id):
    projeto = Project.query.get_or_404(id)
    
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Precisas de fazer login para interagir.', 'error')
            return redirect(url_for('login'))
            
        acao = request.form.get('acao')
        
        if acao == 'comentar':
            texto = request.form.get('comentario')
            novo_comentario = Comment(texto=texto, autor_nome=current_user.nome, projeto_id=projeto.id)
            db.session.add(novo_comentario)
            db.session.commit()
            flash('Comentário adicionado!', 'success')
            
        elif acao == 'colaborar':
            area = request.form.get('area')
            novo_pedido = Colaboracao(area_contribuicao=area, usuario_nome=current_user.nome, projeto_id=projeto.id)
            db.session.add(novo_pedido)
            db.session.commit()
            flash('Pedido de colaboração enviado ao autor!', 'success')
            
        elif acao == 'aceitar' and current_user.id == projeto.autor_id:
            pedido_id = request.form.get('pedido_id')
            pedido = Colaboracao.query.get(pedido_id)
            pedido.status = 'Aceite'
            if projeto.etapa in ['Ideia', 'Planeamento']:
                projeto.etapa = 'Equipa Formada'
            db.session.commit()
            flash('Colaborador aceite!', 'success')
            
        elif acao == 'avancar_etapa' and current_user.id == projeto.autor_id:
            etapas = ['Ideia', 'Planeamento', 'Equipa Formada', 'Protótipo', 'Desenvolvimento', 'Concluído']
            index_atual = etapas.index(projeto.etapa)
            if index_atual < len(etapas) - 1:
                projeto.etapa = etapas[index_atual + 1]
                db.session.commit()
            return redirect(url_for('projeto', id=projeto.id))
            
    return render_template('projeto.html', projeto=projeto)


@app.route('/apagar_projeto/<int:id>', methods=['POST'])
@login_required
def apagar_projeto(id):
    projeto = Project.query.get_or_404(id)
    
    # Verifica se é o autor OU se é administrador
    if projeto.autor_id != current_user.id and not current_user.is_admin:
        flash('Não tens permissão para apagar este projeto.', 'error')
        return redirect(url_for('projeto', id=projeto.id))
    
    # Apagar comentários e pedidos de colaboração associados
    Comment.query.filter_by(projeto_id=projeto.id).delete()
    Colaboracao.query.filter_by(projeto_id=projeto.id).delete()
    
    # Apagar o projeto
    db.session.delete(projeto)
    db.session.commit()
    
    flash('Projeto apagado com sucesso!', 'success')
    return redirect(url_for('index'))
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Cria o administrador automaticamente se ele não existir
        if not User.query.filter_by(email='jm848923848@gmail.com').first():
            admin = User(nome='Admin', email='jm848923848@gmail.com', password=generate_password_hash('admin123', method='pbkdf2:sha256'), faculdade='Admin', curso='Admin', is_admin=True)
            db.session.add(admin)
            db.session.commit()
            print("Conta Admin criada automaticamente!")
            
    app.run(debug=True)