
import customtkinter as ctk
import tkinter as tk
from tkcalendar import DateEntry # Importar tkcalendar
import yaml
import threading
import logging
import sys
import os
from datetime import datetime, timedelta
from tkinter import messagebox
import main

# Configuración de apariencia
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class RedirectHandler(logging.Handler):
    """
    Handler de logging personalizado.
    - Redirige todo a 'console_box'.
    - Filtra resultados clave a 'results_box'.
    - Detecta [PROGRESS] para 'progress_bar'.
    """
    def __init__(self, console_widget, results_widget, progress_bar=None):
        super().__init__()
        self.console_widget = console_widget
        self.results_widget = results_widget
        self.progress_bar = progress_bar

    def emit(self, record):
        msg = self.format(record)
        
        # 1. Update Progress Bar
        if "[PROGRESS]" in msg and self.progress_bar:
            try:
                parts = msg.split("[PROGRESS]")
                if len(parts) > 1:
                    pct_str = parts[1].strip().replace("%", "")
                    value = float(pct_str) / 100.0
                    def update_prog():
                        self.progress_bar.set(value)
                    self.console_widget.after(0, update_prog)
            except:
                pass

        # 2. Append to Console (Always)
        def append_console():
            self.console_widget.configure(state="normal")
            self.console_widget.insert("end", msg + "\n")
            self.console_widget.see("end")
            self.console_widget.configure(state="disabled")
        self.console_widget.after(0, append_console)
        
        # 3. Filter for Results Box
        # Keywords to identify results
        keywords = ["DEAL ENCONTRADO", "Mejor opción", "Link:", "Google Flights:", "Skyscanner:"]
        if any(k in msg for k in keywords):
            def append_results():
                self.results_widget.configure(state="normal")
                self.results_widget.insert("end", msg + "\n\n") # Extra spacing
                self.results_widget.see("end")
                self.results_widget.configure(state="disabled")
            self.results_widget.after(0, append_results)


class FlightMonitorGUI(ctk.CTk):
    """
    Clase principal de la interfaz gráfica del Monitor de Vuelos.
    """
    CONFIG_PATH = "config.yaml"

    def __init__(self):
        super().__init__()

        self.title("Flight Monitor Launcher - Enhanced")
        self.geometry("1100x750") 

        # Cargar configuración inicial
        self.config_data = self.load_config()

        # Layout principal (2 columnas)
        self.grid_columnconfigure(0, weight=1) # Settings
        self.grid_columnconfigure(1, weight=2) # Results & Logs
        self.grid_rowconfigure(0, weight=1)

        self._create_left_panel()
        self._create_right_panel()
        
        self.setup_logging()

    def load_config(self):
        if not os.path.exists(self.CONFIG_PATH):
            return {}
        try:
            with open(self.CONFIG_PATH, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Error leyendo config: {e}")
            return {}

    def save_config(self, show_msg=False):
        try:
            self.config_data['travel']['origin_country'] = self.entry_origin.get().upper()
            self.config_data['travel']['destination_country'] = self.entry_dest.get().upper()

            today = datetime.now().date()
            start_date = self.date_start.get_date()
            end_date = self.date_end.get_date()
            
            if start_date < today:
                raise ValueError("Start date cannot be in the past.")
            if end_date <= start_date:
                raise ValueError("End date must be after start date.")

            days_start = (start_date - today).days
            days_end = (end_date - today).days

            self.config_data['dates']['travel_window_start'] = days_start
            self.config_data['dates']['travel_window_end'] = days_end

            if 'filters' not in self.config_data: self.config_data['filters'] = {}
            stopover_map = {"Direct Only": 0, "Max 1 Stop": 1, "Max 2 Stops": 2}
            self.config_data['filters']['max_stopovers'] = stopover_map.get(self.option_stops.get(), 2)
            
            if 'baggage' not in self.config_data['filters']: self.config_data['filters']['baggage'] = {}
            self.config_data['filters']['baggage']['require_carry_on'] = bool(self.chk_carryon.get())
            self.config_data['filters']['baggage']['require_checked_bag'] = bool(self.chk_checked.get())

            self.config_data['budget']['max_price'] = int(float(self.slider_budget.get()))
            self.config_data['budget']['currency'] = self.option_currency.get()

            if 'system' not in self.config_data: self.config_data['system'] = {}
            self.config_data['system']['send_summary_if_no_deals'] = bool(self.var_summary.get())

            with open(self.CONFIG_PATH, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False)
            
            if show_msg:
                messagebox.showinfo("Success", "Configuration saved successfully!")
            self.log_message(f"Configuration saved. Range: {start_date} to {end_date}.")

        except ValueError as ve:
            messagebox.showerror("Validation Error", str(ve))
            raise
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
            raise

    def save_config_manual(self):
        self.save_config(show_msg=True)

    def _create_left_panel(self):
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        label_title = ctk.CTkLabel(self.left_frame, text="Configuration", font=ctk.CTkFont(size=20, weight="bold"))
        label_title.pack(pady=10)

        self._create_section_label("Travel Settings")
        self.entry_origin = self._create_input_field("Origin (Code):", self.config_data.get('travel', {}).get('origin_country', ''))
        self.entry_dest = self._create_input_field("Destination (Code):", self.config_data.get('travel', {}).get('destination_country', ''))
        
        dates_cfg = self.config_data.get('dates', {})
        today = datetime.now().date()
        d_start = today + timedelta(days=dates_cfg.get('travel_window_start', 30))
        d_end = today + timedelta(days=dates_cfg.get('travel_window_end', 150))

        ctk.CTkLabel(self.left_frame, text="Start Date:").pack(anchor="w", padx=10)
        self.date_start = DateEntry(self.left_frame, width=12, background='darkblue', foreground='white', borderwidth=2, year=d_start.year, month=d_start.month, day=d_start.day, date_pattern='y-mm-dd')
        self.date_start.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(self.left_frame, text="End Date:").pack(anchor="w", padx=10)
        self.date_end = DateEntry(self.left_frame, width=12, background='darkblue', foreground='white', borderwidth=2, year=d_end.year, month=d_end.month, day=d_end.day, date_pattern='y-mm-dd')
        self.date_end.pack(fill="x", padx=10, pady=(0, 10))

        self._create_section_label("Filters")
        ctk.CTkLabel(self.left_frame, text="Max Stops:").pack(anchor="w", padx=10)
        current_stops = self.config_data.get('filters', {}).get('max_stopovers', 2)
        stop_val = "Max 2 Stops"
        if current_stops == 0: stop_val = "Direct Only"
        elif current_stops == 1: stop_val = "Max 1 Stop"
        
        self.option_stops = ctk.CTkOptionMenu(self.left_frame, values=["Direct Only", "Max 1 Stop", "Max 2 Stops"])
        self.option_stops.set(stop_val)
        self.option_stops.pack(fill="x", padx=10, pady=(0, 10))
        
        bag_cfg = self.config_data.get('filters', {}).get('baggage', {})
        self.chk_carryon = ctk.CTkCheckBox(self.left_frame, text="Carry-on Required", onvalue=True, offvalue=False)
        self.chk_carryon.pack(anchor="w", padx=10, pady=2)
        if bag_cfg.get('require_carry_on', True): self.chk_carryon.select()
        
        self.chk_checked = ctk.CTkCheckBox(self.left_frame, text="Checked Bag Required", onvalue=True, offvalue=False)
        self.chk_checked.pack(anchor="w", padx=10, pady=2)
        if bag_cfg.get('require_checked_bag', False): self.chk_checked.select()

        self._create_section_label("Budget")
        current_budget = self.config_data.get('budget', {}).get('max_price', 20000)
        label_budget = ctk.CTkLabel(self.left_frame, text=f"Max Budget: {current_budget}")
        label_budget.pack(anchor="w", padx=10)
        self.budget_label_ref = label_budget 

        self.slider_budget = ctk.CTkSlider(self.left_frame, from_=5000, to=100000, number_of_steps=190)
        self.slider_budget.set(current_budget)
        self.slider_budget.configure(command=self.update_budget_label)
        self.slider_budget.pack(fill="x", padx=10, pady=(0, 10))

        label_curr = ctk.CTkLabel(self.left_frame, text="Currency:")
        label_curr.pack(anchor="w", padx=10)
        self.option_currency = ctk.CTkOptionMenu(self.left_frame, values=["MXN", "USD", "EUR"])
        self.option_currency.set(self.config_data.get('budget', {}).get('currency', 'MXN'))
        self.option_currency.pack(fill="x", padx=10, pady=(0, 10))

        self.var_summary = ctk.BooleanVar(value=bool(self.config_data.get('system', {}).get('send_summary_if_no_deals', True)))
        self.chk_summary = ctk.CTkCheckBox(self.left_frame, text="Enable Daily Summary", variable=self.var_summary)
        self.chk_summary.pack(pady=(10, 20), padx=10, anchor="w")

        self.btn_save = ctk.CTkButton(self.left_frame, text="Save Configuration", command=self.save_config_manual, fg_color="green")
        self.btn_save.pack(pady=5, padx=10, fill="x")

        self.btn_run = ctk.CTkButton(self.left_frame, text="RUN SEARCH", command=self.run_search_thread, height=40, font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_run.pack(pady=10, padx=10, fill="x")

    def _create_right_panel(self):
        """Crea el panel derecho split (Resultados Top, Logs Bottom)."""
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # 1. Results Section (Top)
        self.right_frame.grid_rowconfigure(0, weight=1) # Results expandable
        self.right_frame.grid_rowconfigure(1, weight=1) # Logs expandable
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.frame_results = ctk.CTkFrame(self.right_frame)
        self.frame_results.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(self.frame_results, text="🔎 Found Deals / Results", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        self.results_box = ctk.CTkTextbox(self.frame_results, state="disabled", font=("Consolas", 12))
        self.results_box.pack(fill="both", expand=True, padx=5, pady=5)

        # 2. Logs Section (Bottom)
        self.frame_logs = ctk.CTkFrame(self.right_frame)
        self.frame_logs.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        ctk.CTkLabel(self.frame_logs, text="📜 System Log", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.progress_label = ctk.CTkLabel(self.frame_logs, text="Search Progress:")
        self.progress_label.pack(pady=(0, 5))
        self.progress_bar = ctk.CTkProgressBar(self.frame_logs)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10))

        self.console_box = ctk.CTkTextbox(self.frame_logs, state="disabled", font=("Consolas", 10))
        self.console_box.pack(fill="both", expand=True, padx=5, pady=5)

    def _create_section_label(self, text):
        l = ctk.CTkLabel(self.left_frame, text=text, font=ctk.CTkFont(size=14, weight="bold"))
        l.pack(anchor="w", padx=10, pady=(15, 5))

    def _create_input_field(self, label_text, default_value):
        l = ctk.CTkLabel(self.left_frame, text=label_text)
        l.pack(anchor="w", padx=10)
        e = ctk.CTkEntry(self.left_frame)
        e.insert(0, str(default_value))
        e.pack(fill="x", padx=10, pady=(0, 10))
        return e

    def update_budget_label(self, value):
        self.budget_label_ref.configure(text=f"Max Budget: {int(value)}")

    def setup_logging(self):
        # Pasar ambos widgets al handler
        handler = RedirectHandler(self.console_box, self.results_box, self.progress_bar)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logging.getLogger().addHandler(handler)

    def log_message(self, msg):
        self.console_box.configure(state="normal")
        self.console_box.insert("end", f"[GUI] {msg}\n")
        self.console_box.see("end")
        self.console_box.configure(state="disabled")

    def run_search_thread(self):
        try:
            self.save_config(show_msg=False)
        except:
            return 
        
        # Limpiar resultados anteriores
        self.results_box.configure(state="normal")
        self.results_box.delete("0.0", "end")
        self.results_box.configure(state="disabled")

        self.btn_run.configure(state="disabled", text="Running...")
        self.log_message("Starting search process...")
        self.progress_bar.set(0)
        
        t = threading.Thread(target=self._run_main_logic)
        t.start()


    def _run_main_logic(self):
        try:
            main.run()
            self.log_message("Process finished successfully.")
        except Exception as e:
            self.log_message(f"CRITICAL ERROR: {e}")
        finally:
            self.after(0, lambda: self.btn_run.configure(state="normal", text="RUN SEARCH"))

if __name__ == "__main__":
    app = FlightMonitorGUI()
    app.mainloop()
