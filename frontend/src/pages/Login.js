import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { Loader2, ShieldCheck } from 'lucide-react';

export const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  
  const [loginData, setLoginData] = useState({
    email: '',
    senha: ''
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const user = await login(loginData.email, loginData.senha);
      toast.success(`Bem-vindo, ${user.nome}!`);
      
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao fazer login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 login-bg">
      <Card className="w-full max-w-md relative z-10 premium-card shadow-2xl">
        <CardHeader className="space-y-4">
          <div className="flex justify-center">
            <div className="login-logo"><ShieldCheck size={42}/><span>CG</span></div>
          </div>
          <CardTitle className="text-2xl font-black tracking-tight text-center">
            Manutenção Frigorífico Campo do Gado
          </CardTitle>
          <CardDescription className="text-center text-muted-foreground font-medium">
            Controle de Manutenção Industrial e Frota
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-1">
              <TabsTrigger value="login" data-testid="login-tab">Entrar</TabsTrigger>
            </TabsList>
            
            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email ou Usuário</Label>
                  <Input
                    id="email"
                    data-testid="login-email-input"
                    type="text"
                    placeholder="seu.email@empresa.com"
                    value={loginData.email}
                    onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                    required
                    className="h-12 text-lg"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="senha">Senha</Label>
                  <Input
                    id="senha"
                    data-testid="login-password-input"
                    type="password"
                    placeholder="••••••••"
                    value={loginData.senha}
                    onChange={(e) => setLoginData({ ...loginData, senha: e.target.value })}
                    required
                    className="h-12 text-lg"
                  />
                </div>
                
                <Button 
                  type="submit" 
                  className="w-full h-12 text-lg font-bold uppercase tracking-wide"
                  disabled={loading}
                  data-testid="login-submit-button"
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Entrando...
                    </>
                  ) : (
                    'Entrar na Planta'
                  )}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};