
import customtkinter as ctk
import tkinter as tk
from tkcalendar import DateEntry # Importar tkcalendar
import yaml
import threading
import logging
import sys
import os
import random # Importar random
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
    - Detecta [PROGRESS] para 'progress_bar'.
    """
    def __init__(self, console_widget, progress_bar=None):
        super().__init__()
        self.console_widget = console_widget
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

# ... (omitted code) ...

    def setup_logging(self):
        # Pasar solo console_box y progress_bar al handler
        handler = RedirectHandler(self.console_box, self.progress_bar)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logging.getLogger().addHandler(handler)


class DealResultsWindow(ctk.CTkToplevel):
    def __init__(self, deals):
        super().__init__()
        self.title("Offers Found! ✈️")
        self.geometry("550x650") 
        self.attributes("-topmost", True)
        
        # Header Banner
        header = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="✨ Result Deals ✨", font=ctk.CTkFont(size=24, weight="bold"), text_color="#facc15").pack(pady=15)
        
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        deals.sort(key=lambda x: x.get("price", 0)) # Sort by price

        for i, deal in enumerate(deals):
            is_best = (i == 0)
            self._create_deal_card(scroll, deal, is_best)
            
    def _create_deal_card(self, parent, deal, is_best):
        # Card container with border
        border_color = "#eab308" if is_best else "#4b5563"
        border_width = 2 if is_best else 1
        bg_color = "#1e293b"
        
        card = ctk.CTkFrame(parent, fg_color=bg_color, border_color=border_color, border_width=border_width)
        card.pack(fill="x", pady=8, padx=5)
        
        # Best Deal Badge
        if is_best:
            badge = ctk.CTkLabel(card, text="⭐ BEST DEAL", fg_color="#eab308", text_color="black", corner_radius=6, font=ctk.CTkFont(size=10, weight="bold"))
            badge.pack(anchor="e", padx=10, pady=(5,0))

        # Header: Route
        route_str = f"{deal.get('cityCodeFrom')} ✈️ {deal.get('cityCodeTo')}"
        ctk.CTkLabel(card, text=route_str, font=ctk.CTkFont(size=18, weight="bold"), text_color="white").pack(anchor="w", padx=15, pady=(5,0))
        
        # Grid Info
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=5)
        
        price = deal.get("price")
        
        # Dates
        ts_dep = deal.get("dTime")
        ts_ret = deal.get("aTime")
        
        fmt = '%d %b'
        date_dep_str = datetime.fromtimestamp(ts_dep).strftime(fmt) if ts_dep else "N/A"
        date_ret_str = datetime.fromtimestamp(ts_ret).strftime(fmt) if ts_ret else "N/A"
        
        # Price (Large)
        ctk.CTkLabel(info_frame, text=f"${price:,}", font=ctk.CTkFont(size=24, weight="bold"), text_color="#4ade80").pack(side="left")
        
        # Date & Airline (Right)
        right_info = ctk.CTkFrame(info_frame, fg_color="transparent")
        right_info.pack(side="right")
        
        # Display Dates (English)
        ctk.CTkLabel(right_info, text=f"DEPART: {date_dep_str}", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="e")
        if ts_ret:
             ctk.CTkLabel(right_info, text=f"RETURN: {date_ret_str}", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="e")
        
        airlines = ", ".join(deal.get("airlines", []))[:20] # Truncate if long
        ctk.CTkLabel(right_info, text=f"🛩️ {airlines}", font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="e")

        # Button Logic: PRIORITIZE SKYSCANNER (backup_link)
        link = deal.get("backup_link") or deal.get("deep_link")
        
        if not link and deal.get("cityCodeFrom") and deal.get("cityCodeTo") and deal.get("dTime"):
            # Fallback: Regenerate Skyscanner Link (YYMMDD format)
            try:
                origin = deal["cityCodeFrom"].lower()
                dest = deal["cityCodeTo"].lower()
                dep_dt = datetime.fromtimestamp(deal["dTime"])
                sky_dep = dep_dt.strftime("%y%m%d")
                sky_ret = ""
                
                if deal.get("aTime") and deal["aTime"] > deal["dTime"]:
                     ret_dt = datetime.fromtimestamp(deal["aTime"])
                     if ret_dt > dep_dt:
                        sky_ret = ret_dt.strftime("%y%m%d")
                
                link = f"https://www.skyscanner.com.mx/transport/vuelos/{origin}/{dest}/{sky_dep}/{sky_ret}"
            except Exception:
                link = None

        if link:
             btn_text = "🔗 View Deal (Skyscanner)"
             state = "normal"
             fg_color = "#2563eb"
             hover_color = "#1d4ed8"
        else:
             btn_text = "Link Not Available"
             state = "disabled"
             fg_color = "#4b5563"
             hover_color = "#4b5563"
             
        btn = ctk.CTkButton(card, text=btn_text, fg_color=fg_color, hover_color=hover_color, 
                            font=ctk.CTkFont(weight="bold"),
                            state=state,
                            command=lambda l=link: self._open_link(l) if l else None)
        btn.pack(fill="x", padx=15, pady=(10, 15))
            
    def _open_link(self, url):
        import webbrowser
        webbrowser.open(url)

class FlightMonitorGUI(ctk.CTk):
    """
    Main GUI Class.
    """
    CONFIG_PATH = "config.yaml"

    LOCATIONS = {
        "Mexico": ["Whole Country (MX)", "Mexico City (MEX)", "Cancun (CUN)", "Guadalajara (GDL)", "Monterrey (MTY)", "Tijuana (TIJ)"],
        "United States": ["Whole Country (US)", "New York (JFK)", "Miami (MIA)", "Los Angeles (LAX)", "Las Vegas (LAS)", "Orlando (MCO)"],
        "Colombia": ["Whole Country (CO)", "Bogota (BOG)", "Medellin (MDE)", "Cartagena (CTG)"],
        "Argentina": ["Whole Country (AR)", "Buenos Aires (EZE)"],
        "Brazil": ["Whole Country (BR)", "Sao Paulo (GRU)", "Rio de Janeiro (GIG)"],
        "Peru": ["Whole Country (PE)", "Lima (LIM)"],
        "Chile": ["Whole Country (CL)", "Santiago (SCL)"],
        "Ecuador": ["Whole Country (EC)", "Quito (UIO)", "Guayaquil (GYE)"],
        "Costa Rica": ["Whole Country (CR)", "San Jose (SJO)"],
        "Panama": ["Whole Country (PA)", "Panama City (PTY)"],
        "Spain": ["Whole Country (ES)", "Madrid (MAD)", "Barcelona (BCN)"],
        "France": ["Whole Country (FR)", "Paris (CDG)"],
        "Italy": ["Whole Country (IT)", "Rome (FCO)"],
        "Germany": ["Whole Country (DE)", "Frankfurt (FRA)"],
        "United Kingdom": ["Whole Country (GB)", "London (LHR)"],
        "Japan": ["Whole Country (JP)", "Tokyo (HND)"],
        "Canada": ["Whole Country (CA)", "Toronto (YYZ)", "Vancouver (YVR)"],
        "Custom / Other": []
    }

    def __init__(self):
        super().__init__()

        self.title("Flight Monitor Launcher - Enhanced")
        self.geometry("1100x750") 

        # Load initial config
        self.config_data = self.load_config()

        # Main Layout
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
            messagebox.showerror("Error", f"Error reading config: {e}")
            return {}

    def _extract_code(self, raw_value):
        """Extracts code between parentheses."""
        if "(" in raw_value and raw_value.endswith(")"):
            try:
                start = raw_value.rfind("(") + 1
                end = raw_value.rfind(")")
                return raw_value[start:end].strip().upper()
            except:
                pass
        return raw_value.strip().upper()

    def save_config(self, show_msg=False):
        try:
            origin_raw = self.combo_origin.get()
            dest_raw = self.combo_dest.get()
            
            self.config_data['travel']['origin_country'] = self._extract_code(origin_raw)
            self.config_data['travel']['destination_country'] = self._extract_code(dest_raw)

            today = datetime.now().date()
            start_date_obj = self.date_start.get_date()
            end_date_obj = self.date_end.get_date()
            
            if start_date_obj < today:
                raise ValueError("Departure date cannot be in the past.")
            if end_date_obj <= start_date_obj:
                raise ValueError("Return date must be after departure date.")

            # SAVE SPECIFIC DATES LOGIC
            self.config_data['dates']['exact_dates_mode'] = True
            self.config_data['dates']['specific_start'] = start_date_obj.strftime("%Y-%m-%d")
            self.config_data['dates']['specific_end'] = end_date_obj.strftime("%Y-%m-%d")

            # Fallback for old logic (window) - Keeping it consistent just in case
            days_start = (start_date_obj - today).days
            days_end = (end_date_obj - today).days
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
            self.log_message(f"Configuration saved. Origin: {self.config_data['travel']['origin_country']}, Dest: {self.config_data['travel']['destination_country']}")
            self.log_message(f"Searching specific dates: {self.config_data['dates']['specific_start']} to {self.config_data['dates']['specific_end']}")

        except ValueError as ve:
            messagebox.showerror("Validation Error", str(ve))
            raise
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
            raise

    def save_config_manual(self):
        self.save_config(show_msg=True)

    def _create_left_panel(self):
        self.left_frame = ctk.CTkScrollableFrame(self, label_text="Configuration", label_font=ctk.CTkFont(size=20, weight="bold"))
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self._create_section_label("Travel Settings")
        
        # Origin (Hierarchical)
        curr_origin = self.config_data.get('travel', {}).get('origin_country', '')
        self.combo_origin = self._create_location_selector("Origin:", curr_origin)
        
        # Destination (Hierarchical)
        curr_dest = self.config_data.get('travel', {}).get('destination_country', '')
        self.combo_dest = self._create_location_selector("Destination:", curr_dest)
        
        # Load saved dates if available, else default
        dates_cfg = self.config_data.get('dates', {})
        today = datetime.now().date()
        
        # Default to specific dates if exist
        if dates_cfg.get('specific_start'):
             try:
                 d_start = datetime.strptime(dates_cfg['specific_start'], "%Y-%m-%d").date()
             except:
                 d_start = today + timedelta(days=30)
        else:
            d_start = today + timedelta(days=30)

        if dates_cfg.get('specific_end'):
             try:
                 d_end = datetime.strptime(dates_cfg['specific_end'], "%Y-%m-%d").date()
             except:
                 d_end = today + timedelta(days=37)
        else:
            d_end = today + timedelta(days=37)


        ctk.CTkLabel(self.left_frame, text="Departure Date:").pack(anchor="w", padx=10)
        self.date_start = DateEntry(self.left_frame, width=12, background='darkblue', foreground='white', borderwidth=2, year=d_start.year, month=d_start.month, day=d_start.day, date_pattern='y-mm-dd')
        self.date_start.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(self.left_frame, text="Return Date:").pack(anchor="w", padx=10)
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
        
        ctk.CTkLabel(self.frame_results, text="🔎 Search Status & Animation", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        # Canvas para animación (Sky Blue-ish dark background)
        self.anim_canvas = tk.Canvas(self.frame_results, bg="#1e293b", highlightthickness=0)
        self.anim_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.clouds = []
        # Create initial clouds at random positions
        for _ in range(4):
            x = random.randint(0, 400)
            y = random.randint(10, 100)
            cloud_id = self.anim_canvas.create_text(x, y, text="☁️", font=("Arial", random.randint(30, 50)), fill="#64748b")
            speed = random.uniform(1.0, 3.0)
            self.clouds.append({"id": cloud_id, "speed": speed})

        # Plane
        self.plane_id = self.anim_canvas.create_text(-60, 140, text="✈️", font=("Arial", 64), fill="white")
        self.anim_running = False
        
        # Status Text centered
        self.status_text = self.anim_canvas.create_text(250, 250, text="Ready for takeoff...", font=("Arial", 14, "italic"), fill="#94a3b8")

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

    def _start_animation(self):
        self.anim_running = True
        self.anim_canvas.itemconfig(self.status_text, text="Searching active... Have a nice flight! 🌎", fill="#38bdf8")
        self._animate_loop()

    def _stop_animation(self):
        self.anim_running = False
        self.anim_canvas.itemconfig(self.status_text, text="Arrived! Check the results window.", fill="#4ade80")

    def _animate_loop(self):
        if not self.anim_running:
            return
            
        w = self.anim_canvas.winfo_width()
        
        # 1. Move Clouds (Parallax - move left)
        for cloud in self.clouds:
            self.anim_canvas.move(cloud["id"], -cloud["speed"], 0)
            pos = self.anim_canvas.coords(cloud["id"])
            if pos[0] < -50: # Reset to right side
                new_y = random.randint(10, 120)
                self.anim_canvas.coords(cloud["id"], w + 50, new_y)
                
        # 2. Move Plane (Right)
        self.anim_canvas.move(self.plane_id, 6, 0)
        plane_pos = self.anim_canvas.coords(self.plane_id)
        if plane_pos[0] > w + 60:
             self.anim_canvas.coords(self.plane_id, -60, 140)
             
        self.after(30, self._animate_loop)

    def _create_section_label(self, text):
        l = ctk.CTkLabel(self.left_frame, text=text, font=ctk.CTkFont(size=14, weight="bold"))
        l.pack(anchor="w", padx=10, pady=(15, 5))

    def _create_location_selector(self, label_text, current_code):
        """
        Crea un selector jerárquico: País -> Ciudad.
        """
        wrapper = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        wrapper.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(wrapper, text=label_text, font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        
        # Determine initial Country and City display values
        initial_country = "Custom / Other"
        initial_city_val = current_code
        
        # Reverse lookup logic
        found = False
        if current_code:
            for country, cities in self.LOCATIONS.items():
                for city_str in cities:
                    if f"({current_code})" in city_str:
                        initial_country = country
                        initial_city_val = city_str
                        found = True
                        break
                if found: break
        
        # Country Combobox
        # Frame for country row
        f_country = ctk.CTkFrame(wrapper, fg_color="transparent")
        f_country.pack(fill="x", pady=2)
        ctk.CTkLabel(f_country, text="Country:", width=60).pack(side="left")
        
        combo_country = ctk.CTkComboBox(f_country, values=list(self.LOCATIONS.keys()))
        combo_country.set(initial_country)
        combo_country.pack(side="left", fill="x", expand=True)

        # City Combobox
        f_city = ctk.CTkFrame(wrapper, fg_color="transparent")
        f_city.pack(fill="x", pady=2)
        ctk.CTkLabel(f_city, text="City:", width=60).pack(side="left")
        
        combo_city = ctk.CTkComboBox(f_city, values=self.LOCATIONS.get(initial_country, []))
        combo_city.set(initial_city_val)
        combo_city.pack(side="left", fill="x", expand=True)
        
        # Callback to update cities
        def on_country_change(choice):
            cities = self.LOCATIONS.get(choice, [])
            combo_city.configure(values=cities)
            if cities:
                combo_city.set(cities[0])
            else:
                combo_city.set("")
                
        combo_country.configure(command=on_country_change)
        
        return combo_city

    def update_budget_label(self, value):
        self.budget_label_ref.configure(text=f"Max Budget: {int(value)}")

    def setup_logging(self):
        # Pasar solo console_box y progress_bar al handler
        handler = RedirectHandler(self.console_box, self.progress_bar)
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
        
        self.btn_run.configure(state="disabled", text="Running...")
        self.log_message("Starting search process...")
        self.progress_bar.set(0)
        
        self._start_animation() # START
        
        t = threading.Thread(target=self._run_main_logic)
        t.start()


    def _run_main_logic(self):
        try:
            results = main.run()
            self.log_message("Process finished successfully.")
            
            # Show results window if deals found OR fallback to best alternative
            deals_to_show = results.get("deals", [])
            
            if not deals_to_show and results.get("best_alternative"):
                # Si no hay "Deals" (ofertas locas), mostramos la mejor opción encontrada de todas formas
                best = results["best_alternative"]
                # Le agregamos una marquita falsa o nota de que es la sugerencia
                deals_to_show = [best]
                
            if deals_to_show:
                 self.after(0, lambda: self.show_results_window(deals_to_show))

        except Exception as e:
            self.log_message(f"CRITICAL ERROR: {e}")
        finally:
            self._stop_animation() # STOP
            self.after(0, lambda: self.btn_run.configure(state="normal", text="RUN SEARCH"))

    def show_results_window(self, deals):
        if not deals: return
        DealResultsWindow(deals)

if __name__ == "__main__":
    app = FlightMonitorGUI()
    app.mainloop()
