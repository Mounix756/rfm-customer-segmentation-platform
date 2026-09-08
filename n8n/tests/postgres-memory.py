"""Intégration isolée : vrai nœud n8n + PostgreSQL, sans appel au modèle.
Nécessite Python 3 et Docker. Ne touche pas aux services ni volumes du projet.
"""
import os
from pathlib import Path
import subprocess
import time
import uuid

prefix = 'rfm-memory-test-' + uuid.uuid4().hex[:10]
network, volume, database = prefix + '-net', prefix + '-data', prefix + '-db'
image = os.environ.get('N8N_IMAGE', 'docker.n8n.io/n8nio/n8n:2.36.7')
workflow_dir = Path(__file__).resolve().parents[1]
# Mot de passe jetable, réservé à un réseau de test isolé et supprimé à la fin.
password = uuid.uuid4().hex
containers = []

def docker(*args, timeout=120):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr + result.stdout)
    return result.stdout.strip()

def ready():
    for _ in range(60):
        result = subprocess.run(['docker', 'exec', database, 'pg_isready', '-U', 'rfm_memory', '-d', 'rfm_memory'], capture_output=True)
        if result.returncode == 0:
            return
        time.sleep(0.5)
    raise RuntimeError('PostgreSQL indisponible')

try:
    docker('network', 'create', '--internal', network)
    docker('volume', 'create', volume)
    containers.append(database)
    docker('run', '-d', '--name', database, '--network', network, '--network-alias', 'postgres',
           '-e', 'POSTGRES_DB=rfm_memory', '-e', 'POSTGRES_USER=rfm_memory',
           '-e', f'POSTGRES_PASSWORD={password}', '--mount', f'type=volume,src={volume},dst=/var/lib/postgresql/data',
           'postgres:16-alpine')
    ready()
    for mode in ['write', 'verify']:
        if mode == 'verify':
            docker('restart', database)
            ready()
        name = prefix + '-' + mode
        containers.append(name)
        print(docker('run', '--rm', '--name', name, '--network', network,
                     '--mount', f'type=bind,src={workflow_dir},dst=/workflow,readonly',
                     '-e', f'PGPASSWORD={password}', '--entrypoint', 'node', image,
                     '/workflow/tests/memory-runtime.cjs', mode), flush=True)
finally:
    for name in reversed(containers):
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
    subprocess.run(['docker', 'volume', 'rm', volume], capture_output=True)
    subprocess.run(['docker', 'network', 'rm', network], capture_output=True)
