from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import datetime
import re
import gspread
from google.oauth2.service_account import Credentials
import os

feirinha_bp = Blueprint('feirinha', __name__)

# --- Configuração do Google Sheets ---
SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Verifica se todas as variáveis de ambiente necessárias estão definidas
required_env_vars = [
    'GCP_TYPE',
    'GCP_PROJECT_ID',
    'GCP_PRIVATE_KEY_ID',
    'GCP_PRIVATE_KEY',
    'GCP_CLIENT_EMAIL',
    'GCP_CLIENT_ID',
    'GCP_AUTH_URI',
    'GCP_TOKEN_URI',
    'GCP_AUTH_PROVIDER_CERT_URL',
    'GCP_CLIENT_CERT_URL'
]

missing_vars = [var for var in required_env_vars if var not in os.environ]
if missing_vars:
    raise RuntimeError(f"Variáveis de ambiente ausentes: {', '.join(missing_vars)}")

# Configuração das credenciais
credentials_dict = {
    "type": os.environ['GCP_TYPE'],
    "project_id": os.environ['GCP_PROJECT_ID'],
    "private_key_id": os.environ['GCP_PRIVATE_KEY_ID'],
    "private_key": os.environ['GCP_PRIVATE_KEY'].replace('\\n', '\n'),
    "client_email": os.environ['GCP_CLIENT_EMAIL'],
    "client_id": os.environ['GCP_CLIENT_ID'],
    "auth_uri": os.environ['GCP_AUTH_URI'],
    "token_uri": os.environ['GCP_TOKEN_URI'],
    "auth_provider_x509_cert_url": os.environ['GCP_AUTH_PROVIDER_CERT_URL'],
    "client_x509_cert_url": os.environ['GCP_CLIENT_CERT_URL']
}

CREDS = Credentials.from_service_account_info(credentials_dict, scopes=SCOPE)
CLIENT = gspread.authorize(CREDS)

# Configurações da planilha
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '1SBvTUfk0sQ3Fp_dXRa5GbCYccVbglKaww-R8BgiOk7M')
ABA_CADASTRO = 'Cadastro de Colaboradores'
ABA_REGISTROS = 'Respostas ao formulário 1'

# Conecta às abas da planilha
try:
    planilha = CLIENT.open_by_key(SPREADSHEET_ID)
    WORKERS_SHEET = planilha.worksheet(ABA_CADASTRO)
    REGISTRATIONS_SHEET = planilha.worksheet(ABA_REGISTROS)
except Exception as e:
    print(f"Erro ao conectar ao Google Sheets: {e}")
    exit()

SECTORS_FUNCTIONS = {
    'Bar': ['Ajudante de Bar', 'Bartender', 'Chefe de Bar'],
    'Cozinha': ['Auxiliar de Cozinha', 'Cozinheiro', 'Chefe de Cozinha'],
    'Salão': ['Cumim', 'Garçom', 'Limpeza', 'Recepcionista', 'Chefe de Salão']
}

def clean_cpf(cpf):
    """Remove formatação do CPF e padroniza para 11 dígitos"""
    if cpf is None:
        return ''
    cpf_clean = re.sub(r'\D', '', str(cpf))
    return cpf_clean.zfill(11)  # Garante 11 dígitos

def get_work_date(date_time):
    """Calcula a data de trabalho baseada na lógica do Apps Script"""
    hour = date_time.hour
    work_date = date_time.date()
    
    # Período noturno (22h-4h) pertence ao dia anterior
    if hour < 4:
        work_date = work_date - datetime.timedelta(days=1)
    elif hour < 10:
        # Período matutino (4h-10h) - verifica se é continuação da noite anterior
        night_start = datetime.datetime.combine(work_date - datetime.timedelta(days=1), datetime.time(22, 0))
        if date_time >= night_start:
            work_date = work_date - datetime.timedelta(days=1)
    
    return work_date

def get_day_of_week(date):
    """Retorna o dia da semana em português"""
    days = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
    return days[date.weekday()]

def calculate_payment(day_of_week, function_name):
    """Calcula o pagamento baseado na função e dia da semana"""
    is_weekend = day_of_week in ['sábado', 'domingo']
    
    if 'Chefe' in function_name:
        return 250 if is_weekend else 190
    
    if function_name in ['Bartender', 'Cozinheiro', 'Recepcionista', 'Garçom']:
        return 190 if is_weekend else 170
    
    if function_name in ['Ajudante de Bar', 'Auxiliar de Cozinha', 'Cumim', 'Limpeza']:
        return 170 if is_weekend else 150
    
    return 0

def get_all_workers():
    """Carrega colaboradores da aba 'Cadastro de Colaboradores'"""
    try:
        # Lê todas as linhas da planilha
        dados = WORKERS_SHEET.get_all_values()
        if len(dados) < 2:  # Se não tiver dados além do cabeçalho
            return {}
        
        workers = {}
        for row in dados[1:]:  # Ignora o cabeçalho
            try:
                cpf = clean_cpf(row[1]) if len(row) > 1 else ''  # Coluna B (índice 1)
                if cpf and len(cpf) == 11:
                    workers[cpf] = {
                        'name': row[0] if len(row) > 0 else '',  # Coluna A (índice 0)
                        'pixKey': row[2] if len(row) > 2 else ''  # Coluna C (índice 2)
                    }
            except Exception as e:
                print(f"Erro ao processar linha de colaborador: {row} - {e}")
                continue
                
        return workers
    except Exception as e:
        print(f"Erro ao ler colaboradores: {e}")
        return {}

def get_all_registrations():
    """Carrega registros da aba 'Respostas ao formulário 1'"""
    try:
        dados = REGISTRATIONS_SHEET.get_all_values()
        if len(dados) < 2:
            return []
        
        registrations = []
        for row in dados[1:]:  # Ignora o cabeçalho
            try:
                if len(row) > 10:  # Verifica se tem pelo menos coluna K (índice 10)
                    timestamp_str = row[0]  # Coluna A (Timestamp)
                    try:
                        timestamp = datetime.datetime.strptime(timestamp_str, '%d/%m/%Y %H:%M:%S')
                    except ValueError:
                        timestamp = datetime.datetime.now()
                    
                    registrations.append({
                        'timestamp': timestamp,
                        'cpf': clean_cpf(row[10]),  # Coluna K (índice 10)
                        'work_date': get_work_date(timestamp)
                    })
            except Exception as e:
                print(f"Erro ao processar linha de registro: {row} - {e}")
                continue
                
        return registrations
    except Exception as e:
        print(f"Erro ao ler registros: {e}")
        return []

# Carrega dados iniciais
WORKERS_DATA = get_all_workers()
REGISTRATIONS = get_all_registrations()

@feirinha_bp.route('/worker/<cpf>', methods=['GET'])
@cross_origin()
def get_worker_info(cpf):
    clean_cpf_value = clean_cpf(cpf)
    
    if clean_cpf_value in WORKERS_DATA:
        worker = WORKERS_DATA[clean_cpf_value]
        return jsonify({
            'found': True,
            'name': worker['name'],
            'pixKey': worker['pixKey']
        })
    
    return jsonify({'found': False})

@feirinha_bp.route('/check-registration/<cpf>', methods=['GET'])
@cross_origin()
def check_existing_registration(cpf):
    clean_cpf_value = clean_cpf(cpf)
    now = datetime.datetime.now()
    work_date = get_work_date(now)
    
    for registration in REGISTRATIONS:
        if (registration['cpf'] == clean_cpf_value and 
            registration['work_date'] == work_date):
            return jsonify({
                'exists': True,
                'date': work_date.strftime('%d/%m/%Y')
            })
    
    return jsonify({
        'exists': False,
        'date': work_date.strftime('%d/%m/%Y')
    })

@feirinha_bp.route('/functions/<sector>', methods=['GET'])
@cross_origin()
def get_functions_by_sector(sector):
    functions = SECTORS_FUNCTIONS.get(sector, [])
    return jsonify(functions)

@feirinha_bp.route('/register', methods=['POST'])
@cross_origin()
def register_presence():
    global REGISTRATIONS
    
    data = request.get_json()
    
    cpf = clean_cpf(data.get('cpf', ''))
    name = data.get('name', '')
    pix_key = data.get('pixKey', '')
    sector = data.get('sector', '')
    function = data.get('function', '')
    
    if not all([cpf, name, sector, function]):
        return jsonify({'error': 'Dados incompletos'}), 400
    
    now = datetime.datetime.now()
    work_date = get_work_date(now)
    day_of_week = get_day_of_week(work_date)
    
    # Verifica se já existe registro
    for registration in REGISTRATIONS:
        if (registration['cpf'] == cpf and 
            registration['work_date'] == work_date):
            return jsonify({
                'error': f'Já existe um registro para este CPF no dia {work_date.strftime("%d/%m/%Y")}'
            }), 400
    
    # Calcula o pagamento
    payment = calculate_payment(day_of_week, function)
    
    try:
        # Prepara a nova linha conforme estrutura da planilha
        new_row = [
            now.strftime('%d/%m/%Y %H:%M:%S'),  # Coluna A: Timestamp
            name,                                # Coluna B: Nome
            work_date.strftime('%d/%m/%Y'),      # Coluna C: Data
            day_of_week.capitalize(),            # Coluna D: Dia da semana
            sector,                             # Coluna E: Setor
            '', '', '',                         # Colunas F-H: Vazias (reservadas)
            function,                           # Coluna I: Função
            payment,                            # Coluna J: Pagamento
            cpf,                                # Coluna K: CPF
            pix_key                             # Coluna L: Chave PIX
        ]
        
        # Adiciona à planilha
        REGISTRATIONS_SHEET.append_row(new_row)
        
        # Atualiza os registros em memória
        REGISTRATIONS = get_all_registrations()
        
        return jsonify({
            'success': True,
            'payment': payment,
            'date': work_date.strftime('%d/%m/%Y'),
            'message': f'Registro realizado para {work_date.strftime("%d/%m/%Y")} | Valor: R$ {payment},00'
        })
    
    except Exception as e:
        return jsonify({'error': f'Erro ao salvar no Google Sheets: {str(e)}'}), 500

@feirinha_bp.route('/registrations', methods=['GET'])
@cross_origin()
def get_registrations():
    formatted_registrations = []
    for reg in REGISTRATIONS:
        formatted_registrations.append({
            'timestamp': reg['timestamp'].strftime('%d/%m/%Y %H:%M'),
            'cpf': reg['cpf'],
            'work_date': reg['work_date'].strftime('%d/%m/%Y')
        })
    
    return jsonify(formatted_registrations)