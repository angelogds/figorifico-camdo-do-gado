import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { toast } from 'sonner';
import { Truck, Clock, Weight, LogOut } from 'lucide-react';
import { ThemeToggle } from '../components/ThemeToggle';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const Portaria = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [entries, setEntries] = useState([]);
  const [formData, setFormData] = useState({
    numero_frota: '',
    toneladas_declaradas: ''
  });

  useEffect(() => {
    fetchEntries();
    const interval = setInterval(fetchEntries, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchEntries = async () => {
    try {
      const response = await axios.get(`${API}/entries`);
      setEntries(response.data);
    } catch (error) {
      console.error('Erro ao buscar entradas:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      await axios.post(`${API}/entries`, {
        numero_frota: formData.numero_frota.toUpperCase(),
        toneladas_declaradas: parseFloat(formData.toneladas_declaradas)
      });
      
      toast.success('Entrada de subproduto registrada com sucesso!');
      setFormData({ numero_frota: '', toneladas_declaradas: '' });
      fetchEntries();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao registrar entrada');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'aguardando_descarregamento':
        return 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20';
      case 'descarregando':
        return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
      case 'descarregado':
        return 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20';
      default:
        return 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20';
    }
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
              <h1 className="text-3xl md:text-4xl font-black tracking-tight">Portaria</h1>
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

        <div className="grid md:grid-cols-2 gap-6">
          {/* Registration Form */}
          <Card className="premium-card" data-testid="entry-form-card">
          <CardHeader>
            <CardTitle className="text-2xl font-bold flex items-center gap-2">
              <Truck className="h-6 w-6" />
              Nova Entrada de Subproduto
            </CardTitle>
            <CardDescription>Registrar chegada de caminhão com material animal</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="numero_frota">Número da Frota</Label>
                <Input
                  id="numero_frota"
                  data-testid="frota-input"
                  placeholder="FROTA-001"
                  value={formData.numero_frota}
                  onChange={(e) => setFormData({ ...formData, numero_frota: e.target.value })}
                  required
                  className="h-12 text-lg uppercase font-mono"
                />
                <p className="text-xs text-muted-foreground">Ex: FROTA-001, F-123, etc.</p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="toneladas">Toneladas de Subproduto</Label>
                <Input
                  id="toneladas"
                  data-testid="toneladas-input"
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="25.5"
                  value={formData.toneladas_declaradas}
                  onChange={(e) => setFormData({ ...formData, toneladas_declaradas: e.target.value })}
                  required
                  className="h-12 text-lg font-mono"
                />
                <p className="text-xs text-muted-foreground">Peso do material animal (ossos, vísceras, etc.)</p>
              </div>
              
              <Button 
                type="submit" 
                className="w-full h-12 text-lg font-bold uppercase tracking-wide btn-premium-green"
                data-testid="submit-entry-button"
              >
                Registrar Entrada de Material
              </Button>
            </form>
          </CardContent>
        </Card>

          {/* Recent Entries */}
          <Card className="premium-card" data-testid="recent-entries-card">
          <CardHeader>
            <CardTitle className="text-2xl font-bold flex items-center gap-2">
              <Clock className="h-6 w-6" />
              Entradas Recentes de Subproduto
            </CardTitle>
            <CardDescription>{entries.length} frotas registradas</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {entries.slice(0, 10).map((entry) => (
                <div 
                  key={entry.id} 
                  className="p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                  data-testid={`entry-${entry.id}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-mono font-bold text-lg">{entry.numero_frota}</p>
                      <p className="text-xs text-muted-foreground">Material Animal</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getStatusColor(entry.status)}`}>
                      {entry.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1">
                      <Weight className="h-4 w-4 text-muted-foreground" />
                      <span className="font-mono font-medium">{entry.toneladas_declaradas} t</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span className="text-muted-foreground">
                        {format(new Date(entry.arrival_at), "HH:mm", { locale: ptBR })}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
              
              {entries.length === 0 && (
                <p className="text-center text-muted-foreground py-8">Nenhuma entrada registrada hoje</p>
              )}
            </div>
          </CardContent>
        </Card>
        </div>
      </div>
    </div>
  );
};