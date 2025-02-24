import requests
import time
from variable import Variable


def analytics(filter, apps):
    """Получает аналитику AppsFlyer для каждого приложения в списке."""
    global_data = []

    for app in apps:
        filter["app_id"] = [app["id"]]
        appsflyer_response = fetch_data(filter, 0)

        if appsflyer_response["status"] != 200:
            return {
                "status": appsflyer_response["status"],
                "services": "appsflyer",
                "response": str(appsflyer_response["data"])
            }

        # Обрабатываем только, если есть данные
        if "data" in appsflyer_response["data"]:
            data = [
                {
                    "installs": i.get("installs", 0),
                    "loyal_rate": i.get("loyal_rate", 0),
                    "impressions": i.get("impressions", 0),
                    "revenue": i.get("revenue", 0),
                    "conv_rate": i.get("conv_rate", 0),
                    "campaign_id": i.get("campaign_id", 0),
                    "clicks": i.get("clicks", 0),
                    "gross_profit": i.get("gross_profit", 0),
                    "click_installs": i.get("click_installs", 0),
                    "installs_ua": i.get("installs_ua", 0),
                    "sessions": i.get("sessions", 0),
                    "loyals": i.get("loyals", 0),
                    "id": i.get("adgroup_id", i.get("adset_id", "")),
                    "combined_conversions": i.get("combined_conversions", 0),
                    "ctr": i.get("ctr", 0),
                }
                for i in appsflyer_response["data"]["data"]
            ]
        else:
            data = []

        global_data.append(data)

    return {"status": appsflyer_response["status"], "data": global_data}


def fetch_data(filter, retry_count):
    """Отправляет запрос в AppsFlyer API и обрабатывает возможные ошибки."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "Cookie": get_data('appsFlyer')["cookie"],
    }

    body = {
        "filters": {
            "app_id": filter["app_id"],
            "media_source": filter["media_source"],
        },
        "kpis": [
            "installs",
            "installs_reattr",
            "installs_retarget",
            "installs_ua",
            "impressions",
            "clicks",
            "revenue",
            "sessions",
            "roi",
            "arpu",
            "avg_ecpi",
            "install_cost",
            "click_installs",
            "impression_installs",
            "conv_rate",
            "loyals",
            "loyal_rate",
            "uninstalls",
            "uninstall_rate",
            "roas",
            "gross_profit",
            "ctr",
            "cpm",
            "cpc",
            "skan_installs",
            "skan_revenue",
        ],
        "start_date": filter["start_date"],
        "sort_by": [["combined_conversions", "desc"]],
        "limit": 100,
        "end_date": filter["end_date"],
        "groupings": filter["groupings"],
    }

    response = requests.post(
        "https://hq1.appsflyer.com/unified/data?widget=ltv-table:3",
        headers=headers,
        json=body,
        verify=False,
    )

    try:
        data = response.json()
        return {"status": response.status_code, "data": data}

    except:
        if response.status_code == 202:
            if retry_count == 0:
                time.sleep(10)
                return fetch_data(filter, retry_count + 1)
            return {"status": 202, "data": "Accepted"}

        if retry_count == 0:
            refresh_auth()
            return fetch_data(filter, retry_count + 1)

        return {"status": 500, "data": response.text}


def refresh_auth():
    auth_data = get_data('appsFlyer_auth')
    """Авторизуется в AppsFlyer и обновляет cookie-токен."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Content-Type": "application/json;charset=UTF-8",
    }

    body = {
        "username": auth_data['login'],
        "password": auth_data['passwd'],
        "googletoken": "",
        "googleaccesstoken": "",
        "keep-user-logged-in": False,
        "2fa": "",
    }

    response = requests.post(
        "https://hq1.appsflyer.com/auth/login", headers=headers, json=body, verify=False
    )

    if response.status_code == 200 and "af_jwt" in response.cookies:
        cookie = f"af_jwt={response.cookies['af_jwt']}"
        Variable.update_variable({"appsFlyer": {"cookie": cookie}})
    else:
        print(f"Ошибка авторизации: {response.status_code} - {response.text}")


def get_data(type):
    return Variable.get_variable(type)