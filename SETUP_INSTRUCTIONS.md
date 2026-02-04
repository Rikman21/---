# Инструкция по настройке бота для работы в Telegram

## Проблема
WebApp в Telegram показывает вечную загрузку, потому что `index.html` пытается обратиться к локальному адресу `http://127.0.0.1:8080`, который недоступен из интернета.

## Решение: Настройка публичного доступа к API

У вас есть два варианта:

---

## Вариант 1: Использование вашего сервера (РЕКОМЕНДУЕТСЯ)

### Шаг 1: Загрузите файлы на сервер

1. Загрузите на сервер файлы:
   - `main.py`
   - `database.py`
   - `requirements.txt`
   - `market.db` (если база уже создана)

### Шаг 2: Установите зависимости на сервере

```bash
pip install -r requirements.txt
```

### Шаг 3: Настройте веб-сервер (Nginx или Apache)

**Для Nginx** создайте конфигурацию `/etc/nginx/sites-available/gorbushka`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Замените на ваш домен

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Включите конфигурацию:
```bash
sudo ln -s /etc/nginx/sites-available/gorbushka /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Шаг 4: Настройте SSL (HTTPS) - ОБЯЗАТЕЛЬНО!

Telegram требует HTTPS для WebApp. Используйте Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Шаг 5: Запустите бота на сервере

Создайте systemd сервис `/etc/systemd/system/gorbushka-bot.service`:

```ini
[Unit]
Description=Gorbushka Telegram Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/bot
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /path/to/bot/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Запустите:
```bash
sudo systemctl enable gorbushka-bot
sudo systemctl start gorbushka-bot
sudo systemctl status gorbushka-bot
```

### Шаг 6: Обновите `index.html`

В файле `index.html` найдите строку:
```javascript
const API_BASE = urlParams.get('api') || 'https://your-server.com';
```

Замените `'https://your-server.com'` на адрес вашего сервера:
```javascript
const API_BASE = urlParams.get('api') || 'https://your-domain.com';
```

### Шаг 7: Загрузите обновленный `index.html` на GitHub Pages

1. Закоммитьте изменения в `index.html`
2. Запушьте на GitHub
3. GitHub Pages автоматически обновится

---

## Вариант 2: Использование ngrok (для тестирования)

Если у вас нет сервера или нужно быстро протестировать:

### Шаг 1: Установите ngrok

Скачайте с https://ngrok.com/download

### Шаг 2: Запустите ваш бот локально

```bash
python main.py
```

### Шаг 3: В другом терминале запустите ngrok

```bash
ngrok http 8080
```

Вы получите публичный URL вида: `https://xxxx-xx-xx-xx-xx.ngrok-free.app`

### Шаг 4: Обновите `index.html`

Замените в `index.html`:
```javascript
const API_BASE = urlParams.get('api') || 'https://xxxx-xx-xx-xx-xx.ngrok-free.app';
```

**ВАЖНО:** ngrok бесплатный план меняет URL при каждом перезапуске. Для продакшена используйте сервер!

---

## Вариант 3: Использование параметра URL (временное решение)

Можно передать адрес API через URL параметр в `main.py`:

В `main.py` измените:
```python
full_url = f"{WEB_APP_URL}?uid={user_id}&api=https://your-server.com"
```

Тогда в `index.html` адрес будет браться из параметра `api`.

---

## Проверка работы

1. Откройте в браузере: `https://your-server.com/api/offers`
2. Должен вернуться JSON с товарами (может быть пустой массив `[]`)
3. Откройте бота в Telegram и нажмите "ОТКРЫТЬ МАРКЕТ"
4. Должна загрузиться страница без вечной загрузки

---

## Отладка

Если не работает:

1. **Проверьте логи бота:**
   ```bash
   sudo journalctl -u gorbushka-bot -f
   ```

2. **Проверьте доступность API:**
   ```bash
   curl https://your-server.com/api/offers
   ```

3. **Проверьте CORS заголовки** - они должны быть настроены в `main.py` (уже есть)

4. **Откройте консоль браузера в Telegram:**
   - В Telegram Desktop: View → Developer Tools → Console
   - Посмотрите ошибки загрузки

---

## Быстрая настройка для вашего сервера

Если у вас уже есть сервер с доменом:

1. **Скопируйте файлы на сервер:**
   ```bash
   scp main.py database.py requirements.txt user@your-server:/path/to/bot/
   ```

2. **На сервере установите зависимости:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Настройте Nginx** (см. выше)

4. **Обновите `index.html`** с адресом вашего сервера

5. **Запустите бота** через systemd или screen/tmux

6. **Загрузите обновленный `index.html` на GitHub**

---

## Контакты для помощи

Если что-то не работает, проверьте:
- ✅ Бот запущен и работает
- ✅ API доступен по HTTPS
- ✅ CORS заголовки настроены
- ✅ `index.html` обновлен с правильным адресом API
- ✅ GitHub Pages обновлен
