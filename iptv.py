from datetime import datetime
import os
import gzip
from pprint import pprint
import shutil

import requests
import xmltodict

from epgs import urls
from canales import incluir

folder_path = 'downloads'
output_name = "epg.xml"

xmls = []

def obtener_extension(filename):
    return os.path.splitext(filename)[1]


fechahoraactual = datetime.now().strftime("%Y%m%d%H%M%S")

if not os.path.exists(folder_path):
    os.makedirs(folder_path)
    print(f"Carpeta '{folder_path}' creada.")

for name, url in urls:
    extension = obtener_extension(name)
    filename = f"{folder_path}/{name}"

    response = requests.get(url)
    with open(filename, 'wb') as file:
        file.write(response.content)

    print(f"Archivo guardado como {filename}")

    if extension == '.gz':
        uncompressed_filename = filename[:-3]

        with gzip.open(filename, 'rb') as f_in:
            with open(uncompressed_filename, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        print(f"Archivo descomprimido como {uncompressed_filename}")
        xmls.append(uncompressed_filename)
    if extension == '.xml':
        xmls.append(filename)

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

        if len(xml_canales_filtrados) == 0:
            continue

        canales += xml_canales_filtrados
        programas += [p for p in xml_programas if p["@channel"] in incluir]

        ids_en_xml_canales = {canal["@id"] for canal in xml_canales}
        incluir = [id_str for id_str in incluir if id_str not in ids_en_xml_canales]



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
