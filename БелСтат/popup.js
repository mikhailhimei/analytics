window.onload = function() {
    const savedUrl = localStorage.getItem('urlInput');
    const tokenInput = localStorage.getItem('tokenInput')
    if (savedUrl) {
        document.getElementById('urlInput').value = savedUrl;
    }
    if(tokenInput){
        document.getElementById('tokenInput').value = tokenInput
    }
    startExtension()
};

async function startExtension() {
    let tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    console.log(tabs)
    if (!tabs[0]) return;

    console.log(123)
    let url = tabs[0].url.split("/").slice(0, 3).join("/");
    let incognito = tabs[0].incognito ? "1" : "0";

    localStorage.setItem('url', url)
    localStorage.setItem('incognito', incognito)
}

async function start() {
    const supportedTypes = {
        'dzen': 'dzen',
        'elama': 'elama',
        'ads.vk': 'vkAds',
        'appsflyer': 'appsFlyer'
    };
    
    // Определяем тип в зависимости от URL
    let type = null;
    console.log(localStorage.getItem('url'))
    let url = localStorage.getItem("url")

    for (let key in supportedTypes) {
        if (url.indexOf(key) !== -1) {
            type = supportedTypes[key];
            break;
        }
    }
    
    // Если тип не найден, завершаем выполнение
    if (!type) {
        return;
    }
    console.log(123)
    let cookieString = '';

    // Получаем куки в зависимости от типа
    if (['dzen', 'vkAds', 'appsFlyer', 'elama'].includes(type)) {
        let cookies = await chrome.cookies.getAll({ url: url, storeId: localStorage.getItem("incognito") });    
        // Формируем строку из куки
        cookieString = cookies
            .filter(c => ['zen_session_id', 'Session_id', 'af_jwt', 'vkads', '_ugeuid'].includes(c.name))
            .map(c => `${c.name}=${c.value}`)
            .join("; ");
    }

    // Запускаем скрипт на странице
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            function: getDataFromDzen, // или другой универсальный метод для всех типов
            args: [cookieString, type]
        }, Results);
    });
}

function getDataFromDzen(cookieString,type) {
    let data = {}
    if(type == 'dzen'){
    let csrfMatch = document.documentElement.innerHTML.match(/"csrfToken":"(.*?)"/);
    let id = document.documentElement.innerHTML.match(/"publisher":{"id":"(.*?)"/);
    let csrfToken = csrfMatch ? csrfMatch[1] : null;

        data = {
            dzen: {
                cookie: cookieString,
                token: csrfToken,
                editId: id[1]
            }
        };
    }
    else if(type == 'vkAds'){
        let localkey = Object.keys(JSON.parse(localStorage.getItem("storageService/main/dashboard/filter"))['value'])
        data = {
            vk: {
                cookie: cookieString,
                account: localkey[0],
                sudo: localkey[1].split('-')[1]
            }
        };
    }
    else if(type == 'appsFlyer'){
        data = {
            appsFlyer: {
                cookie: cookieString
            }
        };
    }
    else if(type == 'elama'){
        let token = sessionStorage.getItem("accessToken").replaceAll('"','')
        let refresh_token = sessionStorage.getItem("refreshToken").replaceAll('"','')
        let gid = document.querySelector('.sc-iVCKna.cFWWDD').href.split('=')[1]
        let id = document.querySelector('.PageTitlestyled__TitleHeader-sc-1slwcv0-8').innerText.replace('Аккаунт elama-', '')

        data = {
            tgAds: {
                token: token,
                refresh_token:refresh_token,
                _ugeuid: cookieString.replace('_ugeuid=',''),
                _id:id,
                _gid:gid
            }
        };
    }
    return data
}

function Results(frames){

    fetch(`${document.getElementById('urlInput').value}/api/update/variable`, {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "Authorization":localStorage.getItem('tokenInput')
         },
        body: JSON.stringify({"data":frames[0].result})
    })
    .then(response => console.log(response.json()))

    return true; // sendResponse вызывается асинхронно
}

document.querySelector('.start').addEventListener('click', async (e) => {
    const urlInput = document.getElementById('urlInput').value;
    const tokenInput = document.getElementById('tokenInput').value
    if (urlInput) {
        await start() 
        localStorage.setItem('urlInput', urlInput);
        localStorage.setItem('tokenInput', tokenInput)
        showNotification();
    } else {
        
    }
})

function showNotification() {
    const notification = document.getElementById('notification');
    notification.style.display = 'block';

    // Скрыть уведомление через 3 секунды
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}