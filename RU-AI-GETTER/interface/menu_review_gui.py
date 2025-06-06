#!/usr/bin/env python3
"""
Interface gráfica para revisar e aprovar cardápios dos RUs.
Permite aprovar, excluir ou obter novamente cada JSON dos cardápios.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import glob
from datetime import datetime
from typing import Dict, Any, List
import threading
import subprocess
import sys

# Importar o módulo de upload para Firebase
try:
    from core.firebase_uploader import upload_menu_to_firebase, upload_approved_menus, test_firebase_connection
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

class MenuReviewGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Revisor de Cardápios dos RUs")
        self.root.geometry("1200x800")
        
        # Configurar estilo
        style = ttk.Style()
        style.theme_use('clam')
        
        # Variáveis
        self.jsons_dir = os.path.join(os.path.dirname(__file__), "jsons")
        self.json_files = []
        self.current_json_index = 0
        self.current_json_data = {}
        
        # Criar interface
        self.create_widgets()
        self.load_json_files()
        
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configurar redimensionamento
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text="Revisor de Cardápios dos RUs", 
                               style='Heading.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Frame de controles
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=1, column=0, columnspan=3, sticky="we", pady=(0, 10))
        controls_frame.columnconfigure(1, weight=1)
        
        # Lista de arquivos
        ttk.Label(controls_frame, text="Arquivo:").grid(row=0, column=0, padx=(0, 10))
        
        self.file_combo = ttk.Combobox(controls_frame, state="readonly")
        self.file_combo.grid(row=0, column=1, sticky="we", padx=(0, 10))
        self.file_combo.bind('<<ComboboxSelected>>', self.on_file_selected)
        
        # Botão atualizar lista
        refresh_btn = ttk.Button(controls_frame, text="Atualizar Lista", 
                                command=self.load_json_files)
        refresh_btn.grid(row=0, column=2)
        
        # Frame de conteúdo
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=2, column=0, columnspan=3, sticky="nsew")
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Painel esquerdo - informações do arquivo
        left_panel = ttk.LabelFrame(content_frame, text="Informações do Arquivo", padding="10")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Status do arquivo
        self.file_info_text = scrolledtext.ScrolledText(left_panel, width=40, height=15)
        self.file_info_text.grid(row=0, column=0, sticky="nsew")
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(0, weight=1)
        
        # Painel direito - conteúdo do JSON
        right_panel = ttk.LabelFrame(content_frame, text="Conteúdo do Cardápio", padding="10")
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        
        # Visualizador do JSON
        self.json_display = scrolledtext.ScrolledText(right_panel, wrap=tk.WORD)
        self.json_display.grid(row=0, column=0, sticky="nsew")
        
        # Frame de ações
        actions_frame = ttk.Frame(main_frame)
        actions_frame.grid(row=3, column=0, columnspan=3, pady=(20, 0))
        
        # Botões de ação
        self.approve_btn = ttk.Button(actions_frame, text="✅ Aprovar", 
                                     command=self.approve_menu, style='Success.TButton')
        self.approve_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.delete_btn = ttk.Button(actions_frame, text="🗑️ Excluir", 
                                    command=self.delete_menu, style='Danger.TButton')
        self.delete_btn.grid(row=0, column=1, padx=(0, 10))
        
        self.regenerate_btn = ttk.Button(actions_frame, text="🔄 Obter Novamente", 
                                        command=self.regenerate_menu)
        self.regenerate_btn.grid(row=0, column=2, padx=(0, 10))
        
        self.validate_all_btn = ttk.Button(actions_frame, text="🔍 Validar Todos", 
                                          command=self.validate_all_files)
        self.validate_all_btn.grid(row=0, column=3, padx=(0, 10))
        
        # Botão de upload para o Firebase (sempre visível)
        self.upload_btn = ttk.Button(actions_frame, text="📤 Upload Firebase", 
                                    command=self.upload_approved_menus, style='Upload.TButton')
        self.upload_btn.grid(row=0, column=4)
        
        # Configurar estilos para botões
        style = ttk.Style()
        style.configure('Success.TButton', foreground='darkgreen')
        style.configure('Danger.TButton', foreground='darkred')
        style.configure('Upload.TButton', foreground='darkblue')
        style.configure('Heading.TLabel', font=('TkDefaultFont', 16, 'bold'))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Pronto")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=3, sticky="we", pady=(10, 0))
    
    def load_json_files(self):
        """Carrega a lista de arquivos JSON."""
        try:
            json_pattern = os.path.join(self.jsons_dir, "*.json")
            self.json_files = glob.glob(json_pattern)
            
            # Atualizar combobox
            file_names = [os.path.basename(f) for f in self.json_files]
            self.file_combo['values'] = file_names
            
            if file_names:
                self.file_combo.current(0)
                self.on_file_selected()
                self.status_var.set(f"Carregados {len(file_names)} arquivos JSON")
            else:
                self.status_var.set("Nenhum arquivo JSON encontrado")
                self.clear_display()
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivos: {e}")
            self.status_var.set("Erro ao carregar arquivos")
    
    def on_file_selected(self, event=None):
        """Chamado quando um arquivo é selecionado."""
        if not self.file_combo.get():
            return
            
        selected_file = os.path.join(self.jsons_dir, self.file_combo.get())
        self.load_json_content(selected_file)
    
    def load_json_content(self, file_path):
        """Carrega e exibe o conteúdo de um arquivo JSON."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.current_json_data = json.load(f)
            
            self.display_json_content(file_path)
            self.status_var.set(f"Arquivo carregado: {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao ler arquivo JSON: {e}")
            self.status_var.set("Erro ao carregar arquivo")
    
    def display_json_content(self, file_path):
        """Exibe o conteúdo do JSON de forma organizada."""
        # Limpar displays
        self.file_info_text.delete(1.0, tk.END)
        self.json_display.delete(1.0, tk.END)
        
        # Informações do arquivo
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        info_text = f"📁 Arquivo: {file_name}\n"
        info_text += f"📏 Tamanho: {file_size} bytes\n"
        info_text += f"🕒 Modificado: {file_mtime.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        
        # Estatísticas do cardápio
        total_days = len(self.current_json_data)
        days_with_meals = 0
        total_meals = 0
        
        for day, data in self.current_json_data.items():
            menu = data.get('menu', [])
            day_meals = 0
            for meal_period in menu:
                if meal_period and meal_period != ["Sem refeições disponíveis"]:
                    day_meals += len(meal_period)
            if day_meals > 0:
                days_with_meals += 1
            total_meals += day_meals
        
        info_text += f"📅 Total de dias: {total_days}\n"
        info_text += f"🍽️ Dias com refeições: {days_with_meals}\n"
        info_text += f"🥘 Total de pratos: {total_meals}\n\n"
        
        # Validação básica
        validation_issues = self.validate_json_structure(self.current_json_data)
        if validation_issues:
            info_text += "⚠️ Problemas encontrados:\n"
            for issue in validation_issues[:10]:  # Mostrar até 10 problemas
                info_text += f"  • {issue}\n"
            if len(validation_issues) > 10:
                info_text += f"  ... e mais {len(validation_issues) - 10} problemas\n"
        else:
            info_text += "✅ Estrutura JSON válida!\n"
        
        self.file_info_text.insert(1.0, info_text)
        
        # Conteúdo formatado do JSON
        formatted_content = self.format_menu_content(self.current_json_data)
        self.json_display.insert(1.0, formatted_content)
    
    def format_menu_content(self, data):
        """Formata o conteúdo do menu de forma legível."""
        content = ""
        
        for day, day_data in sorted(data.items()):
            weekday = day_data.get('weekday', 'Dia da semana não especificado')
            content += f"📅 {day} - {weekday}\n"
            content += "=" * 50 + "\n"
            
            menu = day_data.get('menu', [])
            meal_names = ['☕ Café da Manhã', '🍽️ Almoço', '🌙 Jantar']
            
            for i, meal_period in enumerate(menu):
                if i < len(meal_names):
                    content += f"\n{meal_names[i]}:\n"
                else:
                    content += f"\nRefeição {i+1}:\n"
                
                if not meal_period or meal_period == ["Sem refeições disponíveis"]:
                    content += "  ❌ Sem refeições disponíveis\n"
                else:
                    for item in meal_period:
                        content += f"  • {item}\n"
            
            content += "\n" + "-" * 50 + "\n\n"
        
        return content
    
    def validate_json_structure(self, data):
        """Valida a estrutura básica do JSON."""
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
    
    def clear_display(self):
        """Limpa os displays."""
        self.file_info_text.delete(1.0, tk.END)
        self.json_display.delete(1.0, tk.END)
        self.current_json_data = {}
    
    def approve_menu(self):
        """Aprova o cardápio atual."""
        if not self.file_combo.get():
            messagebox.showwarning("Aviso", "Nenhum arquivo selecionado")
            return
        
        file_name = self.file_combo.get()
        response = messagebox.askyesno("Confirmar Aprovação", 
                                     f"Deseja aprovar o cardápio '{file_name}'?\n\n"
                                     "O arquivo será marcado como aprovado.")
        
        if response:
            try:
                # Adicionar metadata de aprovação
                file_path = os.path.join(self.jsons_dir, file_name)
                
                # Adicionar timestamp de aprovação
                for day_data in self.current_json_data.values():
                    day_data['approved'] = True
                    day_data['approved_timestamp'] = int(datetime.now().timestamp())
                
                # Salvar arquivo atualizado
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.current_json_data, f, ensure_ascii=False, indent=2)
                
                # Perguntar se deseja fazer upload para Firebase
                if FIREBASE_AVAILABLE:
                    upload_response = messagebox.askyesno("Upload Firebase", 
                                                         f"Cardápio '{file_name}' aprovado!\n\n"
                                                         "Deseja fazer upload para o Firebase agora?")
                    
                    if upload_response:
                        # Upload em thread separada
                        ru_name = file_name.replace('.json', '')
                        thread = threading.Thread(target=self._upload_single_file, 
                                                 args=(self.current_json_data, ru_name, file_name))
                        thread.daemon = True
                        thread.start()
                        return
                
                messagebox.showinfo("Sucesso", f"Cardápio '{file_name}' aprovado com sucesso!")
                self.load_json_content(file_path)  # Recarregar para mostrar as mudanças
                self.status_var.set(f"Cardápio aprovado: {file_name}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao aprovar cardápio: {e}")
    
    def delete_menu(self):
        """Exclui o cardápio atual."""
        if not self.file_combo.get():
            messagebox.showwarning("Aviso", "Nenhum arquivo selecionado")
            return
        
        file_name = self.file_combo.get()
        response = messagebox.askyesno("Confirmar Exclusão", 
                                     f"Deseja EXCLUIR o cardápio '{file_name}'?\n\n"
                                     "⚠️ Esta ação não pode ser desfeita!")
        
        if response:
            try:
                file_path = os.path.join(self.jsons_dir, file_name)
                os.remove(file_path)
                
                messagebox.showinfo("Sucesso", f"Cardápio '{file_name}' excluído com sucesso!")
                self.load_json_files()  # Recarregar lista
                self.status_var.set(f"Cardápio excluído: {file_name}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao excluir cardápio: {e}")
    
    def regenerate_menu(self):
        """Regenera o cardápio atual."""
        if not self.file_combo.get():
            messagebox.showwarning("Aviso", "Nenhum arquivo selecionado")
            return
        
        file_name = self.file_combo.get()
        ru_name = file_name.replace('.json', '').replace('_', ' ').title()
        
        response = messagebox.askyesno("Confirmar Regeneração", 
                                     f"Deseja obter novamente o cardápio de '{ru_name}'?\n\n"
                                     "O arquivo atual será substituído.")
        
        if response:
            # Executar regeneração em thread separada para não travar a GUI
            thread = threading.Thread(target=self._regenerate_worker, args=(ru_name, file_name))
            thread.daemon = True
            thread.start()
    
    def _regenerate_worker(self, ru_name, file_name):
        """Worker thread para regeneração do cardápio."""
        try:
            self.status_var.set(f"Regenerando cardápio de {ru_name}...")
            
            # Executar o scraper principal
            script_path = os.path.join(os.path.dirname(__file__), "main.py")
            result = subprocess.run([sys.executable, script_path], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.root.after(0, lambda: messagebox.showinfo("Sucesso", 
                    f"Cardápio de '{ru_name}' regenerado com sucesso!"))
                self.root.after(0, self.load_json_files)
                self.root.after(0, lambda: self.status_var.set(f"Cardápio regenerado: {file_name}"))
            else:
                error_msg = result.stderr or result.stdout or "Erro desconhecido"
                self.root.after(0, lambda: messagebox.showerror("Erro", 
                    f"Erro ao regenerar cardápio:\n{error_msg}"))
                self.root.after(0, lambda: self.status_var.set("Erro na regeneração"))
                
        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: messagebox.showerror("Erro", 
                "Timeout na regeneração do cardápio"))
            self.root.after(0, lambda: self.status_var.set("Timeout na regeneração"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro", 
                f"Erro ao regenerar cardápio: {e}"))
            self.root.after(0, lambda: self.status_var.set("Erro na regeneração"))
    
    def validate_all_files(self):
        """Valida todos os arquivos JSON."""
        if not self.json_files:
            messagebox.showwarning("Aviso", "Nenhum arquivo JSON encontrado")
            return
        
        # Executar validação em thread separada
        thread = threading.Thread(target=self._validate_all_worker)
        thread.daemon = True
        thread.start()
    
    def upload_approved_menus(self):
        """Faz upload dos cardápios aprovados para o Firebase."""
        if not FIREBASE_AVAILABLE:
            messagebox.showerror("Erro", 
                "Módulo Firebase não disponível.\nVerifique se o arquivo firebase_uploader.py existe e as dependências estão instaladas.")
            return
        
        if not self.json_files:
            messagebox.showwarning("Aviso", "Nenhum arquivo JSON encontrado")
            return
        
        response = messagebox.askyesno("Confirmar Upload", 
                                     "Deseja fazer upload dos cardápios APROVADOS para o Firebase?\n\n"
                                     "⚠️ Apenas cardápios marcados como 'aprovados' serão enviados.\n"
                                     "Certifique-se de que as variáveis BASE_URL e FIREBASE_KEY estão configuradas.")
        
        if response:
            # Criar barra de progresso
            if not hasattr(self, 'progress_bar'):
                self.progress_bar = ttk.Progressbar(self.root, orient='horizontal', length=400, mode='determinate')
                self.progress_bar.grid(row=2, column=0, columnspan=3, pady=10)
            self.progress_bar['value'] = 0
            self.progress_bar['maximum'] = len(self.json_files)
            self.root.update_idletasks()
            thread = threading.Thread(target=self._upload_worker_with_progress)
            thread.daemon = True
            thread.start()

    def _upload_worker_with_progress(self):
        try:
            self.status_var.set("Testando conexão com Firebase...")
            
            # Testar conexão primeiro
            if not test_firebase_connection():
                self.root.after(0, lambda: messagebox.showerror("Erro", 
                    "Falha na conexão com Firebase.\n\n"
                    "Verifique:\n"
                    "1. Variáveis BASE_URL e FIREBASE_KEY estão configuradas\n"
                    "2. Conexão com internet\n"
                    "3. Credenciais do Firebase"))
                self.root.after(0, lambda: self.status_var.set("Falha na conexão"))
                return
            
            self.status_var.set("Fazendo upload dos cardápios aprovados...")
            
            results = {}
            json_files = list(self.json_files)
            total = len(json_files)
            for idx, json_file in enumerate(json_files, 1):
                file_name = os.path.basename(json_file)
                ru_name = file_name.replace('.json', '')
                self.root.after(0, lambda f=file_name, i=idx, t=total: self.status_var.set(f"Enviando {f} ({i}/{t})..."))
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    menu_data = json.load(f)
                
                # Filtrar apenas dados aprovados
                approved_data = {date_str: day_data for date_str, day_data in menu_data.items() 
                               if day_data.get('approved', False)}
                
                if not approved_data:
                    results[file_name] = False
                    continue
                
                # Fazer upload
                success = upload_menu_to_firebase(approved_data, ru_name)
                results[file_name] = success
                
                self.root.after(0, lambda v=idx: self.progress_bar.config(value=v))
                self.root.update_idletasks()
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            if success_count > 0:
                message = f"Upload concluído!\n\n"
                message += f"✅ Uploads bem-sucedidos: {success_count}\n"
                message += f"❌ Falhas: {total_count - success_count}\n\n"
                
                if total_count - success_count > 0:
                    message += "Arquivos com problemas:\n"
                    for file_name, success in results.items():
                        if not success:
                            message += f"  • {file_name}\n"
                
                self.root.after(0, lambda: messagebox.showinfo("Upload Concluído", message))
                self.root.after(0, lambda: self.status_var.set(f"Upload concluído: {success_count}/{total_count}"))
            else:
                self.root.after(0, lambda: messagebox.showwarning("Upload", 
                    "Nenhum upload foi realizado.\n\n"
                    "Possíveis causas:\n"
                    "• Nenhum cardápio aprovado encontrado\n"
                    "• Falhas de conexão\n"
                    "• Dados inválidos"))
                self.root.after(0, lambda: self.status_var.set("Nenhum upload realizado"))
            
            self.root.after(0, self.load_json_files)
            self.root.after(0, lambda: self.progress_bar.grid_remove())
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro durante upload: {e}"))
            self.root.after(0, lambda: self.status_var.set("Erro no upload"))
            self.root.after(0, lambda: self.progress_bar.grid_remove())
    
    def _upload_single_file(self, menu_data, ru_name, file_name):
        """Worker thread para upload de um arquivo individual."""
        try:
            self.status_var.set(f"Fazendo upload de {file_name}...")
            
            # Filtrar apenas dados aprovados
            approved_data = {date_str: day_data for date_str, day_data in menu_data.items() 
                           if day_data.get('approved', False)}
            
            if not approved_data:
                self.root.after(0, lambda: messagebox.showwarning("Upload", 
                    f"Nenhum cardápio aprovado encontrado em {file_name}"))
                self.root.after(0, lambda: self.status_var.set("Nenhum dado para upload"))
                return
            
            # Fazer upload
            success = upload_menu_to_firebase(approved_data, ru_name)
            
            if success:
                self.root.after(0, lambda: messagebox.showinfo("Upload Concluído", 
                    f"Upload de '{file_name}' realizado com sucesso!\n"
                    f"Enviados {len(approved_data)} dias de cardápio."))
                self.root.after(0, lambda: self.status_var.set(f"Upload concluído: {file_name}"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Erro no Upload", 
                    f"Falha no upload de '{file_name}'.\n"
                    "Verifique a conexão e as credenciais do Firebase."))
                self.root.after(0, lambda: self.status_var.set("Falha no upload"))
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro", 
                f"Erro durante upload de {file_name}: {e}"))
            self.root.after(0, lambda: self.status_var.set("Erro no upload"))
    
    def _validate_all_worker(self):
        """Worker thread para validação de todos os arquivos."""
        try:
            self.status_var.set("Validando todos os arquivos...")
            
            # Usar o validador do projeto
            script_path = os.path.join(os.path.dirname(__file__), "json_validator.py")
            result = subprocess.run([sys.executable, script_path], 
                                  capture_output=True, text=True, timeout=60)
            
            output = result.stdout or result.stderr or "Validação concluída"
            
            self.root.after(0, lambda: messagebox.showinfo("Validação Completa", output))
            self.root.after(0, lambda: self.status_var.set("Validação concluída"))
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro", 
                f"Erro na validação: {e}"))
            self.root.after(0, lambda: self.status_var.set("Erro na validação"))


def main():
    """Função principal para executar a GUI."""
    root = tk.Tk()
    app = MenuReviewGUI(root)
    
    # Configurar comportamento de fechamento
    def on_closing():
        if messagebox.askokcancel("Sair", "Deseja fechar o revisor de cardápios?"):
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
