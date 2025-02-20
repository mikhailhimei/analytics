import requests
from collections import defaultdict
import services.appsflyer_analytics as appsflyer_analytics
from datetime import datetime, timedelta
from variable import Variable

def analytics(auth, date_from, date_to):
    array_full_structur, array_parent_id, array_children_id, array_children_children_id = [], [], [], []
    get_id = method_get_id(auth)

    if get_id['status'] != 200:
        return error_response(get_id, 'vk')
    
    for item in get_id['data']['items']:
        if item['status'] == 'blocked' and (date_from or date_to):
            continue
        children, p = [], 0
        campaign_id = campaigns_id(auth, item['id'])
        if campaign_id['status'] != 200:
            return error_response(campaign_id, 'vk')
        
        for h in campaign_id['data']['items']:
            array_children_id.append(h['id'])
            children.append({'parent_id': h['id'], 'name': h['name'], 'status':h['status'], 'children': []})
            banner_id = banners_id(auth, h['id'])
            if banner_id['status'] != 200:
                return error_response(banner_id, 'vk')
            
            for j in banner_id['data']['items']:
                array_children_children_id.append(j['id'])
                children[p]['children'].append({'parent_id': j['id'], 'status':j['status'], 'name': j['name']})
            p += 1
        
        array_parent_id.append(item['id'])
        array_full_structur.append({'parent_id': item['id'], 'name': item['name'], 'status':item['status'], 'children': children})

    if len(array_full_structur) == 0:
        return {"status": 200, "message": {}, "body": array_full_structur}
    
    if not date_from or not date_to:
        yesterday = datetime.today()
        year_ago = datetime.today() - timedelta(days=360)
        date_from, date_to = year_ago.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")

    parent, children, children_children = process_nesting(auth, array_parent_id, array_children_id, array_children_children_id, date_from, date_to)
    stats = {entry['id']: entry for entry in children + children_children + parent}
    full_data = [build_hierarchy(parent, stats) for parent in array_full_structur]

    apps = get_apps()

    appsflyer_data = fetch_appsflyer_data(date_from, date_to, apps)
    if appsflyer_data['status'] != 200:
        return {"status": 200, "message": appsflyer_data, "body": full_data}

    merge_appsflyer_data(full_data, appsflyer_data, apps)
    
    return {"status": 200, "message": {}, "body": full_data}

def error_response(response, service):
    return {"status": response['status'], "message": {"services": service, "response": str(response['data'])}, "body": {}}

def process_nesting(auth, array_parent_id, array_children_id, array_children_children_id, date_from, date_to):
    return (
        fetch_nesting_data(auth, method_nesting_one, array_parent_id, date_from, date_to),
        fetch_nesting_data(auth, method_nesting_two, array_children_id, date_from, date_to),
        fetch_nesting_data(auth, method_nesting_three, array_children_children_id, date_from, date_to)
    )

def fetch_nesting_data(auth, method, id_list, date_from, date_to):
    page, results = 0, []
    while True:
        data = method(auth, id_list, page, date_from, date_to)
        if data['status'] != 200:
            return error_response(data, 'vk')
        if not data['data']['items']:
            break
        results += parent_data(data['data']['items'])
        page += 20
    return results

def fetch_appsflyer_data(date_from, date_to, apps):
    return appsflyer_analytics.analytics(filter={'media_source': ['mail.ru_int'], 'start_date': date_from, 'end_date': date_to, 'groupings': ['adgroup_id', 'campaign_id']}, apps=apps)

def merge_appsflyer_data(full_data, appsflyer, apps):
    if appsflyer['status'] != 200:
        return
    
    for i, x in enumerate(appsflyer['data']):
        mapping = {str(entry['id']): entry for entry in x}
        campaign_mapping = defaultdict(lambda: {"impressions": 0, "revenue": 0.0, "conv_rate": 0.0, "clicks": 0, "gross_profit": 0.0, "combined_conversions": 0, "ctr": 0.0})
        
        for entry in x:
            campaign_id = str(entry.get('campaign_id'))
            if campaign_id:
                for key in campaign_mapping[campaign_id]:
                    if isinstance(entry.get(key), (int, float)):
                        campaign_mapping[campaign_id][key] += entry.get(key, 0)
        
        merge_data(full_data, campaign_mapping, mapping, str(apps[i]['name']))

def method_get_id(header):
    return api_get_request(header, 'ad_plans.json', {'fields': 'id,name,status,max_price,price,package_id,stats_info,campaigns', '_status__in': ['active','blocked'], 'sorting': '-id', 'limit': 50})

def campaigns_id(header, id):
    return api_get_request(header, 'campaigns.json', {'fields': 'id,name,status', '_ad_plan_id__in': id})

def banners_id(header, id):
    return api_get_request(header, 'banners.json', {'fields': 'id,name,status', '_ad_group_id__in': id})

def method_nesting_one(header, id, page, date_from, date_to):
    return api_post_request(header, 'statistics/ad_plans/day.json', id, page, date_from, date_to)

def method_nesting_two(header, id, page, date_from, date_to):
    return api_post_request(header, 'statistics/campaigns/day.json', id, page, date_from, date_to)

def method_nesting_three(header, id, page, date_from, date_to):
    return api_post_request(header, 'statistics/banners/day.json', id, page, date_from, date_to)

def api_get_request(header, endpoint, params):
    params.update(get_params())
    print(params)
    req = requests.get(f'https://ads.vk.com/proxy/mt/v2/{endpoint}', params=params, headers=header, verify=False)
    print(req.json())
    return {"status": req.status_code, "data": req.json()}

def api_post_request(header, endpoint, id, page, date_from, date_to):
    params = get_params()
    data = {"date_from": date_from, "date_to": date_to, "id": id, 'offset': page}
    req = requests.post(f'https://ads.vk.com/proxy/mt/v3/{endpoint}', params=params, headers=header, json=data, verify=False)
    return {"status": req.status_code, "data": req.json()}

def parent_data(data):
    """Обрабатывает данные статистики и формирует список словарей."""
    array = []
    for i in data:
        s = i.get('total', {}).get('base', {})
        array.append({
            "id": i.get("id"),
            "shows": s.get("shows", 0),
            "clicks": s.get("clicks", 0),
            "goals": s.get("goals", 0),
            "spent": s.get("spent", 0.0),
            "cpm": s.get("cpm", 0.0),
            "cpc": s.get("cpc", 0.0),
            "cpa": s.get("cpa", 0.0),
            "ctr": s.get("ctr", 0.0),
            "cr": s.get("cr", 0.0)
        })
    return array

def build_hierarchy(node, stats):
    """Рекурсивно строит иерархию элементов, добавляя статистику."""
    parent_id = node["parent_id"]
    children = [build_hierarchy(child, stats) for child in node.get("children", [])]

    return {
        "id": parent_id,
        "name": node["name"],
        "status": node['status'],
        "stats": stats.get(parent_id, {}),  # Берем данные, если есть
        "children": children
    }

from collections import defaultdict

def merge_data(nodes, campaign_mapping, id_mapping, name_app):
    """Объединяет данные из AppsFlyer и VK Ads в общую структуру."""
    for node in nodes:
        node_id = str(node.get("id"))
        node.setdefault(f'{name_app}_appsFlyer', {})  # Используем словарь вместо списка
        
        if node_id in campaign_mapping:
            node[f'{name_app}_appsFlyer'].update(campaign_mapping[node_id])
        if node_id in id_mapping:
            node[f'{name_app}_appsFlyer'].update(id_mapping[node_id])
        
        if "children" in node:
            merge_data(node["children"], campaign_mapping, id_mapping, f'{name_app}')
            
            # Суммируем appsf детей для родителя
            parent_appsf = defaultdict(float)
            for child in node["children"]:
                for key, value in child.get(f'{name_app}_appsFlyer', {}).items():
                    if isinstance(value, (int, float)):
                        parent_appsf[key] += value
            
            if parent_appsf:
                node[f'{name_app}_appsFlyer'].update(dict(parent_appsf))

def get_apps():
    _apps = Variable.get_variable('apps')
    return _apps

def get_params():
    _vk = Variable.get_variable('vk')
    return {'account':_vk['account'], 'sudo':_vk['sudo']}