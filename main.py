import os
import shutil
import logging
import uuid
from typing import List

from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.config import Config

# Загрузка конфигурации из .env файла
config = Config(".env")
UPLOAD_DIR = config("UPLOAD_DIR", default="images")  # Директория для загрузки файлов
MAX_FILE_SIZE_MB = config("MAX_FILE_SIZE_MB", cast=int, default=5)  # Максимальный размер файла в мегабайтах

# Создание директории для загрузки файлов, если её нет
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Настройка логгирования
LOG_DIR = os.getenv("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "app.log"),  # Файл для логов
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",  # Формат сообщения лога
    datefmt="%Y-%m-%d %H:%M:%S"  # Формат даты и времени
)

# Инициализация приложения FastAPI
app = FastAPI()

# Подключение статических файлов (изображения и статика)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

# Шаблонизатор Jinja2 для отображения HTML-шаблонов
templates = Jinja2Templates(directory="app/templates")


@app.get("/")  # Стартовая страница
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/upload")  # Страница загрузки файлов
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/upload")  # Обработка POST-запроса на загрузку файла
async def upload_file(file: UploadFile = File(...)):
    # Проверка MIME-типа файла
    if file.content_type not in {"image/jpeg", "image/png", "image/gif"}:
        logging.error(f"Ошибка: неподдерживаемый формат файла ({file.filename})")
        raise HTTPException(status_code=400, detail="Неподдерживаемый тип файла")

    # Определение размера файла
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    # Проверка максимального размера файла
    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        logging.error(f"Ошибка: файл {file.filename} превышает размер")
        raise HTTPException(status_code=400, detail="Файл превышает допустимый размер")

    # Генерация уникального имени файла с сохранением расширения
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    # Сохранение файла
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    logging.info(f"Успех: изображение {unique_name} загружено.")

    # Возврат URL для доступа к загруженному файлу
    return {"url": f"/images/{unique_name}"}


@app.get("/images")  # Страница со списком загруженных изображений
async def images_page(request: Request, page: int = 1):
    per_page = 50  # Количество изображений на странице
    files = sorted(os.listdir(UPLOAD_DIR))  # Получение списка файлов
    total_files = len(files)
    start = (page - 1) * per_page  # Начало текущей страницы
    end = start + per_page  # Конец текущей страницы
    paginated_files = files[start:end]  # Файлы текущей страницы

    # Подготовка данных для отображения
    images = [{"name": f, "url": f"/images/{f}"} for f in paginated_files]
    has_next = end < total_files  # Есть ли следующая страница

    return templates.TemplateResponse("images.html", {
        "request": request,
        "images": images,
        "page": page,
        "has_next": has_next
    })


@app.post("/delete-selected")  # Удаление нескольких файлов
async def delete_selected(filenames: List[str] = Form(...)):
    deleted = []  # Список удалённых файлов
    not_found = []  # Список не найденных файлов

    for filename in filenames:
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            deleted.append(filename)
            logging.info(f"Файл {filename} удалён.")
        else:
            not_found.append(filename)
            logging.error(f"Ошибка: файл {filename} не найден при удалении.")

    return {"deleted": deleted, "not_found": not_found}


@app.post("/delete/{filename}")  # Удаление одного файла
async def delete_image(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        logging.info(f"Файл {filename} удалён.")
        return {"detail": "Файл удалён"}
    else:
        logging.error(f"Ошибка: файл {filename} не найден при удалении.")
        raise HTTPException(status_code=404, detail="Файл не найден")


if __name__ == "__main__":
    # Запуск сервера Uvicorn
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
