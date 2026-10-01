# Team Issue Tracker API

Учебный backend-проект на Django REST Framework — REST API для работы с командами, проектами, задачами и комментариями.

Проект делался с упором не только на CRUD, но и на бизнес-логику: роли внутри команды, ограничения доступа, жизненный цикл задач, audit log, фоновые задачи через Celery, Docker и CI.

## Возможности

- команды и участники команд;
- роли `owner`, `manager`, `member` внутри конкретной команды;
- проекты, принадлежащие командам;
- задачи с исполнителем, приоритетом и статусом;
- отдельные правила доступа для разных ролей;
- контролируемые переходы статусов задач;
- комментарии к задачам;
- история изменений задач;
- фильтрация, поиск и сортировка задач;
- фоновая Celery-задача при создании issue;
- PostgreSQL и Redis;
- запуск через Docker Compose;
- Ruff для форматирования и линтинга;
- GitHub Actions CI;
- OpenAPI-схема и Swagger UI через `drf-spectacular`;
- 58 автоматических тестов.

## Стек

- Python 3.14
- Django 6.1
- Django REST Framework 3.18
- PostgreSQL 18
- Celery 5.6.3
- Redis 8
- psycopg 3
- drf-spectacular 0.30.0
- Docker / Docker Compose
- Ruff 0.16.9
- GitHub Actions

## Предметная модель

```text
User
 │
 └── TeamMembership ─── Team
                         │
                         └── Project
                              │
                              └── Issue
                                   │
                                   ├── Comment
                                   │
                                   └── IssueHistory
```

Роль пользователя хранится не в `User`, а в `TeamMembership`, потому что один и тот же пользователь может иметь разные роли в разных командах.

Доступные роли:

- `owner`
- `manager`
- `member`

При создании команды её создатель автоматически получает роль `owner`.

## Права доступа

Все основные API endpoints требуют аутентификацию.

### Teams

Список команд доступен аутентифицированным пользователям. Это сделано намеренно: команды сами по себе не скрываются по membership.

Поддерживаются:

- просмотр списка команд;
- создание команды;
- просмотр участников команды;
- добавление участника в команду.

Получение, изменение и удаление отдельной команды через `/api/teams/{id}/` не поддерживаются.

Список участников может получить только участник этой команды. Добавлять новых участников может только `owner`. Через membership endpoint нельзя назначить второго `owner`, а повторно добавить уже состоящего в команде пользователя нельзя.

### Projects

Пользователь видит только проекты тех команд, в которых он состоит.

- `owner` и `manager` могут создавать проекты;
- `owner` и `manager` могут изменять и удалять проекты;
- `member` может просматривать проекты своей команды;
- после создания нельзя перенести проект в другую команду.

### Issues

Пользователь видит только задачи проектов своих команд.

- любой участник команды может создать задачу;
- `owner` и `manager` могут изменять любые задачи своей команды;
- `member` может изменять задачу, только если он её создатель или исполнитель;
- `owner` и `manager` могут удалять задачи;
- `member` не может удалять задачи;
- исполнителем можно назначить только пользователя из команды проекта;
- после создания задачу нельзя перенести в другой проект;
- статус нельзя менять обычным `PATCH` — для этого используется отдельный action.

### Comments

Пользователь видит комментарии только к задачам своих команд.

- любой участник команды может создать комментарий;
- `owner` и `manager` могут редактировать и удалять любые комментарии своей команды;
- `member` может редактировать и удалять только свои комментарии;
- после создания комментарий нельзя перенести к другой задаче.

## Жизненный цикл Issue

Статусы:

```text
new
in_progress
done
```

Разрешённые переходы:

```text
new -> in_progress
in_progress -> new
in_progress -> done
done -> in_progress
```

Переходы `new -> done` и `done -> new` запрещены.

Смена статуса вынесена в отдельную функцию сервисного слоя `change_issue_status()`.

При изменении статуса автоматически обновляются временные поля:

- `started_at` устанавливается при первом переходе в `in_progress`;
- `completed_at` устанавливается при переходе в `done`;
- при возврате из `done` в `in_progress` поле `completed_at` очищается;
- первое значение `started_at` при повторном открытии задачи не теряется.

## Audit log

Изменения задачи сохраняются в `IssueHistory`.

Для обычного обновления отслеживаются:

- `title`;
- `description`;
- `priority`;
- `assignee`.

Переходы статуса также записываются в историю.

Каждая запись содержит:

- пользователя, выполнившего изменение;
- изменённое поле;
- старое значение;
- новое значение;
- время изменения.

Если одним запросом изменено несколько отслеживаемых полей, создаётся несколько записей истории.

## Celery и Redis

После успешного создания задачи ставится фоновая Celery-задача:

```text
POST /api/issues/
        │
        ▼
transaction.atomic()
        │
        ▼
успешный commit в PostgreSQL
        │
        ▼
transaction.on_commit(...)
        │
        ▼
Redis
        │
        ▼
Celery worker
        │
        ▼
notify_issue_created(issue_id)
```

В очередь передаётся только `issue_id`. Worker самостоятельно получает объект из PostgreSQL и пишет сообщение о созданной задаче в лог.

Реальная отправка email в проекте не реализована — текущая задача сделана для отработки Celery, Redis и корректной работы с транзакциями.

## API

Все пути ниже имеют префикс `/api/`.

### Teams

| Метод | Endpoint | Описание |
| --- | --- | --- |
| GET | `/teams/` | Список команд |
| POST | `/teams/` | Создание команды; создатель становится owner |
| GET | `/teams/{id}/members/` | Список участников команды |
| POST | `/teams/{id}/members/` | Добавление участника; только owner |

### Projects

| Метод | Endpoint | Описание |
| --- | --- | --- |
| GET | `/projects/` | Список доступных проектов |
| POST | `/projects/` | Создание проекта |
| GET | `/projects/{id}/` | Получение проекта |
| PUT / PATCH | `/projects/{id}/` | Изменение проекта |
| DELETE | `/projects/{id}/` | Удаление проекта |

### Issues

| Метод | Endpoint | Описание |
| --- | --- | --- |
| GET | `/issues/` | Список доступных задач |
| POST | `/issues/` | Создание задачи |
| GET | `/issues/{id}/` | Получение задачи |
| PUT / PATCH | `/issues/{id}/` | Изменение задачи |
| DELETE | `/issues/{id}/` | Удаление задачи |
| POST | `/issues/{id}/change-status/` | Смена статуса с проверкой перехода |
| GET | `/issues/{id}/history/` | История изменений задачи |

Для списка задач поддерживаются query-параметры:

```text
?status=in_progress
?priority=high
?search=authorization
?ordering=-created_at
```

`search` ищет по `title` и `description` без учёта регистра.

Допустимые поля сортировки:

```text
id
created_at
updated_at
priority
```

Для обратного порядка используется `-`, например `?ordering=-created_at`.

### Comments

| Метод | Endpoint | Описание |
| --- | --- | --- |
| GET | `/comments/` | Список доступных комментариев |
| POST | `/comments/` | Создание комментария |
| GET | `/comments/{id}/` | Получение комментария |
| PUT / PATCH | `/comments/{id}/` | Изменение комментария |
| DELETE | `/comments/{id}/` | Удаление комментария |

## Swagger / OpenAPI

Документация генерируется с помощью `drf-spectacular`.

После запуска приложения доступны:

```text
OpenAPI schema: http://127.0.0.1:8000/api/schema/
Swagger UI:     http://127.0.0.1:8000/api/schema/swagger-ui/
ReDoc:          http://127.0.0.1:8000/api/schema/redoc/
```

Версия API в документации — `1.0.0`.

Для проверки схемы:

```bash
python manage.py spectacular --file schema.yml --validate
```

Для нестандартных actions схема уточняется через `@extend_schema`. В частности, отдельно описаны request/response для смены статуса, истории задачи и membership endpoint.

## Аутентификация

В проекте используется стандартная конфигурация аутентификации Django REST Framework и `IsAuthenticated` для основных ViewSet.

Отдельного API для регистрации, login или JWT сейчас нет. Для разработки пользователей можно создавать через Django admin или Django shell.

Админка:

```text
http://127.0.0.1:8000/admin/
```

## Переменные окружения

Создайте `.env` на основе `.env.example`.

Пример локальной конфигурации:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

CELERY_BROKER_URL=redis://localhost:6379/0

SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
```

`.env` не должен попадать в Git.

Настройки `DEBUG`, `ALLOWED_HOSTS`, `SECRET_KEY` и HTTPS-параметры читаются из переменных окружения, чтобы локальная и будущая production-конфигурации не требовали изменения исходного кода.

## Запуск через Docker Compose

Полный development-стек состоит из четырёх сервисов:

```text
web       Django
postgres  PostgreSQL
redis     Redis broker
worker    Celery worker
```

Создать `.env`:

```powershell
Copy-Item .env.example .env
```

Собрать и запустить контейнеры:

```bash
docker compose up -d --build
```

Применить миграции:

```bash
docker compose exec web python manage.py migrate
```

Создать суперпользователя:

```bash
docker compose exec web python manage.py createsuperuser
```

Запустить тесты внутри контейнера:

```bash
docker compose exec web python manage.py test
```

Посмотреть логи:

```bash
docker compose logs -f web
docker compose logs -f worker
```

Остановить сервисы:

```bash
docker compose down
```

Для PostgreSQL и Redis используются named volumes. Обычный `docker compose down` их не удаляет.

`web` сейчас запускается через Django `runserver`, поэтому текущий Docker Compose предназначен для разработки, а не для публичного production-развёртывания.

## Локальный запуск без Docker для Django

Для локального запуска нужны доступные PostgreSQL и Redis.

Создание виртуального окружения в Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Установка зависимостей:

```powershell
python -m pip install -r requirements-dev.txt
```

После заполнения `.env`:

```powershell
python manage.py migrate
python manage.py runserver
```

Celery worker удобнее запускать через Docker Compose, чтобы не зависеть от особенностей локальной ОС.

## Тесты

Полный набор тестов:

```bash
python manage.py test
```

На текущем этапе в проекте **58 тестов**.

Тестами проверяются, в частности:

- права доступа к проектам, задачам и комментариям;
- изоляция данных между командами;
- назначение исполнителя только из нужной команды;
- ограничения для `member`;
- переходы статусов;
- `started_at` и `completed_at`;
- audit history;
- создание нескольких записей истории при изменении нескольких полей;
- постановка Celery-задачи только после успешного commit транзакции.

## Ruff

Проверить линтинг:

```bash
ruff check .
```

Проверить форматирование:

```bash
ruff format . --check
```

Автоматически отформатировать код:

```bash
ruff format .
```

Файлы миграций исключены из проверки Ruff через `pyproject.toml`.

## CI

GitHub Actions запускается на `push` и `pull_request`.

Pipeline выполняет:

1. checkout репозитория;
2. запуск PostgreSQL 18 как service container;
3. установку Python 3.14;
4. установку зависимостей из `requirements-dev.txt`;
5. `ruff format . --check`;
6. `ruff check .`;
7. `python manage.py check`;
8. `python manage.py makemigrations --check --dry-run`;
9. полный `python manage.py test`.

Workflow находится в:

```text
.github/workflows/ci.yml
```

## Структура проекта

```text
.
├── comments/             # комментарии
├── config/               # настройки Django, URL, Celery config
├── history/              # audit log задач
├── issues/               # задачи, service layer, Celery task
├── projects/             # проекты
├── teams/                # команды и membership
├── users/                # кастомная модель User
├── .github/workflows/    # GitHub Actions
├── compose.yaml          # Docker Compose
├── Dockerfile
├── pyproject.toml        # настройки Ruff
├── requirements.txt      # runtime-зависимости
└── requirements-dev.txt  # runtime + инструменты разработки
```

## Состояние проекта

На текущем этапе MVP закончен: основная бизнес-логика, тесты, Celery/Redis, Docker, Ruff, CI и OpenAPI-документация работают.

Публичный production deploy пока не выполнялся. Перед реальным развёртыванием потребуется отдельно настроить production WSGI/ASGI-сервер, reverse proxy, HTTPS, домен, production security settings, резервное копирование и мониторинг.

Также в текущей версии нет:

- отдельного API регистрации и JWT-аутентификации;
- реальной отправки email;
- публичного production URL.
