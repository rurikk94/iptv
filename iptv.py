from datetime import datetime, timezone
import os
import gzip
from pprint import pprint
import shutil

import requests
import xmltodict

from epgs import urls
from canales import incluir
from utils import descomprimir, download_file, extract_tvg_ids, file_is_expired

folder_path = 'downloads'
output_name = "epg.xml"
horas = 3

xmls = []

def obtener_extension(filename):
    return os.path.splitext(filename)[1]


fechahoraactual = datetime.now().strftime("%Y%m%d%H%M%S")

tvg_ids_lista = extract_tvg_ids('lista.m3u')
canales_no_se_usan = [tvg_id for tvg_id in incluir if tvg_id not in tvg_ids_lista]
tvg_ids_no_existen = [tvg_id for tvg_id in tvg_ids_lista if tvg_id not in incluir]
incluir = [tvg_id for tvg_id in tvg_ids_lista if tvg_id in incluir]

if len(canales_no_se_usan) > 0:
    print("Los siguientes canales no se usan en la lista:")
    pprint(canales_no_se_usan)

if len(tvg_ids_no_existen) > 0:
    print("Los siguientes tvg-ids de la lista no existen en la epg:")
    pprint(tvg_ids_no_existen)


if not os.path.exists(folder_path):
    os.makedirs(folder_path)
    print(f"Carpeta '{folder_path}' creada.")

for name, url in urls:
    extension = obtener_extension(name)
    filename = f"{folder_path}/{name}"

    if os.path.exists(filename):
        print(f"Archivo {filename} ya existe")

        if file_is_expired(filename, horas):
            filename = download_file(url, filename, extension)

        if obtener_extension(filename) == '.gz':
            filename = descomprimir(filename)

        xmls.append(filename)
    else:
        file = download_file(url, filename, extension)

        if obtener_extension(file) == '.gz':
            file = descomprimir(file)
        xmls.append(file)


canales = []
programas = []

for filename in xmls:

    print("Revisando archivo", filename)


    with open(filename, 'r', encoding='utf-8') as file:
        data = file.read()

        xml_dict = xmltodict.parse(data)
        xml_canales = xml_dict["tv"]["channel"]
        xml_programas = xml_dict["tv"]["programme"]

        xml_canales_filtrados = [canal for canal in xml_canales if canal["@id"] in incluir]
        canales_encontrados = [canal["@id"] for canal in xml_canales_filtrados]
        xml_programas_filtrados = [p for p in xml_programas if p["@channel"] in canales_encontrados]

        if len(xml_canales_filtrados) == 0:
            continue

        if len(xml_programas_filtrados) == 0:
            print("No se han encontrado programas para los canales encontrados")
            print(canales_encontrados)
            continue

        for c in xml_canales_filtrados:
            flag = False
            for p in xml_programas_filtrados:
                if p["@channel"] == c["@id"]:
                    flag = True
                    break
            if not flag:
                print(f"No se han encontrado programas para el canal {c['@id']}")

        canales += xml_canales_filtrados
        programas += xml_programas_filtrados

        ids_en_xml_canales = {canal["@id"] for canal in xml_canales}
        incluir = [id_str for id_str in incluir if id_str not in ids_en_xml_canales]

        for programa in programas:
            start_time_str = programa["@start"]
            start_time = datetime.strptime(start_time_str, "%Y%m%d%H%M%S %z")
            start_time_utc = start_time.astimezone(timezone.utc)
            programa["@start"] = start_time_utc.strftime("%Y%m%d%H%M%S %z")

            stop_time_str = programa["@stop"]
            stop_time = datetime.strptime(stop_time_str, "%Y%m%d%H%M%S %z")
            stop_time_utc = stop_time.astimezone(timezone.utc)
            programa["@stop"] = stop_time_utc.strftime("%Y%m%d%H%M%S %z")



        programacion = {
            'tv': {
                '@generator-info-name': 'none',
                '@generator-info-url': 'none',
                'channel': canales,
                'programme': programas
            }
        }

xmltodict.unparse(programacion, output=open(output_name, 'w', encoding="utf-8"), pretty=True)

archivo_comprimido = output_name+'.gz'

with open(output_name, 'rb') as f_in:
    with gzip.open(archivo_comprimido, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

print(f'Archivo {output_name} comprimido como {archivo_comprimido}')


print("No se han encontrado los canales:")
pprint(incluir)
