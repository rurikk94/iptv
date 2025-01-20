import csv

def leer_epgs_csv(filepath):
    epgs_dict = []
    with open(filepath, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            epgs_dict.append((row['filename'], row['url']))
    return epgs_dict

# Ejemplo de uso
urls = leer_epgs_csv('epgs.csv')
# print(urls)
