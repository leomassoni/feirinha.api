# feirinha.py - Versão Final com Fuso Horário e Formato de Data Ajustado

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import datetime
import re
import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
from pathlib import Path
import traceback
import pytz # Adicionado para manipulação de fuso horário

# Carrega variáveis de ambiente do arquivo .env
# Assumimos que o .env está um nível acima da pasta feirinha-api-clean/src/routes
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

feirinha_bp = Blueprint('feirinha', __name__)

# --- Configuração do Google Sheets ---
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Lista de variáveis de ambiente obrigatórias para as credenciais do GCP
required_env_vars = [
    "GCP_TYPE",
    "GCP_PROJECT_ID",
    "GCP_PRIVATE_KEY_ID",
    "GCP_PRIVATE_KEY",
    "GCP_CLIENT_EMAIL",
    "GCP_CLIENT_ID",
    "GCP_AUTH_URI",
    "GCP_TOKEN_URI",
    "GCP_AUTH_PROVIDER_CERT_URL",
    "GCP_CLIENT_CERT_URL"
]

# Verifica se todas as variáveis de ambiente necessárias estão presentes
missing_vars = [var for var in required_env_vars if os.getenv(var) is None]
if missing_vars:
    print(f"❌ ERRO CRÍTICO: Variáveis de ambiente do GCP faltando: {', '.join(missing_vars)}")
    # Em produção, você pode querer levantar uma exceção para evitar que a API inicie
    # raise RuntimeError(f"Variáveis de ambiente do GCP faltando: {', '.join(missing_vars)}")

# Constrói as credenciais do GCP a partir das variáveis de ambiente
gcp_credentials_info = {
    "type": os.getenv("GCP_TYPE"),
    "project_id": os.getenv("GCP_PROJECT_ID"),
    "private_key_id": os.getenv("GCP_PRIVATE_KEY_ID"),
    # A chave privada precisa de quebras de linha reais se for uma string única no .env
    "private_key": os.getenv("GCP_PRIVATE_KEY").replace('\\n', '\n') if os.getenv("GCP_PRIVATE_KEY") else None,
    "client_email": os.getenv("GCP_CLIENT_EMAIL"),
    "client_id": os.getenv("GCP_CLIENT_ID"),
    "auth_uri": os.getenv("GCP_AUTH_URI"),
    "token_uri": os.getenv("GCP_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("GCP_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("GCP_CLIENT_CERT_URL")
}

try:
    # Autentica e autoriza o gspread
    credentials = Credentials.from_service_account_info(gcp_credentials_info, scopes=SCOPE)
    gc = gspread.authorize(credentials)
    print("✅ Autenticação com Google Sheets bem-sucedida.")
except Exception as e:
    print(f"❌ ERRO: Falha na autenticação com Google Sheets: {e}")
    traceback.print_exc()
    gc = None # Garante que gc seja None se a autenticação falhar

# ID da sua planilha Google Sheets (obtido da URL da planilha)
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')

# Verifica se o GOOGLE_SHEET_ID foi carregado
if GOOGLE_SHEET_ID is None:
    print("❌ ERRO: GOOGLE_SHEET_ID não foi carregado das variáveis de ambiente!")

# Nomes das abas da sua planilha
COLLABORATORS_SHEET_NAME = "Cadastro de Colaboradores"
REGISTRATIONS_SHEET_NAME = "Respostas ao formulário 1"

# Fuso horário de São Paulo
SAO_PAULO_TZ = pytz.timezone('America/Sao_Paulo')

# --- Funções Auxiliares ---
def get_worksheet(sheet_id, worksheet_name):
    """
    Retorna uma worksheet específica de uma planilha.
    Lida com a autenticação e reautenticação se necessário.
    """
    if gc is None:
        print(f"❌ ERRO: gspread não está autenticado. Não é possível obter a planilha '{worksheet_name}'.")
        return None
    
    try:
        spreadsheet = gc.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        print(f"✅ Planilha '{worksheet_name}' carregada com sucesso.")
        return worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ ERRO: Planilha com ID '{sheet_id}' não encontrada.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        print(f"❌ ERRO: Aba '{worksheet_name}' não encontrada na planilha ID '{sheet_id}'.")
        return None
    except Exception as e:
        print(f"❌ Erro ao acessar planilha/aba '{worksheet_name}': {e}")
        traceback.print_exc()
        return None

def get_registration_day(dt_object_local_tz):
    """
    Determina o 'dia de registro' para um dado objeto datetime LOCALIZADO no fuso horário de São Paulo.
    Um dia de registro começa às 10:00 AM (do dia D) e termina às 04:00 AM (do dia D+1).
    Retorna um objeto date representando o dia do calendário de início do período de registro.
    """
    # dt_object_local_tz já está no fuso horário de São Paulo

    # Se a hora for 10 AM (10:00) ou mais tarde, pertence ao dia de calendário atual
    if dt_object_local_tz.hour >= 10:
        return dt_object_local_tz.date()
    # Se a hora for antes das 04 AM (04:00), pertence ao dia de calendário anterior
    elif dt_object_local_tz.hour < 4:
        return (dt_object_local_tz - datetime.timedelta(days=1)).date()
    else:
        # Entre 04:00 e 10:00, está fora do período ativo de registro.
        # Retorna None para indicar que não há um "dia de registro" válido.
        return None

def calculate_payment(function, day_of_week):
    """
    Calcula o valor da paga com base na função e no dia da semana.
    """
    function_lower = function.lower()
    day_of_week_lower = day_of_week.lower()

    # Funções de Grupo 1 (Base 150/170)
    grupo1_functions = ['ajudante de bar', 'limpeza', 'cumim', 'auxiliar de cozinha']
    # Funções de Grupo 2 (Base 170/190)
    grupo2_functions = ['bartender', 'recepcionista', 'garçom', 'cozinheiro']
    # Funções de Grupo 3 (Base 190/220)
    grupo3_functions = ['chefe de bar', 'chefe de cozinha', 'chefe de salão']

    # Dias de semana
    dias_semana_normal = ['quarta', 'quinta', 'sexta']
    dias_semana_extra = ['sabado', 'domingo']

    paga = 0

    if function_lower in grupo1_functions:
        if day_of_week_lower in dias_semana_normal:
            paga = 150
        elif day_of_week_lower in dias_semana_extra:
            paga = 170
    elif function_lower in grupo2_functions:
        if day_of_week_lower in dias_semana_normal:
            paga = 170
        elif day_of_week_lower in dias_semana_extra:
            paga = 190
    elif function_lower in grupo3_functions:
        if day_of_week_lower in dias_semana_normal:
            paga = 190
        elif day_of_week_lower in dias_semana_extra:
            paga = 220
    
    return paga


# --- Rotas da API ---

@feirinha_bp.route('/check-registration', methods=['POST'])
@cross_origin()
def check_registration():
    if GOOGLE_SHEET_ID is None:
        return jsonify({"error": "Configuração da planilha principal ausente no servidor. Contate o administrador."}), 500
    
    data = request.json
    cpf = data.get('cpf')

    if not cpf:
        return jsonify({"error": "CPF é obrigatório."}), 400

    # Limpa e formata o CPF (remove pontos e traços)
    cpf_limpo = re.sub(r'[^0-9]', '', cpf)

    try:
        # 1. Verifica CPF na aba "Cadastro de Colaboradores"
        collaborators_worksheet = get_worksheet(GOOGLE_SHEET_ID, COLLABORATORS_SHEET_NAME)
        if collaborators_worksheet is None:
            return jsonify({"error": "Não foi possível acessar a aba de Cadastro de Colaboradores."}), 500

        try:
            # Obtém todos os valores da planilha (lista de listas)
            all_collaborator_values = collaborators_worksheet.get_all_values()
            if not all_collaborator_values:
                return jsonify({"exists": False, "message": "Nenhum dado encontrado no cadastro de colaboradores."}), 404
            
            # Pula o cabeçalho (primeira linha)
            collaborator_data_rows = all_collaborator_values[1:] if len(all_collaborator_values) > 1 else []
        except Exception as e:
            print(f"❌ Erro ao obter valores da aba de colaboradores: {e}")
            traceback.print_exc()
            return jsonify({"error": "Erro ao ler dados de colaboradores da planilha."}), 500

        worker_name = "N/A"
        worker_pix_key = "N/A"
        worker_found = False

        # Busca o CPF na Coluna B (índice 1)
        for row in collaborator_data_rows:
            # Garante que a linha tem pelo menos 3 colunas (A, B, C)
            if len(row) > 2 and re.sub(r'[^0-9]', '', row[1]) == cpf_limpo: # Coluna B é o CPF (índice 1)
                worker_name = row[0] # Coluna A é o Nome Completo (índice 0)
                worker_pix_key = row[2] # Coluna C é a Chave PIX (índice 2)
                worker_found = True
                break

        if not worker_found:
            return jsonify({"exists": False, "message": "CPF não encontrado no cadastro de colaboradores."}), 404

        # 2. Se o CPF foi encontrado, verifica na aba "Respostas ao formulário 1"
        registrations_worksheet = get_worksheet(GOOGLE_SHEET_ID, REGISTRATIONS_SHEET_NAME)
        if registrations_worksheet is None:
            return jsonify({"error": "Não foi possível acessar a aba de Respostas ao formulário 1 para verificação."}), 500

        try:
            all_registrations_values = registrations_worksheet.get_all_values()
            if not all_registrations_values:
                # Se não há registros, o CPF definitivamente não registrou hoje
                return jsonify({
                    "exists": True,
                    "registeredToday": False,
                    "message": "CPF encontrado, mas não registrado hoje.",
                    "nome": worker_name,
                    "pixKey": worker_pix_key
                }), 200
                
            # Pula o cabeçalho (primeira linha)
            registration_data_rows = all_registrations_values[1:] if len(all_registrations_values) > 1 else []
        except Exception as e:
            print(f"❌ Erro ao obter valores da aba de presença: {e}")
            traceback.print_exc()
            return jsonify({"error": "Erro ao ler dados de registro da planilha."}), 500

        registered_today = False
        last_registration_time = None
        
        # Calcula o "dia de registro" atual no fuso horário de São Paulo
        current_datetime_utc = datetime.datetime.now(pytz.utc)
        current_datetime_local_tz = current_datetime_utc.astimezone(SAO_PAULO_TZ)

        current_registration_day = get_registration_day(current_datetime_local_tz)

        if current_registration_day is None:
            # Se a hora atual está fora do período de registro ativo (entre 04:00 e 10:00)
            return jsonify({
                "exists": True,
                "registeredToday": False, 
                "message": "Sistema de registro fechado no momento (fora do horário 10h-04h).",
                "nome": worker_name,
                "pixKey": worker_pix_key
            }), 200 # Retorna 200 para permitir que o frontend exiba a mensagem de fechado

        # Itera sobre os registros de presença
        for row in registration_data_rows:
            # Garante que a linha tem colunas suficientes para CPF (K/índice 10) e Timestamp (A/índice 0)
            if len(row) > 10: 
                reg_timestamp_str = row[0] # Coluna A (Carimbo de data/hora)
                reg_cpf_na_planilha = re.sub(r'[^0-9]', '', row[10]) # Coluna K (Escreva seu CPF)

                if reg_cpf_na_planilha == cpf_limpo and reg_timestamp_str:
                    try:
                        reg_dt_obj_naive = None
                        # Tenta parsear o timestamp em diferentes formatos comuns do Google Sheets
                        if ' ' in reg_timestamp_str and '/' in reg_timestamp_str: # dd/mm/yyyy hh:mm:ss
                            reg_dt_obj_naive = datetime.datetime.strptime(reg_timestamp_str, '%d/%m/%Y %H:%M:%S')
                        elif '-' in reg_timestamp_str and 'T' in reg_timestamp_str: # ISO format (yyyy-mm-ddThh:mm:ss)
                             reg_dt_obj_naive = datetime.datetime.fromisoformat(reg_timestamp_str)
                        else: # Tenta com o formato americano mais comum (mm/dd/yyyy hh:mm:ss) se os anteriores falharem
                            reg_dt_obj_naive = datetime.datetime.strptime(reg_timestamp_str, '%m/%d/%Y %H:%M:%S')

                        # Localiza o objeto datetime parseado para o fuso horário de São Paulo
                        reg_dt_obj_local_tz = SAO_PAULO_TZ.localize(reg_dt_obj_naive)

                    except ValueError:
                        print(f"AVISO: Não foi possível parsear o timestamp '{reg_timestamp_str}' para CPF '{reg_cpf_na_planilha}'.")
                        continue # Pula para o próximo registro

                    # Verifica se o registro pertence ao "dia de registro" atual
                    if get_registration_day(reg_dt_obj_local_tz) == current_registration_day:
                        registered_today = True
                        last_registration_time = reg_dt_obj_local_tz.strftime('%H:%M:%S')
                        break # Encontrou um registro para hoje, pode parar

        # Retorna a resposta ao frontend
        if registered_today:
            return jsonify({
                "exists": True,
                "registeredToday": True, # Indica que já registrou hoje
                "message": "CPF já registrado hoje! Você não pode registrar novamente no mesmo dia.",
                "nome": worker_name,
                "lastRegistrationTime": last_registration_time,
                "pixKey": worker_pix_key
            }), 200
        else:
            return jsonify({
                "exists": True,
                "registeredToday": False, # Indica que não registrou hoje
                "message": "CPF encontrado, você pode prosseguir com o registro.",
                "nome": worker_name,
                "pixKey": worker_pix_key
            }), 200

    except Exception as e:
        print(f"❌ Erro INESPERADO ao verificar registro na rota /check-registration: {e}")
        traceback.print_exc()
        return jsonify({"error": "Erro interno ao verificar registro."}), 500

@feirinha_bp.route('/register-presence', methods=['POST'])
@cross_origin()
def register_presence():
    if GOOGLE_SHEET_ID is None:
        return jsonify({"error": "Configuração da planilha principal ausente no servidor. Contate o administrador."}), 500

    data = request.json
    cpf = data.get('cpf')
    sector = data.get('sector')
    function = data.get('function')

    if not cpf or not sector or not function:
        return jsonify({"error": "CPF, setor e função são obrigatórios."}), 400

    cpf_limpo = re.sub(r'[^0-9]', '', cpf)

    try:
        # Primeiro, re-verifica se o colaborador existe e pega o nome e a chave PIX
        collaborators_worksheet = get_worksheet(GOOGLE_SHEET_ID, COLLABORATORS_SHEET_NAME)
        if collaborators_worksheet is None:
            return jsonify({"error": "Não foi possível acessar a aba de Cadastro de Colaboradores."}), 500

        try:
            all_collaborator_values = collaborators_worksheet.get_all_values()
            collaborator_data_rows = all_collaborator_values[1:] if len(all_collaborator_values) > 1 else []
        except Exception as e:
            print(f"❌ Erro ao obter valores da aba de colaboradores para registro: {e}")
            traceback.print_exc()
            return jsonify({"error": "Erro ao ler dados de colaboradores para registro."}), 500

        worker_name_from_sheet = "N/A"
        worker_pix_key_from_sheet = "N/A"
        worker_found = False

        for row in collaborator_data_rows:
            if len(row) > 2 and re.sub(r'[^0-9]', '', row[1]) == cpf_limpo: # Coluna B (índice 1)
                worker_name_from_sheet = row[0] # Coluna A (índice 0)
                worker_pix_key_from_sheet = row[2] # Coluna C (índice 2)
                worker_found = True
                break

        if not worker_found:
            return jsonify({"error": "CPF não encontrado no cadastro de colaboradores. Registro não permitido."}), 404

        # Agora, re-verifica se o CPF já foi registrado para o "dia de registro" atual na aba "Respostas ao formulário 1"
        registrations_worksheet = get_worksheet(GOOGLE_SHEET_ID, REGISTRATIONS_SHEET_NAME)
        if registrations_worksheet is None:
            return jsonify({"error": "Não foi possível acessar a aba de Respostas ao formulário 1 para registro."}), 500

        try:
            all_registrations_values = registrations_worksheet.get_all_values()
            registration_data_rows = all_registrations_values[1:] if len(all_registrations_values) > 1 else []
        except Exception as e:
            print(f"❌ Erro ao obter valores da aba de presença para verificação antes de registrar: {e}")
            traceback.print_exc()
            return jsonify({"error": "Erro ao ler registros existentes para verificação."}), 500
        
        already_registered_today = False
        
        # Obtém a hora atual no fuso horário de São Paulo
        current_datetime_utc = datetime.datetime.now(pytz.utc)
        current_datetime_local_tz = current_datetime_utc.astimezone(SAO_PAULO_TZ)

        # DEBUG: Print current time and calculated registration day
        print(f"DEBUG (Register): Hora atual da requisição (local SP): {current_datetime_local_tz.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")

        current_registration_day_for_check = get_registration_day(current_datetime_local_tz)

        print(f"DEBUG (Register): Dia de Registro Calculado: {current_registration_day_for_check.strftime('%Y-%m-%d') if current_registration_day_for_check else 'N/A (fora do horário)'}")

        if current_registration_day_for_check is None:
            return jsonify({"error": "Não é possível registrar presença agora. Sistema de registro fechado no momento (fora do horário 10h-04h)."}), 400
            
        for row in registration_data_rows:
            if len(row) > 10: # Pelo menos até a coluna K (índice 10)
                reg_timestamp_str = row[0] # Coluna A
                reg_cpf_na_planilha = re.sub(r'[^0-9]', '', row[10]) # Coluna K

                if reg_cpf_na_planilha == cpf_limpo and reg_timestamp_str:
                    try:
                        reg_dt_obj_naive = None
                        if ' ' in reg_timestamp_str and '/' in reg_timestamp_str:
                            reg_dt_obj_naive = datetime.datetime.strptime(reg_timestamp_str, '%d/%m/%Y %H:%M:%S')
                        elif '-' in reg_timestamp_str and 'T' in reg_timestamp_str:
                             reg_dt_obj_naive = datetime.datetime.fromisoformat(reg_timestamp_str)
                        else: # Tenta com o formato americano mais comum (mm/dd/yyyy hh:mm:ss) como fallback
                            reg_dt_obj_naive = datetime.datetime.strptime(reg_timestamp_str, '%m/%d/%Y %H:%M:%S')
                        
                        # Localiza o objeto datetime parseado para o fuso horário de São Paulo
                        reg_dt_obj_local_tz = SAO_PAULO_TZ.localize(reg_dt_obj_naive)

                    except ValueError:
                        print(f"AVISO: Não foi possível parsear o timestamp '{reg_timestamp_str}' para CPF '{reg_cpf_na_planilha}'.")
                        continue

                    if get_registration_day(reg_dt_obj_local_tz) == current_registration_day_for_check:
                        already_registered_today = True
                        break
        
        if already_registered_today:
            return jsonify({"error": "Este CPF já foi registrado para o dia atual. Um registro por dia é permitido."}), 409

        # --- Geração dos dados para as novas colunas ---
        # Timestamp para a Coluna A (formato DD/MM/YYYY HH:MM:SS)
        timestamp_to_write = current_datetime_local_tz.strftime('%d/%m/%Y %H:%M:%S')
        
        # 1. Coluna C: Dia do Registro (formato DD/MM/AAAA)
        dia_do_registro = current_registration_day_for_check.strftime('%d/%m/%Y')
        
        # 2. Coluna D: Dia da Semana (todo em minúscula) - Já estava correto
        dias_da_semana = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
        dia_da_semana = dias_da_semana[current_registration_day_for_check.weekday()].lower()
        
        # 3. Coluna J: Paga (enviado como int, não str) - Já estava correto
        paga_calculada = calculate_payment(function, dia_da_semana)

        # --- ESTRUTURA FINAL DA LINHA PARA REGISTRO NA ABA "Respostas ao formulário 1" ---
        new_row = [
            timestamp_to_write,             # Coluna A (Índice 0)
            worker_name_from_sheet,         # Coluna B (Índice 1)
            dia_do_registro,                # Coluna C (Índice 2) - Dia do Registro (formato DD/MM/AAAA)
            dia_da_semana,                  # Coluna D (Índice 3) - Dia da Semana (todo em minúscula)
            sector,                         # Coluna E (Índice 4)
            '',                             # Coluna F (Índice 5) - VAZIO
            '',                             # Coluna G (Índice 6) - VAZIO
            '',                             # Coluna H (Índice 7) - VAZIO
            function,                       # Coluna I (Índice 8)
            paga_calculada,                 # Coluna J (Índice 9) - Paga (enviado como int)
            cpf_limpo,                      # Coluna K (Índice 10)
            worker_pix_key_from_sheet,      # Coluna L (Índice 11)
            ''                              # Coluna M (Índice 12) - Observações (VAZIO)
        ]
        
        # Anexa a nova linha à planilha
        worksheet = get_worksheet(GOOGLE_SHEET_ID, REGISTRATIONS_SHEET_NAME)
        if worksheet is None:
            return jsonify({"error": "Não foi possível acessar a aba de Respostas ao formulário 1 para registrar."}), 500

        worksheet.append_row(new_row)

        return jsonify({"message": "Presença registrada com sucesso!", "nome": worker_name_from_sheet}), 201 # Created
    
    except gspread.exceptions.APIError as e:
        print(f"❌ Erro da API do Google Sheets ao registrar presença: {e}")
        error_message = e.response.text if hasattr(e, 'response') and e.response else str(e)
        return jsonify({"error": f"Erro na comunicação com a planilha: {error_message}"}), 500
    except Exception as e:
        print(f"❌ Erro INESPERADO ao registrar presença: {e}")
        traceback.print_exc()
        return jsonify({"error": "Erro interno ao registrar presença."}), 500