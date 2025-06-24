🌡️ CPU Temperature Monitor
Une application Python complète pour surveiller et enregistrer la température du processeur en temps réel avec une interface graphique moderne et un stockage de données flexible.

✨ Fonctionnalités
Surveillance en temps réel : Monitoring continu de la température CPU

Interface graphique intuitive : Dashboard avec graphiques temps réel et tableaux de données

Double stockage : Support Oracle Database et SQLite avec basculement automatique

Visualisation avancée : Graphiques interactifs avec historique des températures

Statistiques détaillées : Min/Max/Moyenne avec indicateurs visuels colorés

Configuration flexible : Intervalles d'échantillonnage personnalisables

Scripts SQL inclus : Requêtes prêtes pour l'analyse des données

🚀 Installation
Prérequis
bash
pip install tkinter matplotlib psutil sqlite3 oracledb
Installation Oracle (optionnelle)
Pour utiliser Oracle Database :

bash
pip install oracledb
📋 Structure du Projet
text
cpu-temperature-monitor/
├── scriptinterface.py          # Application principale avec interface graphique
├── check_oracle_services.py    # Script de test des connexions Oracle
├── view_cpu_temps.sql          # Requêtes SQL pour analyse des données
└── README.md                   # Documentation du projet
🔧 Configuration
Base de Données Oracle
Modifiez les paramètres dans scriptinterface.py :

python
DB_USER = 'system'
DB_PASSWORD = 'votre_mot_de_passe'
CONNECT_STRING = "localhost:1521/FREE"
USE_ORACLE = True
Base de Données SQLite
Le fichier SQLite sera créé automatiquement dans :

text
cpu_temperatures.db
🎯 Utilisation
Lancement de l'Application
bash
python scriptinterface.py
Test de Connexion Oracle
bash
python check_oracle_services.py
Analyse des Données SQL
bash
sqlplus system/mot_de_passe@localhost:1521/FREE @view_cpu_temps.sql
📊 Interface Utilisateur
L'application propose :

Température actuelle avec indicateur coloré (Vert/Jaune/Rouge)

Graphique temps réel avec zoom et navigation

Tableau des données récentes (10 derniers enregistrements)

Statistiques en direct (Min/Max/Moyenne)

Contrôles de surveillance (Démarrer/Arrêter/Actualiser)

🔍 Fonctionnalités Techniques
Détection de Température
Windows : WMI avec fallback sur simulation basée sur charge CPU

Linux/macOS : psutil.sensors_temperatures()

Gestion d'erreurs : Basculement automatique entre méthodes

Stockage des Données
Table automatique : Création automatique des tables nécessaires

Gestion des NULL : Support des valeurs manquantes

Threading sécurisé : Connexions dédiées par thread pour SQLite

📈 Analyses Disponibles
Le fichier view_cpu_temps.sql inclut :

Statistiques globales des températures

Comptage par jour avec moyennes

Top 5 des températures les plus élevées

Histogramme ASCII des plages de température

⚙️ Paramètres Configurables
python
UPDATE_INTERVAL = 2      # Intervalle graphique (secondes)
SAMPLE_INTERVAL = 5      # Intervalle sauvegarde (secondes)
MAX_POINTS = 60         # Points max sur graphique
🛠️ Dépannage
Problèmes Oracle
Vérifiez le service Oracle avec check_oracle_services.py

Testez différents DSN (FREE, FREEPDB1, XE)

L'application bascule automatiquement vers SQLite

Température Non Détectée
Windows : Exécutez en tant qu'administrateur

Linux : Vérifiez les permissions sur /sys/class/hwmon

Fallback : L'application utilise une simulation basée sur la charge CPU

📄 Licence
Ce projet est libre d'utilisation pour des fins éducatives et de monitoring système.

🤝 Contributions
Les contributions sont les bienvenues ! N'hésitez pas à :

Signaler des bugs

Proposer de nouvelles fonctionnalités

Améliorer la documentation

Ajouter le support d'autres capteurs

📞 Support
Pour toute question ou problème, ouvrez une issue sur GitHub ou consultez la documentation incluse dans les fichiers Python.

Technologies utilisées : Python, Tkinter, Matplotlib, Oracle Database, SQLite, WMI, psutil