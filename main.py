import uvicorn

import services.dzen_analytics as dzen_analytics
import services.tg_ads_analytics as tg_ads_analytics
import services.vk_analytics as vk_analytics

from variable import Item, Variable
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# Разрешаем запросы из любых источников (Google Sheets в том числе)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_token(authorization: str = Header(None)):
    valid_token = "TOKEN"  # Замените на реальный токен
    if authorization != valid_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    return authorization

#Обновление токена руками
@app.post("/api/update/variable")
def post_update_variable(item: Item, authorization: str = Depends(verify_token)):
    Variable.update_variable(item.data)

#Аналитика дзен
@app.get("/api/analytics/dzen")
def get_data_dzen(authorization: str = Depends(verify_token), from_date: str = Query(None), until_date: str = Query(None)):
    return dzen_analytics.analytics(from_date, until_date)

#Аналитика вк
@app.get("/api/analytics/vk")
def get_data_vk(authorization: str = Depends(verify_token), from_date: str = Query(None), until_date: str = Query(None)):
    _vk = Variable.get_variable('vk')
    return vk_analytics.analytics(_vk,from_date,until_date)

#Аналитика тг эдс
@app.get("/api/analytics/tgads")
def get_data_tg_ads(authorization: str = Depends(verify_token), from_date: str = Query(None), until_date: str = Query(None)):
    return tg_ads_analytics.analytics(from_date, until_date)

if __name__ == "__main__":
    Variable.set_variable()
    uvicorn.run(app, host="0.0.0.0", port=8888)