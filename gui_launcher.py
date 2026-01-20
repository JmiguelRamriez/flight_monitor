
import customtkinter as ctk
import tkinter as tk
import yaml
import threading
import logging
import sys
import os
from datetime import datetime, timedelta
from tkinter import messagebox
import main  # Importamos el módulo main existente

# Configuración de apariencia
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class RedirectHandler(logging.Handler):
    """
    Handler de logging personalizado para redirigir la salida a un widget de texto.
    Ahora también detecta [PROGRESS] para actualizar la barra.
    """
    def __init__(self, text_widget, progress_bar=None):
        super().__init__()
        self.text_widget = text_widget
        self.progress_bar = progress_bar

    def emit(self, record):
        msg = self.format(record)
        
        # Check for progress tag
        if "[PROGRESS]" in msg and self.progress_bar:
            try:
                # msg format: ... [PROGRESS] 50%
                parts = msg.split("[PROGRESS]")
                if len(parts) > 1:
                    pct_str = parts[1].strip().replace("%", "")
                    value = float(pct_str) / 100.0
                    
                    # CORRECCIÓN: Actualizar la GUI desde el hilo principal
                    def update_prog():
                        self.progress_bar.set(value)
                    self.text_widget.after(0, update_prog)
            except:
                pass # Ignore parsing errors

        def append():
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", msg + "\n")
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")
        # Asegurarse de actualizar la UI en el hilo principal
        self.text_widget.after(0, append)

class FlightMonitorGUI(ctk.CTk):
    """
    Clase principal de la interfaz gráfica del Monitor de Vuelos.
    """
    CONFIG_PATH = "config.yaml"

    def __init__(self):
        super().__init__()

        self.title("Flight Monitor Launcher")
        self.geometry("900x600")

        # Cargar configuración inicial
        self.config_data = self.load_config()

        # Layout principal (2 columnas)
        self.grid_columnconfigure(0, weight=1) # Panel Izquierdo (Settings)
        self.grid_columnconfigure(1, weight=2) # Panel Derecho (Console)
        self.grid_rowconfigure(0, weight=1)

        self._create_left_panel()
        self._create_right_panel()
        
        # Redirigir logs al iniciar
        self.setup_logging()

    def load_config(self):
        """Lee el archivo config.yaml y retorna el diccionario."""
        if not os.path.exists(self.CONFIG_PATH):
            messagebox.showerror("Error", f"No se encontró {self.CONFIG_PATH}")
            return {}
        try:
            with open(self.CONFIG_PATH, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Error leyendo config: {e}")
            return {}

    def save_config(self):
        """Guarda los valores de la UI de vuelta a config.yaml."""
        try:
            # 1. Actualizar Travel Settings
            self.config_data['travel']['origin_country'] = self.entry_origin.get().upper()
            self.config_data['travel']['destination_country'] = self.entry_dest.get().upper()

            # 2. Actualizar Fechas (Conversión de Fechas a Días Relativos)
            start_str = self.entry_start_date.get()
            end_str = self.entry_end_date.get()
            
            today = datetime.now().date()
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            
            if start_date < today:
                raise ValueError("Start date cannot be in the past.")
            if end_date <= start_date:
                raise ValueError("End date must be after start date.")

            days_start = (start_date - today).days
            days_end = (end_date - today).days

            self.config_data['dates']['travel_window_start'] = days_start
            self.config_data['dates']['travel_window_end'] = days_end

            # 3. Actualizar Presupuesto
            self.config_data['budget']['max_price'] = int(float(self.slider_budget.get()))
            self.config_data['budget']['currency'] = self.option_currency.get()

            # Escribir archivo
            with open(self.CONFIG_PATH, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False)
            
            messagebox.showinfo("Success", "Configuration saved successfully!")
            self.log_message(f"Configuration saved. Travel window: +{days_start} to +{days_end} days from today.")

        except ValueError as ve:
            messagebox.showerror("Validation Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")

    def _create_left_panel(self):
        """Crea el panel de configuración (Izquierda)."""
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Título
        label_title = ctk.CTkLabel(self.left_frame, text="Configuration", font=ctk.CTkFont(size=20, weight="bold"))
        label_title.pack(pady=10)

        # Sección Travel
        self._create_section_label("Travel Settings")
        
        self.entry_origin = self._create_input_field("Origin (Code):", self.config_data.get('travel', {}).get('origin_country', ''))
        self.entry_dest = self._create_input_field("Destination (Code):", self.config_data.get('travel', {}).get('destination_country', ''))
        
        # Conversión inversa: Días Relativos a Fechas para mostrar en UI
        dates_cfg = self.config_data.get('dates', {})
        today = datetime.now()
        start_days = dates_cfg.get('travel_window_start', 30)
        end_days = dates_cfg.get('travel_window_end', 150)
        
        default_start = (today + timedelta(days=start_days)).strftime("%Y-%m-%d")
        default_end = (today + timedelta(days=end_days)).strftime("%Y-%m-%d")

        self.entry_start_date = self._create_input_field("Start Date (YYYY-MM-DD):", default_start)
        self.entry_end_date = self._create_input_field("End Date (YYYY-MM-DD):", default_end)

        # Sección Budget
        self._create_section_label("Budget")

        # Slider de presupuesto
        current_budget = self.config_data.get('budget', {}).get('max_price', 20000)
        
        label_budget = ctk.CTkLabel(self.left_frame, text=f"Max Budget: {current_budget}")
        label_budget.pack(anchor="w", padx=10)
        self.budget_label_ref = label_budget # Guardar referencia para actualizar

        self.slider_budget = ctk.CTkSlider(self.left_frame, from_=5000, to=100000, number_of_steps=190)
        self.slider_budget.set(current_budget)
        self.slider_budget.configure(command=self.update_budget_label)
        self.slider_budget.pack(fill="x", padx=10, pady=(0, 10))

        # Currency Dropdown
        label_curr = ctk.CTkLabel(self.left_frame, text="Currency:")
        label_curr.pack(anchor="w", padx=10)
        self.option_currency = ctk.CTkOptionMenu(self.left_frame, values=["MXN", "USD", "EUR"])
        self.option_currency.set(self.config_data.get('budget', {}).get('currency', 'MXN'))
        self.option_currency.pack(fill="x", padx=10, pady=(0, 10))

        # Summary Toggle
        self.var_summary = ctk.BooleanVar(value=bool(self.config_data.get('system', {}).get('send_summary_if_no_deals', True)))
        self.chk_summary = ctk.CTkCheckBox(self.left_frame, text="Enable Daily Summary", variable=self.var_summary)
        self.chk_summary.pack(pady=(10, 20), padx=10, anchor="w")

        # Botones de Acción
        self.btn_save = ctk.CTkButton(self.left_frame, text="Save Configuration", command=self.save_config_manual, fg_color="green")
        self.btn_save.pack(pady=5, padx=10, fill="x")

        self.btn_run = ctk.CTkButton(self.left_frame, text="RUN SEARCH", command=self.run_search_thread, height=40, font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_run.pack(pady=10, padx=10, fill="x")

    def _create_right_panel(self):
        """Crea el panel de logs (Derecha)."""
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        label_log = ctk.CTkLabel(self.right_frame, text="Live System Log", font=ctk.CTkFont(size=16, weight="bold"))
        label_log.pack(pady=10)
        
        # Progress Bar added here
        self.progress_label = ctk.CTkLabel(self.right_frame, text="Search Progress:")
        self.progress_label.pack(pady=(0, 5))
        self.progress_bar = ctk.CTkProgressBar(self.right_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10))

        self.console_box = ctk.CTkTextbox(self.right_frame, state="disabled", font=("Consolas", 12))
        self.console_box.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_section_label(self, text):
        """Helper para títulos de sección."""
        l = ctk.CTkLabel(self.left_frame, text=text, font=ctk.CTkFont(size=14, weight="bold"))
        l.pack(anchor="w", padx=10, pady=(15, 5))

    def _create_input_field(self, label_text, default_value):
        """Helper para crear label + entry."""
        l = ctk.CTkLabel(self.left_frame, text=label_text)
        l.pack(anchor="w", padx=10)
        e = ctk.CTkEntry(self.left_frame)
        e.insert(0, str(default_value))
        e.pack(fill="x", padx=10, pady=(0, 10))
        return e

    def update_budget_label(self, value):
        """Actualiza el texto del label del slider."""
        self.budget_label_ref.configure(text=f"Max Budget: {int(value)}")

    def setup_logging(self):
        """Configura el redireccionamiento de logs."""
        handler = RedirectHandler(self.console_box)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # Conectar SOLO al logger root. Los demás loggers ("Main", "amadeus_client") 
        # propagan sus mensajes automáticamente al root, donde este handler los capturará.
        # Esto evita que se muestren duplicados en la consola.
        logging.getLogger().addHandler(handler)

    def log_message(self, msg):
        """Escribe un mensaje manual en la consola."""
        self.console_box.configure(state="normal")
        self.console_box.insert("end", f"[GUI] {msg}\n")
        self.console_box.see("end")
        self.console_box.configure(state="disabled")

    def save_config_manual(self):
        self.save_config(show_msg=True)

    def save_config(self, show_msg=False):
        """Guarda los valores de la UI de vuelta a config.yaml."""
        try:
            # 1. Actualizar Travel Settings
            self.config_data['travel']['origin_country'] = self.entry_origin.get().upper()
            self.config_data['travel']['destination_country'] = self.entry_dest.get().upper()

            # 2. Actualizar Fechas (Conversión de Fechas a Días Relativos)
            start_str = self.entry_start_date.get()
            end_str = self.entry_end_date.get()
            
            today = datetime.now().date()
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            
            if start_date < today:
                raise ValueError("Start date cannot be in the past.")
            if end_date <= start_date:
                raise ValueError("End date must be after start date.")

            days_start = (start_date - today).days
            days_end = (end_date - today).days

            self.config_data['dates']['travel_window_start'] = days_start
            self.config_data['dates']['travel_window_end'] = days_end

            # 3. Actualizar Presupuesto
            self.config_data['budget']['max_price'] = int(float(self.slider_budget.get()))
            self.config_data['budget']['currency'] = self.option_currency.get()

            # 4. Actualizar System Settings
            if 'system' not in self.config_data: self.config_data['system'] = {}
            self.config_data['system']['send_summary_if_no_deals'] = bool(self.var_summary.get())

            # Escribir archivo
            with open(self.CONFIG_PATH, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False)
            
            if show_msg:
                messagebox.showinfo("Success", "Configuration saved successfully!")
            self.log_message(f"Configuration saved. Range: {start_str} to {end_str} (+{days_start}d to +{days_end}d).")

        except ValueError as ve:
            messagebox.showerror("Validation Error", str(ve))
            raise
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
            raise

    def run_search_thread(self):
        """Inicia el proceso de búsqueda en un hilo separado."""
        # Auto-Guardar antes de correr para asegurar que se usan las fechas de la UI
        try:
            self.save_config(show_msg=False)
        except:
            return # Si falla validación, no correr

        self.btn_run.configure(state="disabled", text="Running...")
        self.log_message("Starting search process...")
        
        t = threading.Thread(target=self._run_main_logic)
        t.start()

    def _run_main_logic(self):
        try:
            # Ejecutar la función main del script del backend
            main.run()
            self.log_message("Process finished successfully.")
        except Exception as e:
            self.log_message(f"CRITICAL ERROR: {e}")
        finally:
            self.after(0, lambda: self.btn_run.configure(state="normal", text="RUN SEARCH"))

if __name__ == "__main__":
    app = FlightMonitorGUI()
    app.mainloop()
