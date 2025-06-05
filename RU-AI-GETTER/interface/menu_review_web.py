#!/usr/bin/env python3
"""
Interface web para revisar e aprovar cardápios dos RUs.
Permite aprovar, excluir ou obter novamente cada JSON dos cardápios.
"""

import os
import json
import glob
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
import subprocess
import sys
import threading
import time

# Corrigir caminho absoluto para a pasta de templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
app = Flask(__name__, template_folder=TEMPLATES_DIR)

class MenuReviewApp:
    def __init__(self):
        self.jsons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jsons")
        self.status = "Pronto"
        
    def get_json_files(self):
        """Retorna lista de arquivos JSON."""
        json_pattern = os.path.join(self.jsons_dir, "*.json")
        return glob.glob(json_pattern)
    
    def load_json_content(self, file_path):
        """Carrega conteúdo de um arquivo JSON."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def get_file_info(self, file_path):
        """Obtém informações sobre o arquivo."""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        return {
            'name': file_name,
            'size': file_size,
            'modified': file_mtime.strftime('%d/%m/%Y %H:%M:%S')
        }
    
    def get_menu_stats(self, data):
        """Calcula estatísticas do cardápio."""
        total_days = len(data)
        days_with_meals = 0
        total_meals = 0
        
        for day, day_data in data.items():
            menu = day_data.get('menu', [])
            day_meals = 0
            for meal_period in menu:
                if meal_period and meal_period != ["Sem refeições disponíveis"]:
                    day_meals += len(meal_period)
            if day_meals > 0:
                days_with_meals += 1
            total_meals += day_meals
        
        return {
            'total_days': total_days,
            'days_with_meals': days_with_meals,
            'total_meals': total_meals
        }
    
    def validate_json_structure(self, data):
        """Valida estrutura básica do JSON."""
        issues = []
        
        for day, day_data in data.items():
            # Verificar formato da data
            try:
                datetime.strptime(day, '%Y-%m-%d')
            except ValueError:
                issues.append(f"Data inválida: {day}")
            
            # Verificar estrutura do dia
            if not isinstance(day_data, dict):
                issues.append(f"Dados do dia {day} não são um dicionário")
                continue
            
            # Verificar campos obrigatórios
            if 'menu' not in day_data:
                issues.append(f"Campo 'menu' ausente no dia {day}")
            elif not isinstance(day_data['menu'], list):
                issues.append(f"Campo 'menu' não é uma lista no dia {day}")
            
            if 'weekday' not in day_data:
                issues.append(f"Campo 'weekday' ausente no dia {day}")
        
        return issues

# Instância global da aplicação
review_app = MenuReviewApp()

@app.route('/')
def index():
    """Página principal."""
    json_files = review_app.get_json_files()
    file_names = [os.path.basename(f) for f in json_files]
    
    # Separar arquivos aprovados e não aprovados
    approved_files = []
    pending_files = []
    total_days = 0
    total_meals = 0
    files_with_issues = 0
    
    for file_path in json_files:
        file_name = os.path.basename(file_path)
        data = review_app.load_json_content(file_path)
        if not data:
            continue
        
        is_approved = any(day_data.get('approved', False) for day_data in data.values())
        approval_timestamp = None
        for day_data in data.values():
            if day_data.get('approved_timestamp'):
                approval_timestamp = day_data['approved_timestamp']
                break
            
        # Calcular estatísticas
        stats = review_app.get_menu_stats(data)
        issues = review_app.validate_json_structure(data)
        
        total_days += stats['total_days']
        total_meals += stats['total_meals']
        if issues:
            files_with_issues += 1
        
        # Formatar timestamp de aprovação
        approval_date_formatted = None
        if approval_timestamp:
            approval_date_formatted = datetime.fromtimestamp(approval_timestamp).strftime('%d/%m/%Y %H:%M')
        
        file_info = {
            'name': file_name,
            'ru_name': file_name.replace('.json', '').replace('_', ' ').title(),
            'approval_timestamp': approval_timestamp,
            'approval_date': approval_date_formatted,
            'stats': stats,
            'issues_count': len(issues),
            'file_size': os.path.getsize(file_path),
            'file_size_mb': round(os.path.getsize(file_path) / 1024 / 1024, 2)
        }
        
        if is_approved:
            approved_files.append(file_info)
        else:
            pending_files.append(file_info)
    
    # Ordenar por timestamp de aprovação (mais recentes primeiro)
    approved_files.sort(key=lambda x: x['approval_timestamp'] or 0, reverse=True)
    
    # Estatísticas globais
    dashboard_stats = {
        'total_files': len(json_files),
        'approved_files': len(approved_files),
        'pending_files': len(pending_files),
        'total_days': total_days,
        'total_meals': total_meals,
        'files_with_issues': files_with_issues
    }
    
    return render_template('index.html', 
                         approved_files=approved_files,
                         pending_files=pending_files,
                         dashboard_stats=dashboard_stats,
                         status=review_app.status)

@app.route('/view/<filename>')
def view_file(filename):
    """Visualizar um arquivo específico."""
    file_path = os.path.join(review_app.jsons_dir, filename)
    
    if not os.path.exists(file_path):
        return "Arquivo não encontrado", 404
    
    data = review_app.load_json_content(file_path)
    if data is None:
        return "Erro ao carregar arquivo", 500
    
    file_info = review_app.get_file_info(file_path)
    stats = review_app.get_menu_stats(data)
    issues = review_app.validate_json_structure(data)
    
    # Verificar se está aprovado e formatar data
    is_approved = any(day_data.get('approved', False) for day_data in data.values())
    approval_date = None
    if is_approved:
        for day_data in data.values():
            if day_data.get('approved_timestamp'):
                approval_date = datetime.fromtimestamp(day_data['approved_timestamp']).strftime('%d/%m/%Y %H:%M')
                break
    
    return render_template('view_file.html', 
                         filename=filename,
                         file_info=file_info,
                         stats=stats,
                         issues=issues,
                         data=data,
                         is_approved=is_approved,
                         approval_date=approval_date)

@app.route('/api/approve/<filename>', methods=['POST'])
def approve_file(filename):
    """Aprovar um arquivo."""
    try:
        file_path = os.path.join(review_app.jsons_dir, filename)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Adicionar metadata de aprovação
        for day_data in data.values():
            day_data['approved'] = True
            day_data['approved_timestamp'] = int(datetime.now().timestamp())
        
        # Salvar arquivo atualizado
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        review_app.status = f"Cardápio aprovado: {filename}"
        return jsonify({'success': True, 'message': f'Cardápio {filename} aprovado com sucesso!'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao aprovar: {e}'}), 500

@app.route('/api/delete/<filename>', methods=['POST'])
def delete_file(filename):
    """Excluir um arquivo."""
    try:
        file_path = os.path.join(review_app.jsons_dir, filename)
        os.remove(file_path)
        
        review_app.status = f"Cardápio excluído: {filename}"
        return jsonify({'success': True, 'message': f'Cardápio {filename} excluído com sucesso!'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao excluir: {e}'}), 500

@app.route('/api/regenerate/<filename>', methods=['POST'])
def regenerate_file(filename):
    """Regenerar um arquivo."""
    def regenerate_worker():
        try:
            review_app.status = f"Regenerando {filename}..."
            
            # Executar o scraper principal
            script_path = os.path.join(os.path.dirname(__file__), "main.py")
            result = subprocess.run([sys.executable, script_path], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                review_app.status = f"Cardápio regenerado: {filename}"
            else:
                review_app.status = "Erro na regeneração"
                
        except Exception:
            review_app.status = "Erro na regeneração"
    
    # Executar em thread separada
    thread = threading.Thread(target=regenerate_worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'Regeneração iniciada...'})

@app.route('/api/validate_all', methods=['POST'])
def validate_all():
    """Validar todos os arquivos."""
    def validate_worker():
        try:
            review_app.status = "Validando todos os arquivos..."
            
            # Usar o validador do projeto
            script_path = os.path.join(os.path.dirname(__file__), "json_validator.py")
            result = subprocess.run([sys.executable, script_path], 
                                  capture_output=True, text=True, timeout=60)
            
            review_app.status = "Validação concluída"
                
        except Exception:
            review_app.status = "Erro na validação"
    
    # Executar em thread separada
    thread = threading.Thread(target=validate_worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'Validação iniciada...'})

@app.route('/api/approve_all', methods=['POST'])
def approve_all():
    """Aprovar todos os arquivos pendentes."""
    try:
        json_files = review_app.get_json_files()
        approved_count = 0
        
        for file_path in json_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Verificar se já está aprovado
            is_approved = any(day_data.get('approved', False) for day_data in data.values())
            if not is_approved:
                # Adicionar metadata de aprovação
                for day_data in data.values():
                    day_data['approved'] = True
                    day_data['approved_timestamp'] = int(datetime.now().timestamp())
                
                # Salvar arquivo atualizado
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                approved_count += 1
        
        review_app.status = f"Aprovação em lote concluída: {approved_count} cardápios aprovados"
        return jsonify({'success': True, 'message': f'{approved_count} cardápios aprovados com sucesso!'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro na aprovação em lote: {e}'}), 500

@app.route('/api/unapprove/<filename>', methods=['POST'])
def unapprove_file(filename):
    """Remover aprovação de um arquivo."""
    try:
        file_path = os.path.join(review_app.jsons_dir, filename)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Remover metadata de aprovação
        for day_data in data.values():
            if 'approved' in day_data:
                del day_data['approved']
            if 'approved_timestamp' in day_data:
                del day_data['approved_timestamp']
        
        # Salvar arquivo atualizado
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        review_app.status = f"Aprovação removida: {filename}"
        return jsonify({'success': True, 'message': f'Aprovação do cardápio {filename} removida com sucesso!'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao remover aprovação: {e}'}), 500

@app.route('/api/status')
def get_status():
    """Obter status atual."""
    return jsonify({'status': review_app.status})

@app.route('/api/edit/<filename>', methods=['POST'])
def edit_file(filename):
    """Salvar edições de um arquivo."""
    try:
        file_path = os.path.join(review_app.jsons_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Arquivo não encontrado'}), 404
        
        # Obter dados editados do request
        edited_data = request.get_json()
        
        if not edited_data:
            return jsonify({'success': False, 'message': 'Dados inválidos'}), 400
        
        # Validar estrutura básica
        issues = review_app.validate_json_structure(edited_data)
        if issues:
            return jsonify({
                'success': False, 
                'message': f'Estrutura inválida: {"; ".join(issues[:3])}'
            }), 400
        
        # Fazer backup do arquivo original
        backup_path = file_path + '.bak'
        with open(file_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(original_data, f, ensure_ascii=False, indent=2)
        
        # Salvar dados editados
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(edited_data, f, ensure_ascii=False, indent=2)
        
        review_app.status = f"Cardápio editado: {filename}"
        return jsonify({'success': True, 'message': f'Cardápio {filename} editado com sucesso!'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao salvar edições: {e}'}), 500

if __name__ == '__main__':
    # Criar templates se não existirem
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)

    import socket
    def find_free_port(preferred_ports):
        for port in preferred_ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        raise RuntimeError("Nenhuma porta disponível para o servidor web.")

    ports = [8080, 8081, 8082]
    port = find_free_port(ports)
    print(f"Abrindo interface web de revisão de cardápios...")
    print(f"Acesse: http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)
