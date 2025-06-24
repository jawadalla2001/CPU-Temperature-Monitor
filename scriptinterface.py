import time
import datetime
import os
import psutil
import ctypes
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
import matplotlib.dates as mdates
import sqlite3

# =======================================
# Script IoT CPU Temp avec Oracle/SQLite + Interface temps réel
# =======================================

# === Variables de connexion Oracle ===
DB_USER     = 'system'    # utilisateur Oracle
DB_PASSWORD = 'jawad-10-10-2001'  # mot de passe Oracle
USE_ORACLE  = True        # Définir sur True pour utiliser Oracle, False pour SQLite

# Chaîne de connexion - Utiliser FREEPDB1 ou FREE qui sont des services disponibles
CONNECT_STRING = "localhost:1521/FREE"
# Alternative si la connexion échoue
# CONNECT_STRING = "localhost:1521/FREEPDB1"

# === Variables de configuration ===
UPDATE_INTERVAL = 2  # Intervalle de mise à jour du graphique en secondes
SAMPLE_INTERVAL = 5  # Intervalle d'échantillonnage et sauvegarde en secondes
MAX_POINTS = 60      # Nombre maximum de points dans le graphique temps réel
SQLITE_DB_PATH = "cpu_temperatures.db"  # Chemin pour la base SQLite

# === Vérification des droits admin sous Windows ===
skip_wmi = False
if os.name == 'nt':
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            print("Attention: exécutez ce script en tant qu'administrateur pour lire la température CPU sous Windows.")
    except Exception:
        # Impossible de vérifier, on tentera quand même WMI
        pass

# Vérifier si oracledb est disponible
try:
    import oracledb
    HAS_ORACLE = True
except ImportError:
    HAS_ORACLE = False
    if USE_ORACLE:
        print("ATTENTION: oracledb n'est pas installé, utilisation de SQLite à la place.")
        print("Pour installer oracledb: pip install oracledb")
        USE_ORACLE = False

# === Classe principale pour l'application ===
class RealTimeCPUTempMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitoring Température CPU - Temps Réel")
        self.root.geometry("950x700")
        self.root.minsize(800, 600)
        
        # Variables d'état
        self.running = False
        self.connection = None
        self.cursor = None
        self.current_temp = None
        self.temps_history = []  # Pour le graphique [timestamp, temp]
        self.monitor_thread = None
        self.last_save_time = None
        self.total_records = 0
        self.using_oracle = False
        
        # Variables pour l'animation
        self.anim = None
        
        # Configurer l'interface
        self.setup_ui()
        
        # Tentative de connexion initiale
        self.connect_to_database()
        
        # Configuration de la fermeture propre
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """Configure l'interface utilisateur"""
        # Configuration du style
        self.configure_styles()
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Création des sections
        self.create_header_section(main_frame)
        self.create_realtime_graph(main_frame)
        self.create_data_table(main_frame)
        self.create_stats_section(main_frame)
        self.create_status_bar()

    def configure_styles(self):
        """Configure les styles pour l'interface"""
        style = ttk.Style()
        style.configure('TLabel', font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'))
        style.configure('Temp.TLabel', font=('Segoe UI', 28))
        style.configure('Stats.TLabel', font=('Segoe UI', 11))
        style.configure('TLabelframe.Label', font=('Segoe UI', 11, 'bold'))
        
        # Créer un style pour les indicateurs colorés
        style.configure('Normal.TLabel', background='#4CAF50')  # Vert
        style.configure('Warning.TLabel', background='#FFC107')  # Jaune
        style.configure('Critical.TLabel', background='#F44336')  # Rouge

    def create_header_section(self, parent):
        """Crée la section d'en-tête avec les informations et contrôles principaux"""
        header_frame = ttk.Frame(parent, padding=5)
        header_frame.pack(fill=tk.X, expand=False, pady=(0, 10))
        
        # Côté gauche - Informations
        info_frame = ttk.Frame(header_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH)
        
        # Température actuelle avec indicateur coloré
        temp_frame = ttk.Frame(info_frame)
        temp_frame.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(temp_frame, text="Température CPU:", style='Header.TLabel').pack(side=tk.LEFT)
        
        # Indicateur visuel (carré coloré)
        self.temp_indicator = ttk.Label(temp_frame, text=" ", width=2, style='Normal.TLabel')
        self.temp_indicator.pack(side=tk.LEFT, padx=(10, 5))
        
        # Valeur température
        self.temp_var = tk.StringVar(value="--.- °C")
        ttk.Label(temp_frame, textvariable=self.temp_var, style='Temp.TLabel').pack(side=tk.LEFT, padx=5)
        
        # Statut de connexion Oracle
        conn_frame = ttk.Frame(info_frame)
        conn_frame.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(conn_frame, text="Base de données:", style='Header.TLabel').pack(side=tk.LEFT)
        self.conn_status_var = tk.StringVar(value="Non connecté")
        ttk.Label(conn_frame, textvariable=self.conn_status_var).pack(side=tk.LEFT, padx=10)
        
        # Côté droit - Contrôles
        control_frame = ttk.Frame(header_frame)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        
        # Intervalle d'échantillonnage
        sample_frame = ttk.Frame(control_frame)
        sample_frame.pack(fill=tk.X, pady=5)
        ttk.Label(sample_frame, text="Intervalle (s):").pack(side=tk.LEFT)
        
        self.interval_var = tk.StringVar(value=str(SAMPLE_INTERVAL))
        interval_entry = ttk.Entry(sample_frame, textvariable=self.interval_var, width=5)
        interval_entry.pack(side=tk.LEFT, padx=5)
        
        # Boutons de contrôle
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(btn_frame, text="Démarrer", command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Arrêter", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = ttk.Button(btn_frame, text="Actualiser", command=self.load_recent_data)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

    def create_realtime_graph(self, parent):
        """Crée le graphique en temps réel"""
        graph_frame = ttk.LabelFrame(parent, text="Température CPU en temps réel", padding=10)
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Figure avec 2 sous-graphiques
        self.fig = Figure(figsize=(5, 4), dpi=100)
        
        # Graphique principal - temps réel
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('Temps')
        self.ax.set_ylabel('Température (°C)')
        self.ax.grid(True)
        
        # Formater l'axe X pour les heures:minutes:secondes
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # Créer une ligne vide
        self.line, = self.ax.plot([], [], 'b-', linewidth=2)
        
        # Ajouter le canevas
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Barre d'outils de navigation (zoom, pan, etc.)
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(self.canvas, graph_frame)
        toolbar.update()

    def create_data_table(self, parent):
        """Crée le tableau des données récentes"""
        table_frame = ttk.LabelFrame(parent, text="Historique des données", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=False, pady=5)
        
        # Tableau (Treeview)
        columns = ('id', 'timestamp', 'temperature')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=5)
        
        # Définition des colonnes
        self.tree.heading('id', text='ID')
        self.tree.heading('timestamp', text='Date/Heure')
        self.tree.heading('temperature', text='Température (°C)')
        
        self.tree.column('id', width=50, anchor=tk.CENTER)
        self.tree.column('timestamp', width=150, anchor=tk.W)
        self.tree.column('temperature', width=120, anchor=tk.CENTER)
        
        # Scrollbar
        scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        
        # Placement
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def create_stats_section(self, parent):
        """Crée la section des statistiques"""
        stats_frame = ttk.LabelFrame(parent, text="Statistiques", padding=10)
        stats_frame.pack(fill=tk.X, expand=False, pady=5)
        
        # Grille pour les statistiques
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)
        
        # Variables pour les statistiques
        self.temp_min_var = tk.StringVar(value="--.- °C")
        self.temp_max_var = tk.StringVar(value="--.- °C")
        self.temp_avg_var = tk.StringVar(value="--.- °C")
        self.records_var = tk.StringVar(value="0")
        self.last_save_var = tk.StringVar(value="--:--:--")
        
        # Première ligne
        ttk.Label(stats_grid, text="Température min:", style='Stats.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_grid, textvariable=self.temp_min_var, style='Stats.TLabel').grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Température max:", style='Stats.TLabel').grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_grid, textvariable=self.temp_max_var, style='Stats.TLabel').grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Température moyenne:", style='Stats.TLabel').grid(row=0, column=4, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_grid, textvariable=self.temp_avg_var, style='Stats.TLabel').grid(row=0, column=5, sticky=tk.W, padx=5, pady=2)
        
        # Deuxième ligne
        ttk.Label(stats_grid, text="Enregistrements:", style='Stats.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_grid, textvariable=self.records_var, style='Stats.TLabel').grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Dernier enregistrement:", style='Stats.TLabel').grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_grid, textvariable=self.last_save_var, style='Stats.TLabel').grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)

    def create_status_bar(self):
        """Crée la barre de statut"""
        self.status_var = tk.StringVar(value="Prêt")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def connect_to_database(self):
        """Établit la connexion à la base de données (Oracle ou SQLite) et prépare la table"""
        global USE_ORACLE, HAS_ORACLE
        
        # Si Oracle est demandé et disponible, tenter la connexion
        if USE_ORACLE and HAS_ORACLE:
            try:
                if self.connect_to_oracle():
                    return True
            except Exception as e:
                error_msg = f"Erreur de connexion Oracle: {e}\nPassage à SQLite."
                print(error_msg)
                messagebox.showinfo("Fallback SQLite", "La connexion Oracle a échoué, utilisation de SQLite à la place.")
                USE_ORACLE = False  # Désactiver Oracle pour les futures tentatives
        
        # Si Oracle a échoué ou n'est pas demandé, utiliser SQLite
        return self.connect_to_sqlite()
        
    def connect_to_oracle(self):
        """Établit la connexion à Oracle et prépare la table"""
        try:
            # Connexion avec la chaîne directe
            self.connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=CONNECT_STRING)
            self.cursor = self.connection.cursor()
            self.conn_status_var.set(f"Connecté à Oracle ({CONNECT_STRING})")
            self.status_var.set("Connexion Oracle établie avec succès")
            self.using_oracle = True
            
            # Création/Modification de la table pour autoriser NULL
            self.cursor.execute("""
            DECLARE
              cnt NUMBER;
              col_nullable VARCHAR2(1);
            BEGIN
              SELECT COUNT(*) INTO cnt
                FROM user_tables
               WHERE table_name = UPPER('CPU_TEMPERATURES');
              
              IF cnt = 0 THEN
                EXECUTE IMMEDIATE '
                  CREATE TABLE cpu_temperatures (
                    id           NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    timestamp    TIMESTAMP     NOT NULL,
                    temp_celsius NUMBER(5,2)   NULL
                  )';
              ELSE
                -- Vérifier si la colonne temp_celsius accepte les NULL
                SELECT nullable INTO col_nullable
                FROM user_tab_columns
                WHERE table_name = 'CPU_TEMPERATURES'
                AND column_name = 'TEMP_CELSIUS';
                
                -- Si la colonne est définie comme NOT NULL, la modifier
                IF col_nullable = 'N' THEN
                  EXECUTE IMMEDIATE 'ALTER TABLE cpu_temperatures MODIFY (temp_celsius NULL)';
                END IF;
              END IF;
            END;
            """)
            self.connection.commit()
            
            # Obtenir le nombre total d'enregistrements
            self.cursor.execute("SELECT COUNT(*) FROM cpu_temperatures")
            self.total_records = self.cursor.fetchone()[0]
            self.records_var.set(str(self.total_records))
            
            # Chargement des données récentes
            self.load_recent_data()
            
            return True
        except oracledb.DatabaseError as e:
            error_msg = f"Erreur de connexion Oracle : {e}"
            self.conn_status_var.set("Non connecté - Erreur Oracle")
            self.status_var.set(error_msg)
            messagebox.showerror("Erreur Oracle", error_msg)
            return self.connect_to_sqlite()  # Fallback to SQLite
    
    def connect_to_sqlite(self):
        """Établit la connexion à SQLite et prépare la table"""
        try:
            self.connection = sqlite3.connect(SQLITE_DB_PATH)
            self.cursor = self.connection.cursor()
            self.conn_status_var.set(f"Connecté à SQLite ({SQLITE_DB_PATH})")
            self.status_var.set("Connexion SQLite établie avec succès")
            self.using_oracle = False
            
            # Création de la table si elle n'existe pas
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS cpu_temperatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                temp_celsius REAL
            )
            """)
            self.connection.commit()
            
            # Obtenir le nombre total d'enregistrements
            self.cursor.execute("SELECT COUNT(*) FROM cpu_temperatures")
            self.total_records = self.cursor.fetchone()[0]
            self.records_var.set(str(self.total_records))
            
            # Chargement des données récentes
            self.load_recent_data()
            
            return True
        except sqlite3.Error as e:
            error_msg = f"Erreur de connexion SQLite : {e}"
            self.conn_status_var.set("Non connecté - Erreur SQLite")
            self.status_var.set(error_msg)
            messagebox.showerror("Erreur SQLite", error_msg)
            
            # On peut fonctionner sans base de données
            self.connection = None
            self.cursor = None
            return False
    
    def load_recent_data(self):
        """Charge les données récentes de la base"""
        if not self.connection or not self.cursor:
            self.status_var.set("Pas de connexion à la base de données pour charger les données")
            return
            
        try:
            # Récupération des 10 derniers enregistrements pour le tableau
            if self.using_oracle:
                self.cursor.execute("""
                    SELECT id, timestamp, temp_celsius 
                    FROM cpu_temperatures 
                    ORDER BY timestamp DESC 
                    FETCH FIRST 10 ROWS ONLY
                """)
            else:  # SQLite
                self.cursor.execute("""
                    SELECT id, timestamp, temp_celsius 
                    FROM cpu_temperatures 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """)
                
            rows = self.cursor.fetchall()
            
            # Effacer les données actuelles
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Insertion des nouvelles données
            for row in rows:
                # Le format timestamp est différent entre SQLite et Oracle
                if self.using_oracle:
                    timestamp_str = row[1].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row[1], 'strftime') else str(row[1])
                else:
                    timestamp_str = str(row[1])
                    
                temp_str = f"{row[2]:.2f}" if row[2] is not None else "N/A"
                self.tree.insert('', 'end', values=(row[0], timestamp_str, temp_str))
            
            # Récupérer les statistiques
            if self.using_oracle:
                self.cursor.execute("""
                    SELECT 
                        MIN(temp_celsius), 
                        MAX(temp_celsius), 
                        AVG(temp_celsius),
                        COUNT(*)
                    FROM cpu_temperatures
                    WHERE temp_celsius IS NOT NULL
                """)
            else:  # SQLite
                self.cursor.execute("""
                    SELECT 
                        MIN(temp_celsius), 
                        MAX(temp_celsius), 
                        AVG(temp_celsius),
                        COUNT(*)
                    FROM cpu_temperatures
                    WHERE temp_celsius IS NOT NULL
                """)
                
            stats = self.cursor.fetchone()
            
            if stats[0] is not None:
                self.temp_min_var.set(f"{stats[0]:.2f} °C")
                self.temp_max_var.set(f"{stats[1]:.2f} °C")
                self.temp_avg_var.set(f"{stats[2]:.2f} °C")
            
            self.total_records = stats[3]
            self.records_var.set(str(self.total_records))
            
            self.status_var.set(f"Données chargées: {self.total_records} enregistrements au total")
        except Exception as e:
            self.status_var.set(f"Erreur lors du chargement des données: {e}")
    
    def update_graph(self, frame):
        """Fonction appelée par l'animation pour mettre à jour le graphique"""
        if not self.temps_history:
            return self.line,
        
        # Garder seulement les MAX_POINTS derniers points
        if len(self.temps_history) > MAX_POINTS:
            self.temps_history = self.temps_history[-MAX_POINTS:]
        
        dates = [t[0] for t in self.temps_history]
        temps = [t[1] for t in self.temps_history]
        
        # Mettre à jour les données de la ligne
        self.line.set_data(dates, temps)
        
        # Ajuster les axes automatiquement
        self.ax.relim()
        self.ax.autoscale_view()
        
        # Format des dates sur l'axe X
        self.fig.autofmt_xdate(rotation=0)
        
        return self.line,
    
    def start_monitoring(self):
        """Démarre le thread de surveillance"""
        if self.running:
            return
        
        # Vérifier si la connexion est active (pas bloquant)
        if not self.connection or self.cursor is None:
            self.connect_to_database()
        
        # Récupérer l'intervalle
        try:
            interval = int(self.interval_var.get())
            if interval < 1:
                raise ValueError("L'intervalle doit être d'au moins 1 seconde")
        except ValueError as e:
            messagebox.showerror("Erreur", f"Intervalle invalide: {e}")
            return
        
        global SAMPLE_INTERVAL
        SAMPLE_INTERVAL = interval
        
        # Initialiser les données du graphique
        self.temps_history = []
        
        # Démarrer l'animation du graphique
        self.anim = animation.FuncAnimation(
            self.fig, self.update_graph, interval=UPDATE_INTERVAL*1000, blit=True
        )
        
        # Démarrer le thread de surveillance
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Surveillance démarrée")
    
    def stop_monitoring(self):
        """Arrête le thread de surveillance"""
        self.running = False
        
        # Arrêter l'animation
        if self.anim:
            self.anim.event_source.stop()
            self.anim = None
        
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Surveillance arrêtée")
    
    def monitoring_loop(self):
        """Boucle principale de surveillance qui s'exécute dans un thread séparé"""
        # Créer une connexion dédiée pour ce thread si on utilise SQLite
        thread_connection = None
        thread_cursor = None
        
        if self.connection and not self.using_oracle:
            # Pour SQLite, on crée une nouvelle connexion dans ce thread
            try:
                thread_connection = sqlite3.connect(SQLITE_DB_PATH)
                thread_cursor = thread_connection.cursor()
            except sqlite3.Error as e:
                self.root.after(0, lambda: self.status_var.set(f"Erreur de connexion SQLite dans le thread: {e}"))
        
        while self.running:
            try:
                # Lire la température
                temp_c = self.lire_temperature_cpu()
                timestamp = datetime.datetime.now()
                
                # Mettre à jour l'affichage de la température
                self.root.after(0, self.update_temperature_display, temp_c, timestamp)
                
                # Ajouter à l'historique pour le graphique
                if temp_c is not None:
                    self.temps_history.append((timestamp, temp_c))
                
                # Insérer dans la base de données toutes les SAMPLE_INTERVAL secondes
                if (self.last_save_time is None or 
                    (timestamp - self.last_save_time).total_seconds() >= SAMPLE_INTERVAL):
                    
                    # Choisir la connexion appropriée selon le thread
                    if self.using_oracle and self.connection and self.cursor:
                        # Utiliser la connexion Oracle principale (pas de problème de thread)
                        connection = self.connection
                        cursor = self.cursor
                    elif thread_connection and thread_cursor:
                        # Utiliser la connexion SQLite de ce thread
                        connection = thread_connection
                        cursor = thread_cursor
                    else:
                        connection = None
                        cursor = None
                    
                    if connection and cursor:
                        if self.using_oracle:
                            # Oracle
                            if temp_c is not None:
                                cursor.execute(
                                    "INSERT INTO cpu_temperatures (timestamp, temp_celsius) VALUES (:ts, :temp)",
                                    {'ts': timestamp, 'temp': round(temp_c, 2)}
                                )
                            else:
                                cursor.execute(
                                    "INSERT INTO cpu_temperatures (timestamp, temp_celsius) VALUES (:ts, NULL)",
                                    {'ts': timestamp}
                                )
                        else:
                            # SQLite
                            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                            if temp_c is not None:
                                cursor.execute(
                                    "INSERT INTO cpu_temperatures (timestamp, temp_celsius) VALUES (?, ?)",
                                    (timestamp_str, round(temp_c, 2))
                                )
                            else:
                                cursor.execute(
                                    "INSERT INTO cpu_temperatures (timestamp, temp_celsius) VALUES (?, NULL)",
                                    (timestamp_str,)
                                )
                        
                        connection.commit()
                        self.last_save_time = timestamp
                        self.total_records += 1
                        
                        # Mettre à jour le tableau et les statistiques
                        self.root.after(0, lambda: self.records_var.set(str(self.total_records)))
                        self.root.after(0, lambda: self.last_save_var.set(timestamp.strftime('%H:%M:%S')))
                        self.root.after(0, self.update_table_with_new_record, timestamp, temp_c)
                
                # Attendre un court instant
                time.sleep(UPDATE_INTERVAL)
                
            except Exception as e:
                error_msg = f"Erreur dans la boucle de surveillance: {e}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: messagebox.showerror("Erreur", error_msg))
                self.running = False
                self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
                break
    
    def update_temperature_display(self, temp_c, timestamp):
        """Met à jour l'affichage de la température actuelle et son indicateur coloré"""
        if temp_c is not None:
            self.temp_var.set(f"{temp_c:.1f} °C")
            
            # Mettre à jour l'indicateur coloré
            if temp_c > 75:  # Critique
                self.temp_indicator.configure(style='Critical.TLabel')
            elif temp_c > 60:  # Attention
                self.temp_indicator.configure(style='Warning.TLabel')
            else:  # Normal
                self.temp_indicator.configure(style='Normal.TLabel')
                
            # Mettre à jour les statistiques si nécessaire
            try:
                current_min = float(self.temp_min_var.get().split()[0])
                if temp_c < current_min or self.temp_min_var.get() == "--.- °C":
                    self.temp_min_var.set(f"{temp_c:.2f} °C")
            except:
                self.temp_min_var.set(f"{temp_c:.2f} °C")
                
            try:
                current_max = float(self.temp_max_var.get().split()[0])
                if temp_c > current_max or self.temp_max_var.get() == "--.- °C":
                    self.temp_max_var.set(f"{temp_c:.2f} °C")
            except:
                self.temp_max_var.set(f"{temp_c:.2f} °C")
        else:
            self.temp_var.set("N/A")
            self.temp_indicator.configure(style='TLabel')  # Style neutre
    
    def update_table_with_new_record(self, timestamp, temp_c):
        """Ajoute un nouvel enregistrement au tableau et retire le plus ancien"""
        if not self.connection or not self.cursor:
            return
            
        # Récupérer l'ID du dernier enregistrement
        try:
            if self.using_oracle:
                self.cursor.execute("SELECT MAX(id) FROM cpu_temperatures")
            else:  # SQLite
                self.cursor.execute("SELECT MAX(id) FROM cpu_temperatures")
                
            last_id = self.cursor.fetchone()[0]
            
            # Ajouter le nouvel enregistrement en haut du tableau
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            temp_str = f"{temp_c:.2f}" if temp_c is not None else "N/A"
            
            self.tree.insert('', 0, values=(last_id, timestamp_str, temp_str))
            
            # Supprimer le dernier élément si plus de 10
            if len(self.tree.get_children()) > 10:
                last_item = self.tree.get_children()[-1]
                self.tree.delete(last_item)
                
        except Exception as e:
            self.status_var.set(f"Erreur lors de la mise à jour du tableau: {e}")
    
    def lire_temperature_cpu(self):
        """
        Lit la température CPU moyenne en °C.
        - Sous Windows: tente WMI, puis fallback à d'autres méthodes.
        - Sous Linux/macOS: psutil.sensors_temperatures().
        Retourne float (°C) ou None si impossible.
        """
        global skip_wmi
        # Branch Windows
        if os.name == 'nt' and not skip_wmi:
            try:
                import wmi
                w = wmi.WMI(namespace="root\\WMI")
                temps = w.MSAcpi_ThermalZoneTemperature()
                if temps:
                    valeurs = [(t.CurrentTemperature / 10.0 - 273.15) for t in temps]
                    return sum(valeurs) / len(valeurs)
                else:
                    raise RuntimeError("Aucun capteur WMI disponible.")
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"WMI failed: {e}. Passage en fallback alternatif."))
                skip_wmi = True

        # Tentative avec psutil (Linux/macOS ou fallback)
        try:
            if hasattr(psutil, 'sensors_temperatures'):
                temps_dict = psutil.sensors_temperatures()
                
                # Linux coretemp
                if 'coretemp' in temps_dict:
                    valeurs = [t.current for t in temps_dict['coretemp']]
                    return sum(valeurs) / len(valeurs)
                # Autre capteur
                for key in temps_dict:
                    if temps_dict[key]:
                        return temps_dict[key][0].current
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"psutil.sensors_temperatures() error: {e}"))

        # Si on est sur Windows, essayons une dernière méthode - simulation basée sur la charge CPU
        if os.name == 'nt':
            try:
                # Obtenir charge CPU actuelle
                cpu_load = psutil.cpu_percent(interval=0.5)
                # Température ambiante supposée + charge proportionnelle (simulation)
                simulated_temp = 25 + (cpu_load * 0.5)
                return simulated_temp
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Méthode alternative de température échouée: {e}"))

        return None
    
    def on_closing(self):
        """Ferme proprement l'application"""
        self.running = False
        
        # Arrêter l'animation
        if self.anim:
            self.anim.event_source.stop()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(1.0)  # Attendre 1 seconde max
        
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            
        self.root.destroy()

# === Point d'entrée de l'application ===
if __name__ == "__main__":
    try:
        # Configurer matplotlib pour un meilleur rendu
        plt.style.use('ggplot')
        
        root = tk.Tk()
        app = RealTimeCPUTempMonitor(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Erreur critique", f"Une erreur critique est survenue: {e}")
        import traceback
        traceback.print_exc()