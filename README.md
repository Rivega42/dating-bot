# 🤖 Dating Bot Platform

Платформа для автоматизации VK Mini App dating-симуляторов.

## 🚀 Быстрый старт

### Требования
- Ubuntu 22.04 LTS
- 4+ GB RAM
- 2+ vCPU
- 40+ GB SSD

### Установка

```bash
# На чистом сервере с root доступом:
curl -sSL https://raw.githubusercontent.com/Rivega42/dating-bot/main/scripts/install.sh | sudo bash
```

### После установки

```bash
cd /home/datingbot/dating-bot
nano .env  # Заполните данные Beget
make restart
make health
```

## 📖 Документация

- **API**: http://your-server:8000/docs
- **Grafana**: http://your-server:3000
- **Prometheus**: http://your-server:9090

## 🔧 Команды

```bash
make start      # Запуск
make stop       # Остановка
make logs       # Логи
make health     # Проверка
make backup     # Бэкап
```

## 📁 Структура

```
dating-bot/
├── api/           # FastAPI backend
├── worker/        # Playwright workers
├── monitoring/    # Prometheus + Grafana
├── nginx/         # Reverse proxy
├── postgres/      # Database schema
├── scripts/       # Automation
└── .github/       # CI/CD
```

## 📊 Мониторинг

Алерты отправляются в Telegram:
- 🔴 Critical - сервис упал
- 🟡 Warning - нагрузка растёт
- 📈 Scale Up - пора добавить worker

## 🔐 SSL

```bash
sudo ./scripts/setup-ssl.sh yourdomain.com
```
