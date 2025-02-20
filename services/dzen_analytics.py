import requests
import services.appsflyer_analytics as appsflyer_analytics
from variable import Variable
from datetime import datetime, timedelta


def get_headers():
    """Возвращает заголовки для запросов."""
    _dzen = Variable.get_variable('dzen')
            
    return {
            "cookie": _dzen.get("cookie", ""),
            "X-Csrf-Token": _dzen.get("token", ""),
            "User-Agent": ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36')
        }

def analytics(date_from=None, date_to=None):
    array = []
    page, attempts = 0, 0
    
    while True:
        header = get_headers()
    
        data = fetch_publications(header, page, date_from, date_to)
        
        if is_invalid_csrf_token(data, attempts):
            header = refres_token(header)
            attempts += 1
            continue
        
        if data['status'] != 200:
            return error_response(data, 'dzen')
        
        publications = data['data'].get('publications', [])
        if not publications:
            break
        
        array.extend(parse_publications(publications))
        page += 1
    
    date_from, date_to = set_default_dates(date_from, date_to)
    apps = get_apps()
    
    appsflyer_data = fetch_appsflyer_data(date_from, date_to, apps)
    if appsflyer_data['status'] != 200:
        return {"status": 200, "message": appsflyer_data, "body": array}
    
    return {"status": 200, "message": {}, "body": merge_data(array, appsflyer_data['data'], apps)}

def fetch_publications(header, page, date_from, date_to):
    params = {
        "allPublications": 'true',
        "fields": ["impressions", "deepViews", "comments", "likes", "typeSpecificViews",
                    "subscriptions", "unsubscriptions", "sumInvolvedViewTimeSec", "ctr", "deepViewsRate", "vtr"],
        "sortBy": "subscriptions",
        "sortOrderDesc": 'false',
        "total": "true",
        "totalLimitedByIds": 'false',
        "pageSize": 30,
        "page": page
    }
    if date_from and date_to:
        params.update({'from': date_from, 'to': date_to})
    
    response = requests.get(
        f"https://dzen.ru/editor-api/v2/publisher/{Variable.get_variable('dzen')['editId']}/stats2",
        headers=header, params=params, verify=False)
    return {"status": response.status_code, "data": response.json()}

def is_invalid_csrf_token(data, attempts):
    return (data['status'] == 400 and 
            data["data"].get('errors', [{}])[0].get('type') == 'invalid-csrf-token-error' and 
            attempts == 0)

def error_response(data, service):
    return {"status": data['status'], "message": {"services": service, "response": str(data['data'])}, "body": {}}

def parse_publications(publications):
    parsed_data = []
    for pub in publications:
        if pub['publication']['deleted']:
            continue
        dt = datetime.utcfromtimestamp(int(pub['publication']['addTime']) / 1000)
        stats = pub['stats']
        parsed_data.append({
            "title": pub['publication']['title'],
            "commonUrl": pub['publication']['commonUrl'],
            "date": dt.strftime("%d.%m.%Y"),
            "stats": {key: stats.get(key, "null") for key in stats.keys()}
        })
    return parsed_data

def set_default_dates(date_from, date_to):
    if not date_from or not date_to:
        return (datetime.today() - timedelta(days=1000)).strftime("%Y-%m-%d"), datetime.today().strftime("%Y-%m-%d")
    return date_from, date_to

def fetch_appsflyer_data(date_from, date_to, apps):
    return appsflyer_analytics.analytics(filter={'media_source': ['dzen'],
                                                 "start_date": date_from,
                                                 "end_date": date_to,
                                                 'groupings': ["adset_id"]}, apps=apps)

def merge_data(array, appsflyer_data, apps):
    app_data = {apps[i]['name']: {item["id"]: item for item in appsflyer_data[i]} for i in range(len(appsflyer_data))}
    
    for item in array:
        adset_id = item["commonUrl"].split("/")[-1]
        for app_name, app_dict in app_data.items():
            item[f'{app_name}_appsFlyer'] = app_dict.get(adset_id, None)
    
    return array

def get_apps():
    _apps = Variable.get_variable('apps')
    return _apps

def refres_token(header, attempts = 0):
    
    response = requests.get(f'https://dzen.ru/profile/editor/id/{Variable.get_variable('dzen')['editId']}/publications-stat',
                            headers=header, verify=False, allow_redirects=False)
    
    if attempts == 0:

        header['cookie'] += f'; zencookie={response.cookies.get("zencookie", "")};zen_sso_checked=1'

        token_data = extract_csrf_token(refres_token(header,1))
    
        if token_data:
            Variable.update_variable({"dzen": {"token": token_data, 'cookie': header['cookie']}})
    
        return None
    
    return response.text

def extract_csrf_token(response_text):
    try:
        return response_text.split('"csrfToken":')[1].split(',')[0].replace('\\:', '').replace('"', '')
    except IndexError:
        return None
