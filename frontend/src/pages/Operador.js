import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { Factory, Timer, LogOut, Play, CheckCircle2, AlertTriangle, Clock, Package, Weight } from 'lucide-react';
import { ThemeToggle } from '../components/ThemeToggle';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow, differenceInMinutes } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const Operador = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [digestors, setDigestors] = useState([]);
  const [entries, setEntries] = useState([]);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [selectedDigestor, setSelectedDigestor] = useState(null);
  const [showDescarregamentoDialog, setShowDescarregamentoDialog] = useState(false);
  const [showDescarregarDialog, setShowDescarregarDialog] = useState(false);
  const [toneladasEfetivas, setToneladasEfetivas] = useState('');
  const [observacao, setObservacao] = useState('');
  const [currentDescarregamento, setCurrentDescarregamento] = useState(null);
  const [currentTrituracao, setCurrentTrituracao] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    const timeInterval = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => {
      clearInterval(interval);
      clearInterval(timeInterval);
    };
  }, []);

  const fetchData = async () => {
    try {
      const [digestorsRes, entriesRes] = await Promise.all([
        axios.get(`${API}/digestors`),
        axios.get(`${API}/entries?status=aguardando_descarregamento`)
      ]);
      setDigestors(digestorsRes.data);
      setEntries(entriesRes.data);
    } catch (error) {
      console.error('Erro ao buscar dados:', error);
    }
  };

  const handleStartDescarregamento = async () => {
    try {
      const response = await axios.post(`${API}/descarregamento/start`, {
        entry_id: selectedEntry.id,
        toneladas_efetivas: parseFloat(toneladasEfetivas)
      });
      
      setCurrentDescarregamento(response.data);
      toast.success('Descarregamento iniciado!');
      setShowDescarregamentoDialog(false);
      setToneladasEfetivas('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao iniciar descarregamento');
    }
  };

  const handleFinishDescarregamento = async (descarregamentoId) => {
    try {
      const response = await axios.post(`${API}/descarregamento/${descarregamentoId}/finish`);
      toast.success('Descarregamento finalizado!');
      setCurrentDescarregamento(prev => ({
        ...prev,
        end_at: new Date().toISOString(),
        tempo_minutos: response.data.tempo_minutos
      }));
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao finalizar descarregamento');
    }
  };

  const handleStartTrituracao = async (digestorId) => {
    if (!currentDescarregamento) {
      toast.error('Nenhum descarregamento ativo');
      return;
    }
    
    try {
      const response = await axios.post(`${API}/trituracao/start`, {
        descarregamento_id: currentDescarregamento.id,
        digestor_id: digestorId,
        toneladas: currentDescarregamento.toneladas_efetivas
      });
      
      setCurrentTrituracao(response.data);
      toast.success(`Trituração iniciada no Digestor ${digestorId}`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao iniciar trituração');
    }
  };

  const handleFinishTrituracao = async (trituracaoId, digestorId) => {
    try {
      await axios.post(`${API}/trituracao/${trituracaoId}/finish`);
      toast.success('Trituração finalizada!');
      
      // Auto start cozimento
      const response = await axios.post(`${API}/cozimento/start`, {
        trituracao_id: trituracaoId,
        digestor_id: digestorId
      });
      
      toast.info('Cozimento iniciado automaticamente');
      setCurrentTrituracao(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao finalizar trituração');
    }
  };

  const handleFinishCozimento = async (digestor) => {
    try {
      const cozimentosRes = await axios.get(`${API}/cozimentos`);
      const activeCozimento = cozimentosRes.data.find(
        c => c.digestor_id === digestor.id && !c.end_at
      );
      
      if (!activeCozimento) {
        toast.error('Nenhum cozimento ativo encontrado');
        return;
      }
      
      await axios.post(`${API}/cozimento/${activeCozimento.id}/finish`);
      toast.success('Cozimento finalizado! Digestor pronto para descarregar.');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao finalizar cozimento');
    }
  };

  const handleDescarregarDigestor = async () => {
    try {
      const response = await axios.post(`${API}/digestor/descarregar`, {
        digestor_id: selectedDigestor.id,
        observacao: observacao || null
      });
      
      toast.success(`Digestor ${selectedDigestor.id} descarregado! Tempo parado: ${response.data.tempo_parado_minutos.toFixed(1)}min`);
      setShowDescarregarDialog(false);
      setSelectedDigestor(null);
      setObservacao('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao descarregar digestor');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'livre':
        return 'border-green-500 bg-green-500/10';
      case 'triturando':
        return 'border-yellow-500 bg-yellow-500/10';
      case 'cozinhando':
        return 'border-amber-500 bg-amber-500/10';
      case 'pronto':
        return 'border-blue-500 bg-blue-500/10 animate-pulse-glow-green';
      case 'alerta':
        return 'border-red-500 bg-red-500/10';
      case 'manutencao':
        return 'border-gray-500 bg-gray-500/10';
      default:
        return 'border-gray-500 bg-gray-500/10';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'livre':
        return <CheckCircle2 className="h-8 w-8 text-green-500" />;
      case 'triturando':
      case 'cozinhando':
        return <Timer className="h-8 w-8 text-yellow-500 animate-pulse" />;
      case 'pronto':
        return <Package className="h-8 w-8 text-blue-500 animate-pulse" />;
      case 'alerta':
      case 'manutencao':
        return <AlertTriangle className="h-8 w-8 text-red-500" />;
      default:
        return null;
    }
  };

  const getElapsedTime = (startTime) => {
    if (!startTime) return '';
    const start = new Date(startTime);
    const minutes = differenceInMinutes(currentTime, start);
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  const shouldShowAlert = (digestor) => {
    if (digestor.status !== 'pronto' || !digestor.pronto_para_descarregar_at) return false;
    const minutesSinceReady = differenceInMinutes(currentTime, new Date(digestor.pronto_para_descarregar_at));
    return minutesSinceReady >= 30;
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar Gradient */}
      <div className="sidebar-gradient dark:sidebar-gradient fixed left-0 top-0 bottom-0 w-24 md:w-32 z-0" />
      
      <div className="relative z-10 p-4 md:p-8 ml-24 md:ml-32">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-4">
            <img 
              src="https://customer-assets.emergentagent.com/job_digestionmgr/artifacts/ng922rci_logo_menu.png.png" 
              alt="Campo do Gado Manutenção" 
              className="h-16 w-auto object-contain"
            />
            <div>
              <h1 className="text-3xl md:text-4xl font-black tracking-tight">Operador de Produção</h1>
              <p className="text-muted-foreground mt-1">
                Olá, {user?.nome} • 
                <span className="font-bold text-foreground ml-1">{entries.length} veículo(s)</span> no pátio
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <ThemeToggle />
            <Button variant="outline" onClick={handleLogout} data-testid="logout-button">
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </div>

        {/* Veículos no Pátio - Cards Compactos */}
        {entries.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-lg font-bold">Veículos no Pátio</h2>
                <p className="text-sm text-muted-foreground">
                  <span className="font-bold text-foreground">{entries.length} veículo(s)</span> • 
                  <span className="font-bold text-foreground ml-1">
                    {entries.reduce((sum, e) => sum + e.toneladas_declaradas, 0).toFixed(1)} ton
                  </span>
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-2">
              {entries.map((entry, index) => (
                <Card 
                  key={entry.id}
                  className="p-3 hover:shadow-lg transition-all cursor-pointer border-2 hover:border-primary"
                  onClick={() => {
                    setSelectedEntry(entry);
                    setToneladasEfetivas(entry.toneladas_declaradas.toString());
                    setShowDescarregamentoDialog(true);
                  }}
                  data-testid={`entry-${entry.id}`}
                >
                  <div className="flex flex-col items-center gap-1">
                    <div className="w-8 h-8 rounded-full bg-primary/10 border-2 border-primary flex items-center justify-center">
                      <span className="text-sm font-black">{index + 1}</span>
                    </div>
                    <p className="font-mono font-bold text-xs text-center">{entry.numero_frota}</p>
                    <div className="flex items-center gap-1">
                      <Weight className="h-3 w-3" />
                      <span className="font-mono font-bold text-sm">{entry.toneladas_declaradas}t</span>
                    </div>
                    <Button size="sm" className="w-full text-xs h-7 mt-1">
                      Descarregar
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Active Descarregamento */}
        {currentDescarregamento && !currentDescarregamento.end_at && (
          <Card className="mb-6 premium-card border-blue-500 bg-blue-500/5">
            <CardHeader>
              <CardTitle className="text-blue-600 dark:text-blue-400 flex items-center gap-2">
                <Clock className="h-5 w-5 animate-pulse" />
                Descarregamento em Andamento
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-mono font-bold text-xl">{currentDescarregamento.toneladas_efetivas} toneladas</p>
                  <p className="text-sm text-muted-foreground">
                    Tempo decorrido: {getElapsedTime(currentDescarregamento.start_at)}
                  </p>
                </div>
                <Button
                  size="lg"
                  onClick={() => handleFinishDescarregamento(currentDescarregamento.id)}
                  data-testid="finish-unload-button"
                >
                  <CheckCircle2 className="mr-2 h-5 w-5" />
                  Finalizar Descarregamento
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* DIGESTORES - FOCO PRINCIPAL */}
        <div>
          <h2 className="text-2xl font-black mb-4">Gestão dos Digestores</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {digestors.map((digestor) => (
              <Card 
                key={digestor.id} 
                className={`digestor-card border-t-8 ${getStatusColor(digestor.status)} transition-all hover:shadow-2xl`}
                data-testid={`digestor-card-${digestor.id}`}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between mb-2">
                    <CardTitle className="text-5xl font-black tracking-tight">
                      Digestor {digestor.id}
                    </CardTitle>
                    {getStatusIcon(digestor.status)}
                  </div>
                  <CardDescription className="uppercase text-sm font-bold tracking-wider text-lg">
                    {digestor.status.replace('_', ' ')}
                  </CardDescription>
                  {shouldShowAlert(digestor) && (
                    <div className="mt-3 p-3 bg-red-500/10 border-2 border-red-500 rounded-lg animate-pulse">
                      <p className="text-sm text-red-600 dark:text-red-400 font-bold flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5" />
                        ATENÇÃO: Aguardando há {getElapsedTime(digestor.pronto_para_descarregar_at)}!
                      </p>
                    </div>
                  )}
                </CardHeader>
                <CardContent className="space-y-4">
                  {digestor.current_operation_start && (
                    <div className="p-4 bg-muted rounded-xl border-2">
                      <p className="text-sm text-muted-foreground uppercase font-bold mb-2">
                        {digestor.status === 'pronto' ? 'Tempo Aguardando' : 'Tempo Ativo'}
                      </p>
                      <p className="font-mono text-4xl font-black">
                        {getElapsedTime(digestor.current_operation_start)}
                      </p>
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-3 text-sm">
                    <div className="text-center p-2 bg-muted/50 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-1">Ciclos</p>
                      <p className="font-mono font-black text-2xl">{digestor.total_ciclos}</p>
                    </div>
                    <div className="text-center p-2 bg-muted/50 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-1">Méd. Trit.</p>
                      <p className="font-mono font-black text-2xl">{digestor.tempo_medio_trituracao.toFixed(0)}m</p>
                    </div>
                    <div className="text-center p-2 bg-muted/50 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-1">Méd. Coz.</p>
                      <p className="font-mono font-black text-2xl">{digestor.tempo_medio_cozimento.toFixed(0)}m</p>
                    </div>
                  </div>

                  {digestor.status === 'livre' && currentDescarregamento && currentDescarregamento.end_at && (
                    <Button 
                      className="w-full h-14 text-lg font-bold"
                      onClick={() => handleStartTrituracao(digestor.id)}
                      data-testid={`start-trituration-${digestor.id}`}
                    >
                      <Play className="mr-2 h-5 w-5" />
                      Iniciar Trituração
                    </Button>
                  )}

                  {digestor.status === 'triturando' && currentTrituracao && currentTrituracao.digestor_id === digestor.id && (
                    <Button 
                      className="w-full h-14 text-lg font-bold"
                      variant="secondary"
                      onClick={() => handleFinishTrituracao(currentTrituracao.id, digestor.id)}
                      data-testid={`finish-trituration-${digestor.id}`}
                    >
                      <CheckCircle2 className="mr-2 h-5 w-5" />
                      Finalizar Trituração
                    </Button>
                  )}

                  {digestor.status === 'cozinhando' && (
                    <Button 
                      className="w-full h-14 text-lg font-bold"
                      variant="secondary"
                      onClick={() => handleFinishCozimento(digestor)}
                      data-testid={`finish-cooking-${digestor.id}`}
                    >
                      <CheckCircle2 className="mr-2 h-5 w-5" />
                      Finalizar Cozimento
                    </Button>
                  )}

                  {digestor.status === 'pronto' && (
                    <Button 
                      className="w-full h-14 text-lg font-bold btn-premium-green"
                      onClick={() => {
                        setSelectedDigestor(digestor);
                        setShowDescarregarDialog(true);
                      }}
                      data-testid={`descarregar-digestor-${digestor.id}`}
                    >
                      <Package className="mr-2 h-5 w-5" />
                      Descarregar Material
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Descarregamento Dialog */}
        <Dialog open={showDescarregamentoDialog} onOpenChange={setShowDescarregamentoDialog}>
          <DialogContent data-testid="descarregamento-dialog">
            <DialogHeader>
              <DialogTitle>Iniciar Descarregamento de Subproduto</DialogTitle>
              <DialogDescription>
                Confirme as toneladas efetivas da frota {selectedEntry?.numero_frota}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="toneladas-efetivas">Toneladas Efetivas</Label>
                <Input
                  id="toneladas-efetivas"
                  type="number"
                  step="0.01"
                  value={toneladasEfetivas}
                  onChange={(e) => setToneladasEfetivas(e.target.value)}
                  className="h-12 text-lg font-mono"
                  data-testid="toneladas-efetivas-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowDescarregamentoDialog(false)}>
                Cancelar
              </Button>
              <Button onClick={handleStartDescarregamento} data-testid="confirm-start-unload">
                Iniciar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Descarregar Digestor Dialog */}
        <Dialog open={showDescarregarDialog} onOpenChange={setShowDescarregarDialog}>
          <DialogContent data-testid="descarregar-dialog">
            <DialogHeader>
              <DialogTitle>Descarregar Digestor {selectedDigestor?.id}</DialogTitle>
              <DialogDescription>
                Confirme o descarregamento do material. Se houver algum problema, adicione uma observação.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {selectedDigestor && shouldShowAlert(selectedDigestor) && (
                <div className="p-3 bg-red-500/10 border border-red-500 rounded-lg">
                  <p className="text-sm text-red-600 dark:text-red-400 font-bold">
                    ⚠️ Digestor aguardando há mais de 30 minutos!
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Por favor, adicione uma observação se houver algum problema.
                  </p>
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="observacao">Observações (opcional)</Label>
                <Textarea
                  id="observacao"
                  placeholder="Ex: Máquina de transporte quebrada, aguardando reparo..."
                  value={observacao}
                  onChange={(e) => setObservacao(e.target.value)}
                  className="min-h-[100px]"
                  data-testid="observacao-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => {
                setShowDescarregarDialog(false);
                setObservacao('');
              }}>
                Cancelar
              </Button>
              <Button 
                onClick={handleDescarregarDigestor} 
                data-testid="confirm-descarregar"
                className="btn-premium-green"
              >
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Confirmar Descarregamento
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};