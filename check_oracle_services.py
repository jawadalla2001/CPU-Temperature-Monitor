import oracledb
import socket
import subprocess
import os

def check_oracle_connection():
    print("Vérification des connexions Oracle possibles...")
    
    # Options possibles pour le service_name/SID
    service_names = [
        "Oracle24C", "ORCL", "XE", "FREEPDB1", "ORCLPDB1", 
        "XEPDB1", "PDBORCL", "FREE", "Oracle24C.localdomain"
    ]
    
    # Options possibles pour l'hôte
    hosts = ["localhost", "127.0.0.1"]
    
    # Options possibles pour le port
    ports = [1521, 1522]
    
    # User/password
    user = "system"
    password = "jawad-10-10-2001"
    
    # Tester les connexions
    for host in hosts:
        for port in ports:
            # Vérifier si le port est ouvert
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex((host, port))
                    if result != 0:
                        print(f"Port {port} non disponible sur {host}")
                        continue
                    else:
                        print(f"Port {port} est ouvert sur {host}")
            except Exception as e:
                print(f"Erreur de vérification du port {port} sur {host}: {e}")
                continue
            
            # Tester chaque service
            for service in service_names:
                try:
                    # Format EZ Connect
                    dsn = f"{host}:{port}/{service}"
                    print(f"Essai avec: {dsn}")
                    conn = oracledb.connect(user=user, password=password, dsn=dsn)
                    print(f"✅ Connexion réussie avec: {dsn}")
                    conn.close()
                except Exception as e:
                    print(f"❌ Échec: {e}")
                    
                try:
                    # Format SID
                    dsn = f"{host}:{port}:{service}"
                    print(f"Essai avec: {dsn}")
                    conn = oracledb.connect(user=user, password=password, dsn=dsn)
                    print(f"✅ Connexion réussie avec: {dsn}")
                    conn.close()
                except Exception as e:
                    print(f"❌ Échec: {e}")

if __name__ == "__main__":
    try:
        check_oracle_connection()
    except Exception as e:
        print(f"Erreur globale: {e}")
    
    print("\nAppuyez sur Entrée pour quitter...")
    input() 