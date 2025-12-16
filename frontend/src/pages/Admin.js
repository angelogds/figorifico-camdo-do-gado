import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { toast } from 'sonner';
import { BarChart, Package, Clock, LogOut, TrendingUp, AlertTriangle } from 'lucide-react';
import { ThemeToggle } from '../components/ThemeToggle';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const Admin = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [alertas, setAlertas] = useState([]);
  const [manutencoes, setManutencoes] = useState([]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, alertasRes, manutencoesRes] = await Promise.all([
        axios.get(`${API}/stats/dashboard`),
        axios.get(`${API}/alertas?resolvido=false`),
        axios.get(`${API}/manutencao`)
      ]);
      
      setStats(statsRes.data);
      setAlertas(alertasRes.data);
      setManutencoes(manutencoesRes.data);
    } catch (error) {
      console.error('Erro ao buscar dados:', error);
    }
  };

  const handleInitDigestors = async () => {
    try {
      await axios.post(`${API}/digestors/init`);
      toast.success('Digestores inicializados!');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao inicializar digestores');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
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
              <h1 className="text-3xl md:text-4xl font-black tracking-tight">Administração</h1>
              <p className="text-muted-foreground mt-1">Olá, {user?.nome}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <ThemeToggle />
            <Button variant="outline" onClick={handleLogout} data-testid="logout-button">
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid md:grid-cols-4 gap-4 mb-8">
            <Card data-testid="stat-entradas" className="premium-card">
            <CardHeader className="pb-2">
              <CardDescription>Frotas Hoje</CardDescription>
              <CardTitle className="text-4xl font-black font-mono">
                {stats.total_entradas_hoje}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground flex items-center gap-1">
                <Package className="h-4 w-4" />
                Veículos com subproduto
              </p>
            </CardContent>
          </Card>

            <Card data-testid="stat-toneladas" className="premium-card">
            <CardHeader className="pb-2">
              <CardDescription>Subproduto Hoje</CardDescription>
              <CardTitle className="text-4xl font-black font-mono">
                {stats.total_toneladas_hoje.toFixed(1)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground flex items-center gap-1">
                <TrendingUp className="h-4 w-4" />
                Toneladas de material animal
              </p>
            </CardContent>
          </Card>

            <Card data-testid="stat-ciclos" className="premium-card">
            <CardHeader className="pb-2">
              <CardDescription>Ciclos Ativos</CardDescription>
              <CardTitle className="text-4xl font-black font-mono">
                {stats.ciclos_ativos}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground flex items-center gap-1">
                <Clock className="h-4 w-4" />
                Em processamento
              </p>
            </CardContent>
          </Card>

            <Card data-testid="stat-alertas" className="premium-card">
            <CardHeader className="pb-2">
              <CardDescription>Alertas Ativos</CardDescription>
              <CardTitle className="text-4xl font-black font-mono text-red-500">
                {stats.alertas_ativos}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground flex items-center gap-1">
                <AlertTriangle className="h-4 w-4" />
                Requerem atenção
              </p>
              </CardContent>
            </Card>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          {/* Digestors Performance */}
          <Card data-testid="digestors-performance-card" className="premium-card">
          <CardHeader>
            <CardTitle className="text-2xl font-bold flex items-center gap-2">
              <BarChart className="h-6 w-6" />
              Desempenho dos Digestores
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats?.digestores && stats.digestores.length > 0 ? (
              <div className="space-y-4">
                {stats.digestores.map((digestor) => (
                  <div key={digestor.id} className="p-4 border rounded-lg">
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="font-bold text-lg">{digestor.nome}</h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        digestor.status === 'livre' ? 'bg-green-500/10 text-green-600' :
                        digestor.status === 'triturando' || digestor.status === 'cozinhando' ? 'bg-yellow-500/10 text-yellow-600' :
                        'bg-red-500/10 text-red-600'
                      }`}>
                        {digestor.status.toUpperCase()}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-xs text-muted-foreground">Total Ciclos</p>
                        <p className="font-mono font-bold text-lg">{digestor.total_ciclos}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Média Trituração</p>
                        <p className="font-mono font-bold text-lg">{digestor.tempo_medio_trituracao.toFixed(1)}m</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Média Cozimento</p>
                        <p className="font-mono font-bold text-lg">{digestor.tempo_medio_cozimento.toFixed(1)}m</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-muted-foreground mb-4">Nenhum digestor encontrado</p>
                <Button onClick={handleInitDigestors} data-testid="init-digestors-button">
                  Inicializar 4 Digestores
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

          {/* Active Alerts */}
          <Card data-testid="active-alerts-card" className="premium-card">
          <CardHeader>
            <CardTitle className="text-2xl font-bold flex items-center gap-2">
              <AlertTriangle className="h-6 w-6" />
              Alertas e Manutenções
            </CardTitle>
            <CardDescription>{alertas.length} alertas ativos</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {alertas.length > 0 ? (
                alertas.map((alerta) => (
                  <div key={alerta.id} className="p-4 border-l-4 border-red-500 bg-red-500/5 rounded">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-bold">Digestor {alerta.digestor_id}</p>
                        <p className="text-sm">{alerta.mensagem}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {format(new Date(alerta.created_at), "dd/MM/yyyy HH:mm", { locale: ptBR })}
                        </p>
                      </div>
                      <span className="px-2 py-1 bg-red-500 text-white text-xs rounded font-bold">
                        {alerta.tipo.toUpperCase()}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-center text-muted-foreground py-8">Nenhum alerta ativo</p>
              )}

              {manutencoes.filter(m => !m.concluida).length > 0 && (
                <div className="pt-4 border-t">
                  <h4 className="font-bold mb-2">Manutenções Pendentes</h4>
                  {manutencoes.filter(m => !m.concluida).map((man) => (
                    <div key={man.id} className="p-3 border rounded mb-2">
                      <p className="font-bold">Digestor {man.digestor_id}</p>
                      <p className="text-sm">{man.descricao}</p>
                      <p className="text-xs text-muted-foreground">Por: {man.responsavel_name}</p>
                    </div>
                  ))}
                </div>
              )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};