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
4. Запустить сервис:
```bash
sudo docker-compose --env-file .env up -d
```
5. Сервис доступен по адресу `http://ip_сервера:TIMETAGGER_PORT`, где `TIMETAGGER_PORT` — это порт, указанный в файле `.env`
