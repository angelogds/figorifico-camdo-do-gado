#!/usr/bin/env python3
"""
RecycleFlow OS Backend API Testing Suite
Tests all backend endpoints for the industrial recycling control system
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class RecycleFlowAPITester:
    def __init__(self, base_url="https://digestionmgr.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test credentials
        self.credentials = {
            'admin': {'email': 'admin@recycleflow.com', 'senha': 'admin123'},
            'portaria': {'email': 'portaria@recycleflow.com', 'senha': 'portaria123'},
            'operador': {'email': 'operador@recycleflow.com', 'senha': 'operador123'}
        }

    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            'name': name,
            'success': success,
            'details': details,
            'response_data': response_data
        })

    def make_request(self, method: str, endpoint: str, data: Dict = None, 
                    token: str = None, expected_status: int = 200) -> tuple[bool, Dict]:
        """Make HTTP request with error handling"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return False, {'error': f'Unsupported method: {method}'}

            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = {'status_code': response.status_code, 'text': response.text}

            return success, response_data

        except requests.exceptions.RequestException as e:
            return False, {'error': str(e)}

    def test_authentication(self):
        """Test authentication for all user roles"""
        print("\n🔐 Testing Authentication...")
        
        for role, creds in self.credentials.items():
            success, response = self.make_request('POST', 'auth/login', creds)
            
            if success and 'token' in response:
                self.tokens[role] = response['token']
                self.users[role] = response['user']
                self.log_test(f"Login {role}", True, f"User: {response['user']['nome']}")
            else:
                self.log_test(f"Login {role}", False, f"Failed: {response}")
                return False
        
        return True

    def test_user_info(self):
        """Test getting user information"""
        print("\n👤 Testing User Information...")
        
        for role, token in self.tokens.items():
            success, response = self.make_request('GET', 'auth/me', token=token)
            
            if success and 'email' in response:
                self.log_test(f"Get user info {role}", True, f"Email: {response['email']}")
            else:
                self.log_test(f"Get user info {role}", False, f"Failed: {response}")

    def test_digestors_initialization(self):
        """Test digestors initialization"""
        print("\n🏭 Testing Digestors...")
        
        # First check if digestors exist
        success, response = self.make_request('GET', 'digestors', token=self.tokens['admin'])
        
        if success:
            digestors_count = len(response) if isinstance(response, list) else 0
            self.log_test("Get digestors", True, f"Found {digestors_count} digestors")
            
            if digestors_count == 0:
                # Initialize digestors
                success, response = self.make_request('POST', 'digestors/init', token=self.tokens['admin'])
                if success:
                    self.log_test("Initialize digestors", True, "4 digestors created")
                else:
                    self.log_test("Initialize digestors", False, f"Failed: {response}")
            else:
                self.log_test("Digestors already exist", True, f"{digestors_count} digestors found")
        else:
            self.log_test("Get digestors", False, f"Failed: {response}")

    def test_entries_workflow(self):
        """Test complete entries workflow"""
        print("\n🚛 Testing Entries Workflow...")
        
        # Test creating entry (Portaria role)
        entry_data = {
            'placa': f'TEST-{datetime.now().strftime("%H%M")}',
            'frota': 'Frota Test',
            'toneladas_declaradas': 25.5
        }
        
        success, response = self.make_request('POST', 'entries', entry_data, token=self.tokens['portaria'])
        
        if success and 'id' in response:
            entry_id = response['id']
            self.log_test("Create entry", True, f"Entry ID: {entry_id}, Placa: {response['placa']}")
            
            # Test listing entries
            success, entries = self.make_request('GET', 'entries', token=self.tokens['portaria'])
            if success and isinstance(entries, list):
                self.log_test("List entries", True, f"Found {len(entries)} entries")
            else:
                self.log_test("List entries", False, f"Failed: {entries}")
                
            return entry_id
        else:
            self.log_test("Create entry", False, f"Failed: {response}")
            return None

    def test_descarregamento_workflow(self, entry_id: str):
        """Test unloading workflow"""
        print("\n📦 Testing Descarregamento Workflow...")
        
        if not entry_id:
            self.log_test("Descarregamento workflow", False, "No entry_id provided")
            return None
        
        # Start descarregamento
        descarregamento_data = {
            'entry_id': entry_id,
            'toneladas_efetivas': 24.8
        }
        
        success, response = self.make_request('POST', 'descarregamento/start', 
                                            descarregamento_data, token=self.tokens['operador'])
        
        if success and 'id' in response:
            descarregamento_id = response['id']
            self.log_test("Start descarregamento", True, f"Descarregamento ID: {descarregamento_id}")
            
            # Finish descarregamento
            success, response = self.make_request('POST', f'descarregamento/{descarregamento_id}/finish', 
                                                token=self.tokens['operador'])
            if success:
                self.log_test("Finish descarregamento", True, f"Time: {response.get('tempo_minutos', 'N/A')} min")
            else:
                self.log_test("Finish descarregamento", False, f"Failed: {response}")
                
            return descarregamento_id
        else:
            self.log_test("Start descarregamento", False, f"Failed: {response}")
            return None

    def test_trituracao_workflow(self, descarregamento_id: str):
        """Test grinding workflow"""
        print("\n⚙️ Testing Trituração Workflow...")
        
        if not descarregamento_id:
            self.log_test("Trituração workflow", False, "No descarregamento_id provided")
            return None
        
        # Start trituração
        trituracao_data = {
            'descarregamento_id': descarregamento_id,
            'digestor_id': 1,
            'toneladas': 24.8
        }
        
        success, response = self.make_request('POST', 'trituracao/start', 
                                            trituracao_data, token=self.tokens['operador'])
        
        if success and 'id' in response:
            trituracao_id = response['id']
            self.log_test("Start trituração", True, f"Trituração ID: {trituracao_id}")
            
            # Finish trituração
            success, response = self.make_request('POST', f'trituracao/{trituracao_id}/finish', 
                                                token=self.tokens['operador'])
            if success:
                self.log_test("Finish trituração", True, f"Time: {response.get('tempo_minutos', 'N/A')} min")
            else:
                self.log_test("Finish trituração", False, f"Failed: {response}")
                
            return trituracao_id
        else:
            self.log_test("Start trituração", False, f"Failed: {response}")
            return None

    def test_cozimento_workflow(self, trituracao_id: str):
        """Test cooking workflow"""
        print("\n🔥 Testing Cozimento Workflow...")
        
        if not trituracao_id:
            self.log_test("Cozimento workflow", False, "No trituracao_id provided")
            return None
        
        # Start cozimento
        cozimento_data = {
            'trituracao_id': trituracao_id,
            'digestor_id': 1
        }
        
        success, response = self.make_request('POST', 'cozimento/start', 
                                            cozimento_data, token=self.tokens['operador'])
        
        if success and 'id' in response:
            cozimento_id = response['id']
            self.log_test("Start cozimento", True, f"Cozimento ID: {cozimento_id}")
            
            # Finish cozimento
            success, response = self.make_request('POST', f'cozimento/{cozimento_id}/finish', 
                                                token=self.tokens['operador'])
            if success:
                self.log_test("Finish cozimento", True, f"Time: {response.get('tempo_minutos', 'N/A')} min")
            else:
                self.log_test("Finish cozimento", False, f"Failed: {response}")
                
            return cozimento_id
        else:
            self.log_test("Start cozimento", False, f"Failed: {response}")
            return None

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        print("\n📊 Testing Dashboard Stats...")
        
        success, response = self.make_request('GET', 'stats/dashboard', token=self.tokens['admin'])
        
        if success and isinstance(response, dict):
            stats = response
            self.log_test("Get dashboard stats", True, 
                         f"Entries today: {stats.get('total_entradas_hoje', 0)}, "
                         f"Tons today: {stats.get('total_toneladas_hoje', 0)}")
        else:
            self.log_test("Get dashboard stats", False, f"Failed: {response}")

    def test_alertas_system(self):
        """Test alerts system"""
        print("\n🚨 Testing Alertas System...")
        
        # List alertas
        success, response = self.make_request('GET', 'alertas', token=self.tokens['admin'])
        
        if success and isinstance(response, list):
            self.log_test("List alertas", True, f"Found {len(response)} alertas")
        else:
            self.log_test("List alertas", False, f"Failed: {response}")

    def test_manutencao_system(self):
        """Test maintenance system"""
        print("\n🔧 Testing Manutenção System...")
        
        # List manutencoes
        success, response = self.make_request('GET', 'manutencao', token=self.tokens['admin'])
        
        if success and isinstance(response, list):
            self.log_test("List manutenções", True, f"Found {len(response)} manutenções")
        else:
            self.log_test("List manutenções", False, f"Failed: {response}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting RecycleFlow OS Backend API Tests...")
        print(f"🌐 Testing against: {self.base_url}")
        
        # Authentication tests
        if not self.test_authentication():
            print("❌ Authentication failed - stopping tests")
            return False
        
        # User info tests
        self.test_user_info()
        
        # Digestors tests
        self.test_digestors_initialization()
        
        # Complete workflow test
        entry_id = self.test_entries_workflow()
        if entry_id:
            descarregamento_id = self.test_descarregamento_workflow(entry_id)
            if descarregamento_id:
                trituracao_id = self.test_trituracao_workflow(descarregamento_id)
                if trituracao_id:
                    self.test_cozimento_workflow(trituracao_id)
        
        # Dashboard and stats tests
        self.test_dashboard_stats()
        self.test_alertas_system()
        self.test_manutencao_system()
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = RecycleFlowAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())