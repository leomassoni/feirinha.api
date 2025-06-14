import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert.jsx'
import { Loader2, CheckCircle, AlertCircle, User, MapPin, Briefcase } from 'lucide-react'
import './App.css'

const API_BASE_URL = 'http://localhost:5000/api/feirinha'

function App() {
  const [formData, setFormData] = useState({
    cpf: '',
    sector: '',
    function: ''
  })
  
  const [workerInfo, setWorkerInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})
  const [success, setSuccess] = useState('')
  const [blocked, setBlocked] = useState(null)
  const [availableFunctions, setAvailableFunctions] = useState([])

  const sectors = [
    { value: 'Bar', label: 'Bar' },
    { value: 'Cozinha', label: 'Cozinha' },
    { value: 'Salão', label: 'Salão' }
  ]

  // Máscara para CPF
  const formatCPF = (value) => {
    const numbers = value.replace(/\D/g, '')
    if (numbers.length <= 3) return numbers
    if (numbers.length <= 6) return numbers.replace(/(\d{3})(\d+)/, '$1.$2')
    if (numbers.length <= 9) return numbers.replace(/(\d{3})(\d{3})(\d+)/, '$1.$2.$3')
    return numbers.replace(/(\d{3})(\d{3})(\d{3})(\d+)/, '$1.$2.$3-$4').substring(0, 14)
  }

  const handleCPFChange = (e) => {
    const formatted = formatCPF(e.target.value)
    setFormData(prev => ({ ...prev, cpf: formatted }))
    
    const numbers = formatted.replace(/\D/g, '')
    if (numbers.length === 11) {
      checkWorker(numbers)
    } else {
      setWorkerInfo(null)
      setBlocked(null)
      setErrors(prev => ({ ...prev, cpf: '' }))
    }
  }

  const checkWorker = async (cpf) => {
    setLoading(true)
    setErrors(prev => ({ ...prev, cpf: '' }))
    
    try {
      // Primeiro verifica se já existe registro
      const existingResponse = await fetch(`${API_BASE_URL}/check-registration/${cpf}`)
      const existingData = await existingResponse.json()
      
      if (existingData.exists) {
        setBlocked({
          message: `${existingData.name} já registrado hoje (${existingData.date})`
        })
        setWorkerInfo(null)
      } else {
        // Se não existir, busca os dados do colaborador
        const workerResponse = await fetch(`${API_BASE_URL}/worker/${cpf}`)
        const workerData = await workerResponse.json()
        
        if (workerData.found) {
          setWorkerInfo(workerData)
          setBlocked(null)
        } else {
          setErrors(prev => ({ ...prev, cpf: 'CPF não encontrado. Verifique ou cadastre-se.' }))
          setBlocked({ message: 'CPF não cadastrado' })
          setWorkerInfo(null)
        }
      }
    } catch (error) {
      setErrors(prev => ({ ...prev, cpf: 'Erro ao buscar dados: ' + error.message }))
    } finally {
      setLoading(false)
    }
  }

  const handleSectorChange = async (value) => {
    setFormData(prev => ({ ...prev, sector: value, function: '' }))
    
    try {
      const response = await fetch(`${API_BASE_URL}/functions/${value}`)
      const functions = await response.json()
      setAvailableFunctions(functions)
    } catch (error) {
      console.error('Erro ao buscar funções:', error)
      setAvailableFunctions([])
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!formData.cpf || !formData.sector || !formData.function || !workerInfo) {
      return
    }

    setLoading(true)
    setErrors({})
    setSuccess('')

    try {
      const response = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cpf: formData.cpf,
          name: workerInfo.name,
          pixKey: workerInfo.pixKey,
          sector: formData.sector,
          function: formData.function
        })
      })

      const data = await response.json()

      if (response.ok) {
        setSuccess(`✅ ${data.message}`)
        
        // Reset form
        setFormData({ cpf: '', sector: '', function: '' })
        setWorkerInfo(null)
        setAvailableFunctions([])
      } else {
        setErrors({ submit: data.error || 'Erro no registro' })
      }
      
    } catch (error) {
      setErrors({ submit: 'Erro no registro: ' + error.message })
    } finally {
      setLoading(false)
    }
  }

  const isFormValid = formData.cpf && formData.sector && formData.function && workerInfo && !blocked

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4 sm:p-6 lg:p-8">
      <div className="max-w-md mx-auto">
        <Card className="shadow-xl border-0 bg-white/95 backdrop-blur">
          <CardHeader className="text-center space-y-2 pb-6">
            <CardTitle className="text-2xl sm:text-3xl font-bold text-gray-900">
              Cadastro de EXTRAS
            </CardTitle>
            <CardDescription className="text-lg text-gray-600">
              Feirinha 2025
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* CPF Input */}
            <div className="space-y-2">
              <Label htmlFor="cpf" className="text-base font-medium flex items-center gap-2">
                <User className="w-4 h-4" />
                CPF <span className="text-red-500">*</span>
              </Label>
              <Input
                id="cpf"
                type="text"
                placeholder="Digite seu CPF"
                value={formData.cpf}
                onChange={handleCPFChange}
                className="h-12 text-lg"
                maxLength={14}
              />
              {errors.cpf && (
                <Alert variant="destructive" className="py-2">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-sm">{errors.cpf}</AlertDescription>
                </Alert>
              )}
            </div>

            {/* Loading Indicator */}
            {loading && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                <span className="ml-2 text-gray-600">Processando...</span>
              </div>
            )}

            {/* Worker Info */}
            {workerInfo && (
              <Alert className="bg-blue-50 border-blue-200">
                <CheckCircle className="h-4 w-4 text-blue-600" />
                <AlertDescription>
                  <div className="space-y-1">
                    <div><strong>Nome:</strong> {workerInfo.name}</div>
                    <div><strong>Chave PIX:</strong> {workerInfo.pixKey}</div>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* Blocked Message */}
            {blocked && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>⚠️ ATENÇÃO:</strong> {blocked.message}
                </AlertDescription>
              </Alert>
            )}

            {/* Sector Select */}
            <div className="space-y-2">
              <Label className="text-base font-medium flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                Setor <span className="text-red-500">*</span>
              </Label>
              <Select 
                value={formData.sector} 
                onValueChange={handleSectorChange}
                disabled={!workerInfo || blocked}
              >
                <SelectTrigger className="h-12 text-lg">
                  <SelectValue placeholder="Selecione um setor" />
                </SelectTrigger>
                <SelectContent>
                  {sectors.map(sector => (
                    <SelectItem key={sector.value} value={sector.value}>
                      {sector.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Function Select */}
            <div className="space-y-2">
              <Label className="text-base font-medium flex items-center gap-2">
                <Briefcase className="w-4 h-4" />
                Função <span className="text-red-500">*</span>
              </Label>
              <Select 
                value={formData.function} 
                onValueChange={(value) => setFormData(prev => ({ ...prev, function: value }))}
                disabled={!formData.sector || !workerInfo || blocked}
              >
                <SelectTrigger className="h-12 text-lg">
                  <SelectValue placeholder={formData.sector ? "Selecione uma função" : "Selecione o setor primeiro"} />
                </SelectTrigger>
                <SelectContent>
                  {availableFunctions.map(func => (
                    <SelectItem key={func} value={func}>
                      {func}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Submit Button */}
            <Button 
              onClick={handleSubmit}
              disabled={!isFormValid || loading}
              className="w-full h-12 text-lg font-medium"
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

            {/* Success Message */}
            {success && (
              <Alert className="bg-green-50 border-green-200">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-800">
                  {success}
                </AlertDescription>
              </Alert>
            )}

            {/* Error Message */}
            {errors.submit && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{errors.submit}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default App

