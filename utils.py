from datetime import datetime, timezone
import gzip
import os
import re
import shutil

import requests

def extract_tvg_ids(file_path):
    tvg_ids = set()
    tvg_id_pattern = re.compile(r'tvg-id="([^"]+)"')

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = tvg_id_pattern.search(line)
            if match:
                tvg_ids.add(match.group(1))

    return sorted(tvg_ids)

def file_is_expired(filename, horas):
    modification_time = os.path.getmtime(filename)
    modification_datetime =datetime.fromtimestamp(modification_time, tz=timezone.utc)
    current_time = datetime.now(timezone.utc)
    time_difference = current_time - modification_datetime

    if time_difference.total_seconds() > horas * 3600:
        print(f"Archivo expirado {filename}")
        return True
    return False

def descomprimir(filename):
    uncompressed_filename = filename[:-3]

    with gzip.open(filename, 'rb') as f_in:
        with open(uncompressed_filename, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    print(f"Archivo descomprimido como {uncompressed_filename}")
    return uncompressed_filename

def download_file(url, filename, extension):

    response = requests.get(url)
    with open(filename, 'wb') as file:
        file.write(response.content)

    print(f"Archivo descargado {filename}")

    if extension == '.gz':
        return descomprimir(filename)
    if extension == '.xml':
        return filename