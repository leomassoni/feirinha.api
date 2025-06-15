import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button.jsx';
import { Input } from '@/components/ui/input.jsx';
import { Label } from '@/components/ui/label.jsx';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx';
import { Alert, AlertDescription } from '@/components/ui/alert.jsx';
import { Loader2, CheckCircle, AlertCircle, User, MapPin, Briefcase } from 'lucide-react'; // KeyRound não está sendo usado, removi

const API_BASE_URL = 'http://localhost:5000/api/feirinha';

const functionsBySector = {
  Bar: ['Ajudante de Bar', 'Bartender', 'Chefe de Bar'],
  Cozinha: ['Auxiliar de Cozinha', 'Cozinheiro', 'Chefe de Cozinha'],
  Salão: ['Limpeza', 'Cumim', 'Garçom', 'Recepcionista', 'Chefe de Salão'],
};

function App() {
  const [formData, setFormData] = useState({
    cpf: '',
    sector: '',
    function: ''
  });

  // workerInfo armazena os dados do colaborador (nome, cpf, pixKey, registeredToday, lastRegistrationTime)
  const [workerInfo, setWorkerInfo] = useState(null); 
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [errors, setErrors] = useState({
    cpf: '',
    sector: '',
    function: '',
    submit: ''
  });
  const [isFormValid, setIsFormValid] = useState(false);

  // Efeito para revalidar o formulário quando formData ou loading mudam
  useEffect(() => {
    // O formulário é válido se:
    // 1. CPF tem 11 dígitos e é válido (não há erro de validação local)
    // 2. Setor e função estão selecionados
    // 3. Nenhuma operação está em loading
    // 4. O CPF não foi marcado como já registrado hoje (workerInfo?.registeredToday é false ou null)
    const isValid = formData.cpf.length === 11 &&
                    !errors.cpf && // Verifica que não há erro de validação de CPF local
                    formData.sector !== '' &&
                    formData.function !== '' &&
                    !loading && // Desabilita o botão enquanto carrega
                    !(workerInfo?.registeredToday); // Impede submissão se já registrado hoje
    setIsFormValid(isValid);
  }, [formData, loading, errors.cpf, workerInfo]);

  // Efeito para limpar mensagens de sucesso/erro após um tempo
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(''), 5000); // Limpa após 5 segundos
      return () => clearTimeout(timer);
    }
    if (errors.submit) {
      const timer = setTimeout(() => setErrors(prev => ({ ...prev, submit: '' })), 7000); // Limpa após 7 segundos
      return () => clearTimeout(timer);
    }
  }, [success, errors.submit]);


  // Função de validação de CPF (Luhn algorithm ou similar, seu código já faz isso)
  const validateCpf = (cpf) => {
    cpf = cpf.replace(/\D/g, ''); // Remove caracteres não numéricos
    if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) {
      return 'CPF inválido.';
    }
    let sum = 0;
    let remainder;
    for (let i = 1; i <= 9; i++) sum = sum + parseInt(cpf.substring(i - 1, i)) * (11 - i);
    remainder = (sum * 10) % 11;
    if ((remainder === 10) || (remainder === 11)) remainder = 0;
    if (remainder !== parseInt(cpf.substring(9, 10))) return 'CPF inválido.';
    sum = 0;
    for (let i = 1; i <= 10; i++) sum = sum + parseInt(cpf.substring(i - 1, i)) * (12 - i);
    remainder = (sum * 10) % 11;
    if ((remainder === 10) || (remainder === 11)) remainder = 0;
    if (remainder !== parseInt(cpf.substring(10, 11))) return 'CPF inválido.';
    return ''; // CPF válido
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setErrors(prev => ({ ...prev, [name]: '', submit: '' })); // Limpa erro ao digitar
    setSuccess(''); // Limpa mensagem de sucesso ao digitar

    if (name === 'cpf') {
      const formattedCpf = value.replace(/\D/g, '').substring(0, 11);
      setFormData(prev => ({ ...prev, cpf: formattedCpf }));
      // Valida o CPF apenas se tiver 11 dígitos
      if (formattedCpf.length === 11) {
        setErrors(prev => ({ ...prev, cpf: validateCpf(formattedCpf) }));
      } else {
        setErrors(prev => ({ ...prev, cpf: '' })); // Limpa erro se o CPF for incompleto
      }
      setWorkerInfo(null); // Limpa informações do trabalhador ao mudar o CPF
    }
  };

  const handleSelectChange = (name, value) => {
    setFormData(prev => ({ ...prev, [name]: value }));
    setErrors(prev => ({ ...prev, [name]: '', submit: '' })); // Limpa erro ao selecionar
    setSuccess(''); // Limpa mensagem de sucesso ao selecionar
    if (name === 'sector') {
      // Quando o setor muda, reseta a função
      setFormData(prev => ({ ...prev, function: '' }));
    }
  };

  const handleCheckCpf = async () => {
    // Só verifica o CPF se ele tiver 11 dígitos e não houver um erro de validação local
    if (formData.cpf.length !== 11 || errors.cpf) {
      return;
    }

    setLoading(true);
    setErrors(prev => ({ ...prev, submit: '' })); // Limpa erros de submit anteriores
    setSuccess(''); // Limpa sucessos anteriores
    setWorkerInfo(null); // Limpa info anterior ao verificar novamente

    try {
      const response = await fetch(`${API_BASE_URL}/check-registration`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ cpf: formData.cpf }),
      });

      const data = await response.json();

      if (response.ok) {
        if (data.exists) {
          setWorkerInfo({
            nome: data.nome,
            pixKey: data.pixKey || 'N/A',
            registeredToday: data.registeredToday,
            lastRegistrationTime: data.lastRegistrationTime // Hora do último registro do dia
          });
          if (data.registeredToday) {
            // Mensagem mais específica se já registrado hoje
            setErrors(prev => ({ ...prev, submit: `❌ ${data.message} Último registro: ${data.lastRegistrationTime}` }));
          } else {
            setSuccess(`✅ ${data.message} Bem-vindo(a) ${data.nome}!`);
          }
        } else {
          // CPF não encontrado na planilha
          setErrors(prev => ({ ...prev, submit: '❌ CPF não encontrado. Por favor, verifique ou contate a administração.' }));
          setWorkerInfo(null);
        }
      } else {
        // Erros do backend (ex: 400 Bad Request, 500 Internal Server Error)
        setErrors(prev => ({ ...prev, submit: `❌ Erro ao verificar CPF: ${data.error || 'Erro desconhecido.'}` }));
      }
    } catch (error) {
      console.error('Erro de rede ou API:', error);
      setErrors(prev => ({ ...prev, submit: '❌ Erro de conexão. Tente novamente mais tarde.' }));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    // A validação completa do formulário já é feita pelo isFormValid
    if (!isFormValid) {
      // Se não for válido, exibe uma mensagem genérica de erro no submit
      setErrors(prev => ({ ...prev, submit: 'Por favor, preencha todos os campos corretamente e verifique seu CPF.' }));
      return;
    }

    // Já verificamos via isFormValid e check-registration, mas mantemos uma camada aqui
    if (workerInfo?.registeredToday) {
      setErrors(prev => ({ ...prev, submit: `❌ Este CPF já foi registrado hoje às ${workerInfo.lastRegistrationTime}.` }));
      return;
    }

    setLoading(true);
    setErrors(prev => ({ ...prev, submit: '' }));
    setSuccess('');

    try {
      const response = await fetch(`${API_BASE_URL}/register-presence`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cpf: formData.cpf,
          sector: formData.sector,
          function: formData.function,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setSuccess(`✅ Presença registrada com sucesso! Bem-vindo(a) ${workerInfo?.nome || 'colaborador(a)'}!`);
        // Limpar formulário após sucesso
        setFormData({ cpf: '', sector: '', function: '' });
        setWorkerInfo(null); // Limpa as informações do trabalhador
        setErrors({ cpf: '', sector: '', function: '', submit: '' }); // Limpa quaisquer erros
      } else {
        // Erros do backend durante o registro (ex: CPF já registrado hoje)
        setErrors(prev => ({ ...prev, submit: `❌ Erro ao registrar presença: ${data.error || 'Erro desconhecido.'}` }));
      }
    } catch (error) {
      console.error('Erro de rede ou API:', error);
      setErrors(prev => ({ ...prev, submit: '❌ Erro de conexão. Tente novamente mais tarde.' }));
    } finally {
      setLoading(false);
    }
  };


  return (
    // Container principal: centraliza e adiciona background claro
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      {/* Card principal do formulário, com estilo Google Forms */}
      <Card className="w-full max-w-md mx-auto shadow-lg rounded-xl overflow-hidden border-t-8 border-t-blue-600">
        <CardHeader className="p-6 bg-white border-b border-gray-200">
          <CardTitle className="text-2xl font-bold text-gray-800 text-center">Registro de Presença</CardTitle>
          <CardDescription className="text-gray-600 text-center mt-2">
            Preencha seus dados para registrar sua presença diária.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-6 space-y-6">
          {/* Campo CPF */}
          <div className="space-y-2">
            <Label htmlFor="cpf" className="text-gray-700 font-medium flex items-center">
              <User className="w-4 h-4 mr-2 text-blue-600" /> CPF
            </Label>
            <div className="flex items-center space-x-2">
              <Input
                id="cpf"
                name="cpf"
                placeholder="Ex: 12345678900"
                value={formData.cpf}
                onChange={handleInputChange}
                onBlur={handleCheckCpf} // Verifica CPF ao perder o foco
                className={`focus:border-blue-500 focus:ring-blue-500 rounded-md ${errors.cpf || (workerInfo?.registeredToday && formData.cpf.length === 11) ? 'border-red-500' : ''}`}
                maxLength="11"
              />
              {/* Mostra o loader apenas se o CPF tiver 11 dígitos e estiver carregando */}
              {loading && formData.cpf.length === 11 && (
                <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
              )}
            </div>
            {errors.cpf && <p className="text-red-500 text-sm mt-1">{errors.cpf}</p>}
            {workerInfo && workerInfo.nome && !workerInfo.registeredToday && ( // Mostra info se encontrado e NÃO registrado hoje
              <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                <p className="font-semibold">Nome: {workerInfo.nome}</p>
                <p>Chave PIX: {workerInfo.pixKey}</p>
              </div>
            )}
          </div>

          {/* Campos Setor e Função */}
          <div className="space-y-6"> {/* Espaço extra para os campos abaixo do CPF */}
            <div className="space-y-2">
              <Label htmlFor="sector" className="text-gray-700 font-medium flex items-center">
                <MapPin className="w-4 h-4 mr-2 text-green-600" /> Setor
              </Label>
              <Select onValueChange={(value) => handleSelectChange('sector', value)} value={formData.sector}>
                <SelectTrigger className={`focus:ring-blue-500 rounded-md ${errors.sector ? 'border-red-500' : ''}`}>
                  <SelectValue placeholder="Selecione o setor" />
                </SelectTrigger>
                <SelectContent>
                  {Object.keys(functionsBySector).map((sector) => (
                    <SelectItem key={sector} value={sector}>
                      {sector}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.sector && <p className="text-red-500 text-sm mt-1">{errors.sector}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="function" className="text-gray-700 font-medium flex items-center">
                <Briefcase className="w-4 h-4 mr-2 text-purple-600" /> Função
              </Label>
              <Select onValueChange={(value) => handleSelectChange('function', value)} value={formData.function} disabled={!formData.sector}>
                <SelectTrigger className={`focus:ring-blue-500 rounded-md ${errors.function ? 'border-red-500' : ''}`}>
                  <SelectValue placeholder="Selecione a função" />
                </SelectTrigger>
                <SelectContent>
                  {formData.sector && functionsBySector[formData.sector].map((func) => (
                    <SelectItem key={func} value={func}>
                      {func}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.function && <p className="text-red-500 text-sm mt-1">{errors.function}</p>}
            </div>
          </div>

          {/* Botão de Registro */}
          <Button
            onClick={handleSubmit}
            // Desabilita se não for válido, estiver carregando ou se o CPF já foi registrado hoje
            disabled={!isFormValid || loading || workerInfo?.registeredToday} 
            className="w-full h-12 text-lg font-medium rounded-lg bg-blue-600 hover:bg-blue-700 text-white shadow-md transition-colors duration-200"
            size="lg"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Processando...
              </>
            ) : (
              'Registrar Presença'
            )}
          </Button>

          {/* Mensagem de Sucesso (aparece após um registro bem-sucedido) */}
          {success && (
            <Alert className="bg-green-50 border-green-300 text-green-800 flex items-center rounded-lg">
              <CheckCircle className="h-5 w-5 text-green-600 mr-3" />
              <AlertDescription className="flex-1">
                {success}
              </AlertDescription>
            </Alert>
          )}

          {/* Mensagem de Erro Geral (aparece se houver erros de submissão ou API) */}
          {errors.submit && (
            <Alert variant="destructive" className="border-red-300 text-red-800 flex items-center rounded-lg">
              <AlertCircle className="h-5 w-5 text-red-600 mr-3" />
              <AlertDescription className="flex-1">{errors.submit}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default App;

