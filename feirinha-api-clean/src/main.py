import os
import sys
from pathlib import Path
from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.feirinha import feirinha_bp
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# Configuração do path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Inicialização do app
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '../static'))

# Configurações básicas
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')  # Troque por uma chave segura em produção

# Configuração do banco de dados
basedir = Path(__file__).parent.parent  # Sobe para feirinha-api-clean/
database_path = basedir / "instance" / "database.db"

# Garante que o diretório existe
os.makedirs(basedir / "instance", exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', f'sqlite:///{database_path}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o banco de dados
db.init_app(app)
with app.app_context():
    db.create_all()

# Configuração do CORS
CORS(app)

# Registro dos Blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(feirinha_bp, url_prefix='/api/feirinha')

print("\n--- Mapa de URLs do Flask ---")
for rule in app.url_map.iter_rules():
    print(rule)
print("---------------------------\n")

# Rota para servir arquivos estáticos (React/Vue/etc)
#@app.route('/', defaults={'path': ''})
#@app.route('/<path:path>')
#def serve(path):
#    static_folder_path = app.static_folder
#    if static_folder_path is None:
#        return "Static_folder not configured", 404

#    full_path = os.path.join(static_folder_path, path)
#    if path != "" and os.path.exists(full_path):
#        return send_from_directory(static_folder_path, path)
#    else:
#        index_path = os.path.join(static_folder_path, 'index.html')
#        if os.path.exists(index_path):
#            return send_from_directory(static_folder_path, 'index.html')
#        return "index.html not found", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('DEBUG', 'False').lower() == 'true')