from pydantic import BaseModel
import json
import os

class Variable:
    _data = {}
    _file_path = os.path.join(os.getcwd(), 'data/auth.json')

    @classmethod
    def set_variable(cls):
        """Загружает данные из JSON-файла в переменную класса."""
        if os.path.exists(cls._file_path):
            with open(cls._file_path, 'r', encoding='utf-8') as f:
                cls._data = json.load(f)
        else:
            cls._data = {}

    @classmethod
    def update_variable(cls, new_data: dict):
        """Обновляет данные в памяти и файле."""
        def deep_update(source, updates):
            for key, value in updates.items():
                if isinstance(value, dict) and isinstance(source.get(key), dict):
                    deep_update(source[key], value)
                else:
                    source[key] = value

        deep_update(cls._data, new_data)
        
        with open(cls._file_path, 'w', encoding='utf-8') as f:
            json.dump(cls._data, f, ensure_ascii=False, indent=4)

    @classmethod
    def get_variable(cls, key: str):
        """Возвращает данные по ключу (например, 'vk', 'dzen')."""
        return cls._data.get(key, None)


class Item(BaseModel):
    data: object