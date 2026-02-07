from openfoodfacts import API, APIVersion, Environment

class FoodApi:
    # Инициализируем API на уровне класса, а не в __init__
    api = API(
        user_agent="MyFoodApp/1.0 (akhmeddzhan@mail.ru)",
        version=APIVersion.v3,
        environment=Environment.net
    )
    
    @staticmethod
    def get_calories_by_food_name(food: str):
        try:
            # Ищем продукт
            result = FoodApi.api.product.text_search(food)
            
            # Проверяем, есть ли результаты
            if not result.get('products'):
                print(f"Продукт '{food}' не найден")
                return None
            
            # Получаем первый продукт
            product = result['products'][0]
            
            # Проверяем наличие данных о питательных веществах
            if 'nutriments' not in product:
                print(f"Нет данных о питательных веществах для '{food}'")
                return None
            
            nutriments = product['nutriments']
            
            # Пытаемся получить калории в разных единицах
            # Предпочтительнее ккал
            if 'energy-kcal_100g' in nutriments:
                return float(nutriments['energy-kcal_100g'])
            elif 'energy_100g' in nutriments:
                energy_value = float(nutriments['energy_100g'])
                energy_unit = nutriments.get('energy_unit', 'kJ')
                
                # Конвертируем в ккал если нужно
                if energy_unit == 'kJ':
                    # 1 ккал = 4.184 кДж
                    return energy_value / 4.184
                elif energy_unit == 'J':
                    return energy_value / 4184
                else:
                    return energy_value
            
            print(f"Нет данных о калориях для '{food}'")
            return None
            
        except Exception as e:
            print(f"Ошибка при получении данных: {e}")
            return None