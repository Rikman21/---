import sqlite3
import logging

DB_NAME = "market.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

# --- ФУНКЦИИ ДЛЯ EXCEL ---
def update_prices_from_excel(user_id, username, prices_list):
    """
    prices_list: список кортежей (sku, price). Если price=None, товар не трогаем.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Сначала удаляем старые товары этого продавца (чтобы обновить прайс целиком)
    #    Или можно делать умное обновление, но для простоты перезапишем.
    #    В данной версии мы просто обновляем цены или вставляем новые.
    
    count = 0
    for sku, price in prices_list:
        if price is None: continue
        
        # Получаем имя продукта из каталога (по хорошему надо хранить каталог в БД, 
        # но пока берем из SKU, предполагая что SKU уникален и содержит имя, 
        # либо продавец должен передать имя. 
        # В нашей упрощенной схеме Excel мы не передаем имя продукта во 2-й раз.
        # Поэтому делаем хитро: имя берем из SKU (если SKU это и есть имя) или ищем в базе.
        # ДЛЯ ПРОСТОТЫ: В текущем Excel SKU = Модель + Память...
        product_name = sku 
        
        # Проверяем, есть ли товар
        cursor.execute("SELECT id FROM offers WHERE user_id = ? AND sku = ?", (user_id, sku))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute("UPDATE offers SET price = ?, username = ? WHERE id = ?", (price, username, exists[0]))
        else:
            cursor.execute("INSERT INTO offers (user_id, username, sku, product, price) VALUES (?, ?, ?, ?, ?)",
                           (user_id, username, sku, product_name, price))
        count += 1
        
    conn.commit()
    conn.close()
    return count

def get_catalog_for_excel():
    # Эта функция должна возвращать полный список возможных товаров.
    # Пока вернем пустой список или базовый, если нужно.
    # В идеале здесь должен быть список всех моделей iPhone.
    return []

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