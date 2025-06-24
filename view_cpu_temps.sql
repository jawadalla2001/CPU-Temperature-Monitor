-- Fichier: view_cpu_temps.sql
-- Description: Requêtes pour consulter la table cpu_temperatures
-- Utilisation: sqlplus system/jawad-10-10-2001@localhost:1521/FREE @view_cpu_temps.sql

-- Afficher l'heure et le nom d'utilisateur
SELECT USER, TO_CHAR(SYSDATE, 'DD-MON-YYYY HH24:MI:SS') AS DATE_HEURE FROM DUAL;

-- Voir la structure de la table
DESCRIBE cpu_temperatures;

-- Voir les données enregistrées (10 derniers enregistrements)
SELECT * FROM cpu_temperatures ORDER BY timestamp DESC FETCH FIRST 10 ROWS ONLY;

-- Voir les statistiques des températures
SELECT 
    MIN(temp_celsius) AS min_temp,
    MAX(temp_celsius) AS max_temp,
    AVG(temp_celsius) AS avg_temp,
    COUNT(*) AS total_records
FROM cpu_temperatures
WHERE temp_celsius IS NOT NULL;

-- Compter le nombre d'enregistrements par jour
SELECT 
    TO_CHAR(timestamp, 'YYYY-MM-DD') AS jour,
    COUNT(*) AS nombre_mesures,
    ROUND(AVG(temp_celsius), 2) AS temp_moyenne
FROM cpu_temperatures
GROUP BY TO_CHAR(timestamp, 'YYYY-MM-DD')
ORDER BY jour DESC;

-- Trouver les 5 températures les plus élevées
SELECT 
    id,
    timestamp, 
    temp_celsius
FROM cpu_temperatures
WHERE temp_celsius IS NOT NULL
ORDER BY temp_celsius DESC
FETCH FIRST 5 ROWS ONLY;

-- Afficher un histogramme ASCII simple des températures
COLUMN temp_range FORMAT A15
COLUMN count FORMAT 9999
COLUMN bar FORMAT A50
BREAK ON REPORT
COMPUTE SUM OF count ON REPORT

SELECT 
    CASE 
        WHEN temp_celsius < 40 THEN 'Moins de 40°C'
        WHEN temp_celsius < 50 THEN '40°C - 50°C'
        WHEN temp_celsius < 60 THEN '50°C - 60°C'
        WHEN temp_celsius < 70 THEN '60°C - 70°C'
        WHEN temp_celsius < 80 THEN '70°C - 80°C'
        ELSE 'Plus de 80°C'
    END AS temp_range,
    COUNT(*) AS count,
    RPAD('■', COUNT(*)/10 + 1, '■') AS bar
FROM cpu_temperatures
WHERE temp_celsius IS NOT NULL
GROUP BY CASE 
    WHEN temp_celsius < 40 THEN 'Moins de 40°C'
    WHEN temp_celsius < 50 THEN '40°C - 50°C'
    WHEN temp_celsius < 60 THEN '50°C - 60°C'
    WHEN temp_celsius < 70 THEN '60°C - 70°C'
    WHEN temp_celsius < 80 THEN '70°C - 80°C'
    ELSE 'Plus de 80°C'
END
ORDER BY temp_range;
