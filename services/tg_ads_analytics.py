import requests
import services.appsflyer_analytics as appsflyer_analytics
from datetime import datetime, timedelta
from variable import Variable

def get_headers():
    """Возвращает заголовки для запросов."""
    _tgAds = Variable.get_variable('tgAds')
    return {
        "x-access-token": _tgAds["token"],
        "x-refresh-token": _tgAds['refresh_token'],
        'x-elama-private-office-id': _tgAds['_ugeuid'],
        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
    }

def refresh_token():
    """Обновляет токен и сохраняет его в переменную."""
    req = requests.post('https://new.elama.ru/api/refresh-token', headers=get_headers(), json={}, verify=False)
    if req.status_code == 200:
        Variable.update_variable({
            "tgAds": {
                "token": req.json()['accessToken'],
                "refresh_token": req.json()['refreshToken']
            }
        })
    return req.status_code

def check_auth():
    """Проверяет авторизацию и обновляет токен при необходимости."""
    req = requests.get('https://new.elama.ru/api/me', headers=get_headers(), verify=False)
    if req.status_code == 200:
        return 200
    return 201 if refresh_token() == 200 else 403

def fetch_ads(page, from_date, until_date):
    """Запрашивает данные о рекламе."""
    params = {
        "limit": "50",
        "offset": page,
        "filter": f"group in ['{Variable.get_variable("tgAds")["_gid"]}']"
    }
    if from_date or until_date:
        params.update({"periodFrom": from_date, "periodTo": until_date})
    
    req = requests.get(f'https://new.elama.ru/api/tgd-service/v1/elama-{Variable.get_variable("tgAds")["_id"]}/ad', headers=get_headers(), params=params, verify=False)
    return {"status": req.status_code, "data": req.json()}

def fetch_appsflyer_data(from_date, until_date):
    """Запрашивает аналитику из Appsflyer."""
    _apps = get_apps()
    return appsflyer_analytics.analytics(filter={'media_source': ['telegram_ads'], 
                                                 "start_date": from_date, 
                                                 "end_date": until_date, 
                                                 'groupings': ["adset_id"]}, apps=_apps)

def get_apps():
    _apps = Variable.get_variable('apps')
    return _apps

def analytics(from_date=None, until_date=None):
    """Основная функция аналитики."""
    ads_data = []
    page = 0
    
    while True:
        if check_auth() == 403:
            return {"status": 403, "message": {'services': 'tgAds', 'response': 'Invalid token'}, "body": {}}
        
        data = fetch_ads(page, from_date, until_date)
        if data['status'] != 200:
            return {"status": data['status'], "message": {'services': 'tgAds', 'response': str(data['data'])}, "body": {}}
        
        if not data['data']['items']:
            break
        
        for item in data['data']['items']:
            if (from_date or until_date) and item['impressions'] == 0:
                continue
            ads_data.append({
                "id": item['advertisementId'],
                "title": item['advertisementName'],
                'createdAt': item.get('createdAt', ''),
                "status": item.get('status', ''),
                "stats": {
                    "cpm": round(float(item['cpm']['amountForDisplay']), 2),
                    "budget": round(float(item['budgetBalance']["amountForDisplay"]), 2),
                    "cpc": round(float(item["cpc"]['amountForDisplay']), 2) if item['cpc'] else '',
                    "clicks": item['clicks'],
                    "cpsCpj": float(item['cpsCpj']['amountForDisplay']),
                    'crPercent': round(item.get('crPercent', 0), 2),
                    'ctrPercent': item.get('ctrPercent', ''),
                    'expenses': item['expenses'].get('amountForDisplay', ''),
                    'impressions': item.get('impressions', ''),
                    'subscriptions': item.get('subscriptions', ''),
                    'telegramId': item.get('telegramId', '')
                }
            })
        
        page += 50

    if len(ads_data) == 0:
        return {"status": 200, "message": {}, "body": ads_data}

    if not from_date or not until_date:
        until_date = datetime.today().strftime("%Y-%m-%d")
        from_date = (datetime.today() - timedelta(days=1000)).strftime("%Y-%m-%d")
    
    appsflyer_data = fetch_appsflyer_data(from_date, until_date)
    if appsflyer_data['status'] != 200:
        return {"status": 200, "message": appsflyer_data, "body": ads_data}
    
    app_data = {apps['name']: {item["id"]: item for item in appsflyer_data['data'][i]} 
                for i, apps in enumerate(get_apps())}
    
    for item in ads_data:
        adset_id = item["title"]
        for app_name, app_dict in app_data.items():
            item[f'{app_name}_appsFlyer'] = app_dict.get(adset_id, None)
    
    return {"status": data['status'], "message": {}, "body": ads_data}
