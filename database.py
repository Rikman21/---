import sqlite3
import logging

DB_NAME = "market.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица предложений продавцов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            sku TEXT,
            product TEXT,
            price INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица каталога всех товаров Apple
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            model TEXT NOT NULL,
            memory TEXT,
            color TEXT,
            sim_type TEXT,
            category TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    
    # Заполняем каталог начальными данными, если он пуст
    cursor.execute("SELECT COUNT(*) FROM catalog")
    if cursor.fetchone()[0] == 0:
        populate_catalog(cursor)
        conn.commit()
    
    conn.close()

def populate_catalog(cursor):
    """
    Заполняет каталог базовым набором товаров Apple.
    Можно расширять по мере необходимости.
    """
    # iPhone модели (примеры популярных)
    iphone_models = [
        ("iPhone 16 Pro Max", ["256GB", "512GB", "1TB"], 
         ["Черный титан", "Белый титан", "Синий титан", "Натуральный титан"], 
         ["Dual", "eSIM"]),
        ("iPhone 16 Pro", ["128GB", "256GB", "512GB", "1TB"],
         ["Черный титан", "Белый титан", "Синий титан", "Натуральный титан"],
         ["Dual", "eSIM"]),
        ("iPhone 16", ["128GB", "256GB", "512GB"],
         ["Черный", "Белый", "Синий", "Розовый", "Желтый"],
         ["Dual", "eSIM"]),
        ("iPhone 15 Pro Max", ["256GB", "512GB", "1TB"],
         ["Черный титан", "Белый титан", "Синий титан", "Натуральный титан"],
         ["Dual", "eSIM"]),
        ("iPhone 15 Pro", ["128GB", "256GB", "512GB", "1TB"],
         ["Черный титан", "Белый титан", "Синий титан", "Натуральный титан"],
         ["Dual", "eSIM"]),
        ("iPhone 15", ["128GB", "256GB", "512GB"],
         ["Черный", "Белый", "Синий", "Розовый", "Желтый"],
         ["Dual", "eSIM"]),
    ]
    
    # iPad модели
    ipad_models = [
        ("iPad Pro 13", ["256GB", "512GB", "1TB", "2TB"],
         ["Серый космос", "Серебристый"],
         ["Wi-Fi", "Wi-Fi + Cellular"]),
        ("iPad Pro 11", ["256GB", "512GB", "1TB", "2TB"],
         ["Серый космос", "Серебристый"],
         ["Wi-Fi", "Wi-Fi + Cellular"]),
        ("iPad Air 13", ["128GB", "256GB", "512GB"],
         ["Серый космос", "Серебристый", "Синий", "Фиолетовый"],
         ["Wi-Fi", "Wi-Fi + Cellular"]),
        ("iPad Air 11", ["128GB", "256GB", "512GB"],
         ["Серый космос", "Серебристый", "Синий", "Фиолетовый"],
         ["Wi-Fi", "Wi-Fi + Cellular"]),
        ("iPad 10.2", ["64GB", "256GB"],
         ["Серый космос", "Серебристый"],
         ["Wi-Fi", "Wi-Fi + Cellular"]),
    ]
    
    # Apple Watch модели
    watch_models = [
        ("Apple Watch Series 10", ["42mm", "46mm"],
         ["Черный", "Белый", "Синий", "Красный"],
         ["GPS", "GPS + Cellular"]),
        ("Apple Watch Ultra 2", ["49mm"],
         ["Титан"],
         ["GPS + Cellular"]),
        ("Apple Watch SE", ["40mm", "44mm"],
         ["Серый космос", "Серебристый", "Золотой"],
         ["GPS", "GPS + Cellular"]),
    ]
    
    # Mac модели (для Mac: memory = хранилище SSD, sim_type = RAM)
    mac_models = [
        ("MacBook Pro 16", ["512GB", "1TB", "2TB", "4TB"],
         ["Серый космос", "Серебристый"],
         ["18GB", "36GB", "48GB"]),
        ("MacBook Pro 14", ["512GB", "1TB", "2TB", "4TB"],
         ["Серый космос", "Серебристый"],
         ["18GB", "36GB", "48GB"]),
        ("MacBook Air 15", ["256GB", "512GB", "1TB", "2TB"],
         ["Полночь", "Звездный свет", "Серебристый", "Серый космос"],
         ["8GB", "16GB", "24GB"]),
        ("MacBook Air 13", ["256GB", "512GB", "1TB", "2TB"],
         ["Полночь", "Звездный свет", "Серебристый", "Серый космос"],
         ["8GB", "16GB", "24GB"]),
    ]
    
    def add_products(category, models_list):
        for model, memories, colors, sim_types in models_list:
            for memory in memories:
                for color in colors:
                    for sim in sim_types:
                        # Генерируем уникальный SKU
                        sku = f"{category}_{model}_{memory}_{color}_{sim}".replace(" ", "_").replace("+", "plus")
                        try:
                            cursor.execute(
                                "INSERT INTO catalog (sku, model, memory, color, sim_type, category) VALUES (?, ?, ?, ?, ?, ?)",
                                (sku, model, memory, color, sim, category)
                            )
                        except sqlite3.IntegrityError:
                            pass  # SKU уже существует
    
    add_products("iPhone", iphone_models)
    add_products("iPad", ipad_models)
    add_products("Watch", watch_models)
    add_products("Mac", mac_models)

# --- ФУНКЦИИ ДЛЯ EXCEL ---
def update_prices_from_excel(user_id, username, prices_list):
    """
    prices_list: список кортежей (sku, model, memory, color, sim_type, price).
    Если price=None, товар не трогаем.

    Формируем читаемое имя товара и категории:
    - Категория берётся из начала модели (iPhone / iPad / Watch / Mac),
      а в названии товара ОБЯЗАТЕЛЬНО указываем тип SIM: Dual, eSIM или SIM+eSIM.
    - Валидируем SKU против каталога перед добавлением.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    count = 0
    skipped_invalid = 0
    
    for sku, model, memory, color, sim_type, price in prices_list:
        if price is None:
            continue

        # Валидация: проверяем, что SKU существует в каталоге
        cursor.execute("SELECT model, memory, color, sim_type, category FROM catalog WHERE sku = ?", (sku,))
        catalog_item = cursor.fetchone()
        
        if not catalog_item:
            skipped_invalid += 1
            logging.warning(f"SKU {sku} не найден в каталоге, пропускаем")
            continue
        
        # Используем данные из каталога для гарантии корректности
        cat_model, cat_memory, cat_color, cat_sim, category = catalog_item
        
        # Базовое имя товара из каталога (или из Excel, если каталог неполный)
        parts = []
        if cat_model or model:
            parts.append(str(cat_model or model).strip())
        if cat_memory or memory:
            parts.append(str(cat_memory or memory).strip())
        if cat_color or color:
            parts.append(str(cat_color or color).strip())

        base_name = " ".join(parts) if parts else str(sku)

        # Нормализуем SIM-тип
        sim_label = None
        sim_raw = str(cat_sim or sim_type).strip() if (cat_sim or sim_type) else None
        if sim_raw:
            low = sim_raw.lower()
            if "sim+esim" in low or ("sim" in low and "esim" in low) or "cellular" in low:
                sim_label = "SIM+eSIM"
            elif "dual" in low:
                sim_label = "Dual"
            elif "esim" in low:
                sim_label = "eSIM"
            elif "gps" in low and "cellular" in low:
                sim_label = "GPS + Cellular"
            elif "gps" in low:
                sim_label = "GPS"
            elif "wi-fi" in low and "cellular" in low:
                sim_label = "Wi-Fi + Cellular"
            elif "wi-fi" in low:
                sim_label = "Wi-Fi"
            else:
                sim_label = sim_raw

        if sim_label:
            product_name = f"{base_name} [{sim_label}]"
        else:
            product_name = base_name

        # Проверяем, есть ли товар у этого продавца
        cursor.execute("SELECT id FROM offers WHERE user_id = ? AND sku = ?", (user_id, sku))
        exists = cursor.fetchone()
        
        if exists:
            # Обновляем и цену, и имя товара, и username
            cursor.execute(
                "UPDATE offers SET price = ?, username = ?, product = ? WHERE id = ?",
                (price, username, product_name, exists[0])
            )
        else:
            cursor.execute(
                "INSERT INTO offers (user_id, username, sku, product, price) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, sku, product_name, price)
            )
        count += 1
    
    conn.commit()
    conn.close()
    
    return count, skipped_invalid

def get_catalog_for_excel(category_filter=None):
    """
    Возвращает каталог товаров Apple для генерации Excel шаблона.
    Формат: список кортежей (sku, model, memory, color, sim_type)
    category_filter: фильтр по категории (iPhone, iPad, Watch, Mac) или None для всех
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if category_filter:
        cursor.execute(
            "SELECT sku, model, memory, color, sim_type FROM catalog WHERE category = ? ORDER BY model, memory, color, sim_type",
            (category_filter,)
        )
    else:
        cursor.execute("SELECT sku, model, memory, color, sim_type FROM catalog ORDER BY category, model, memory, color, sim_type")
    
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_catalog_categories():
    """Возвращает список всех категорий в каталоге"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM catalog ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

def add_product_to_catalog(sku, model, memory, color, sim_type, category):
    """Добавляет товар в каталог"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO catalog (sku, model, memory, color, sim_type, category) VALUES (?, ?, ?, ?, ?, ?)",
            (sku, model, memory, color, sim_type, category)
        )
        conn.commit()
        conn.close()
        return True, "Товар добавлен"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Товар с таким SKU уже существует"
    except Exception as e:
        conn.close()
        return False, f"Ошибка: {str(e)}"

def delete_product_from_catalog(sku):
    """Удаляет товар из каталога"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM catalog WHERE sku = ?", (sku,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        return True, "Товар удален из каталога"
    else:
        return False, "Товар не найден"

def search_catalog(query):
    """Поиск товаров в каталоге по модели или SKU"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sku, model, memory, color, sim_type, category FROM catalog WHERE model LIKE ? OR sku LIKE ? LIMIT 20",
        (f"%{query}%", f"%{query}%")
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

# --- ФУНКЦИИ ДЛЯ WEB APP (НОВЫЕ) ---
def get_all_offers_for_web():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Позволяет обращаться к полям по имени
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, username, sku, product, price FROM offers")
    rows = cursor.fetchall()
    conn.close()
    
    # Превращаем в список словарей (JSON-friendly)
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "seller_id": row["user_id"],
            "username": row["username"],
            "sku": row["sku"],
            "product": row["product"],
            "price": row["price"]
        })
    return result

def delete_offer_by_sku(user_id, sku):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM offers WHERE user_id = ? AND sku = ?", (user_id, sku))
    conn.commit()
    conn.close() 

def update_price_from_web(user_id, product_name, price):
    """
    Обновление цены одного товара из WebApp.
    Ищем по user_id и названию товара (product).
    Возвращаем количество затронутых строк, чтобы понимать, был ли товар найден.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE offers SET price = ? WHERE user_id = ? AND product = ?",
        (price, user_id, product_name)
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected