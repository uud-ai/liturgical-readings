import json
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path

BOOK_MAP = {
    "Мф": "Mt", "Мк": "Mk", "Лк": "Lk", "Ин": "Jn",
    "Деян": "Act", "Иак": "Jas", "1Пет": "1Pe", "2Пет": "2Pe",
    "1Ин": "1Jn", "2Ин": "2Jn", "3Ин": "3Jn", "Иуд": "Jude",
    "Рим": "Rom", "1Кор": "1Co", "2Кор": "2Co", "Гал": "Gal",
    "Еф": "Eph", "Флп": "Php", "Кол": "Col", "1Фес": "1Th",
    "2Фес": "2Th", "1Тим": "1Ti", "2Тим": "2Ti", "Тит": "Tit",
    "Флм": "Phm", "Евр": "Heb"
}

def parse_reference_to_azbyka_format(ref_str):
    # Убираем пробелы и заменяем все виды длинных тире на обычный дефис
    ref_str = ref_str.replace("–", "-").replace("—", "-").replace(" ", "")
    for rus, eng in BOOK_MAP.items():
        if ref_str.startswith(rus):
            # Заменяем только само сокращение, оставляя точку на месте
            clean_ref = ref_str.replace(rus, eng)
            return clean_ref
    return None

def fetch_synodal_text(reference_str):
    azbyka_ref = parse_reference_to_azbyka_format(reference_str)
    if not azbyka_ref:
        print(f"[!] Не удалось распознать книгу: {reference_str}")
        return ""

    url = f"https://azbyka.ru/biblia/?{azbyka_ref}&r"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        verses = soup.find_all('div', class_='r')
        if not verses:
            verses = soup.find_all('p', class_='text')

        text_lines = []
        for verse in verses:
            clean_text = verse.get_text(separator=" ", strip=True)
            if clean_text:
                text_lines.append(clean_text)
                
        return " ".join(text_lines)
    except Exception as e:
        print(f"[Ошибка] Не удалось скачать {reference_str}: {e}")
        return ""

def process_zachala_file(input_file, output_file, type_name):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[!] Файл {input_file} не найден.")
        return

    print(f"\n--- Начинаем парсинг: {type_name} ---")
    
    count = 0
    
    def traverse(node):
        nonlocal count
        if isinstance(node, dict):
            # Теперь скрипт ищет правильный ключ 'ref'
            if 'ref' in node and isinstance(node['ref'], str):
                ref = node['ref']
                print(f"Загрузка: {ref}...")
                text = fetch_synodal_text(ref)
                node['text'] = text
                count += 1
                time.sleep(1.5)
            else:
                for k, v in node.items():
                    if k.startswith('_'):
                        continue
                    traverse(v)

    traverse(data)
    
    if count > 0:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Успешно обработано зачал: {count}. Сохранено в {output_file}")
    else:
        print("⚠️ Не найдено ни одного зачала (поля 'ref').")

if __name__ == "__main__":
    process_zachala_file(
        input_file="data/gospel_zachala.json", 
        output_file="data/texts/gospel_texts.json",
        type_name="Евангелие"
    )
    
    process_zachala_file(
        input_file="data/apostle_zachala.json", 
        output_file="data/texts/apostle_texts.json",
        type_name="Апостол"
    )