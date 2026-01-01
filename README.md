# My Timetagger

Данный репозиторий содержит полезные файлы для настройки self-hosted версии сервиса [Timetagger](https://timetagger.app/).

# Установка и запуск

1. Скопировать репозиторий на свой сервер:
```bash
git clone https://github.com/PE51K/my-timetagger
cd my-timetagger
```
2. Установить docker и docker-compose
3. Создать файл `.env` на основе `.env.example` и заполнить его своими данными (хеш пароля можно сгенерировать вот [тут](https://timetagger.app/cred), нужны `raw credentials`)
```bash
cp .env.example .env
```
4. Запустить сервис Timetagger:
```bash
sudo docker-compose --env-file .env up -d timetagger
```
5. Сервис доступен по адресу `http://ip_сервера:TIMETAGGER_PORT`, где `TIMETAGGER_PORT` — это порт, указанный в файле `.env`

## Analytics App (опционально)

В репозитории также включено приложение для аналитики времени, которое предоставляет визуализацию данных Timetagger.

### Установка Analytics App

1. **Сначала запустите Timetagger** (см. инструкции выше)

2. **Определите путь к базе данных внутри контейнера:**
   ```bash
   # Зайдите в контейнер Timetagger
   docker exec -it <timetagger_container_name> sh
   
   # Найдите путь к базе данных
   find ${TIMETAGGER_DATADIR} -name "*.db" -type f
   
   # Или проверьте структуру
   ls -la ${TIMETAGGER_DATADIR}/_timetagger/users/
   ```
   
   Путь будет выглядеть примерно так: `${TIMETAGGER_DATADIR}/_timetagger/users/pe51k~cGU1MWs=.db`

3. **Обновите файл `.env`**, добавив переменные для Analytics:
   ```bash
   ANALYTICS_PORT=8501
   TIMETAGGER_DB_PATH=/data/timetagger/_timetagger/users/pe51k~cGU1MWs=.db
   ```
   
   ⚠️ **Важно:** `TIMETAGGER_DB_PATH` должен соответствовать пути внутри контейнера после монтирования тома. 
   Если `TIMETAGGER_DATADIR=/data/timetagger`, то путь будет `/data/timetagger/_timetagger/users/pe51k~cGU1MWs=.db`

4. **Запустите Analytics App:**
   ```bash
   sudo docker-compose --env-file .env up -d analytics
   ```

5. Приложение будет доступно по адресу `http://ip_сервера:ANALYTICS_PORT`

Подробнее см. [analytics_app/README.md](analytics_app/README.md)
