from fastapi import FastAPI
from app.modules.device_interaction import api as device_interaction_api

app = FastAPI(
    title="Програмний модуль агрегації та обробки індикаторів безпеки",
    description="API для управління пристроями та іншими компонентами системи безпеки ЗСУ.",
    version="0.1.0"
)

app.include_router(device_interaction_api.router)

@app.get("/")
async def root():
    return {"message": "Ласкаво просимо до API модуля безпеки!"}
