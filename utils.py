import re

def extract_tvg_ids(file_path):
    tvg_ids = set()
    tvg_id_pattern = re.compile(r'tvg-id="([^"]+)"')

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = tvg_id_pattern.search(line)
            if match:
                tvg_ids.add(match.group(1))

    return sorted(tvg_ids)