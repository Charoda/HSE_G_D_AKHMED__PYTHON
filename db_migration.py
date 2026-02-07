#db_migrations.py
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from activelifeuser import User

load_dotenv()

DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "health_tracker"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "")
}

async def create_tables():
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        
        # Создание таблицы users
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(50) PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Создание таблицы user_health_data
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_health_data (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(50) NOT NULL,
                weight INTEGER NOT NULL,
                height INTEGER NOT NULL,
                age INTEGER NOT NULL,
                activity INTEGER NOT NULL,
                city VARCHAR(100) NOT NULL,
                water_goal INTEGER NOT NULL,
                calorie_goal INTEGER NOT NULL,
                logged_water INTEGER DEFAULT 0,
                logged_calories INTEGER DEFAULT 0,
                burned_calories INTEGER DEFAULT 0,
                net_calories INTEGER DEFAULT 0,
                record_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_user
                    FOREIGN KEY(user_id) 
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            );
        ''')


        # Создание таблицы для логов активности
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(50) NOT NULL,
                activity_type VARCHAR(50) NOT NULL,
                duration_minutes INTEGER NOT NULL,
                calories_burned INTEGER NOT NULL,
                activity_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_user_activity
                    FOREIGN KEY(user_id) 
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            );
        ''')
        
        print("Таблицы созданы")
    except Exception as e:
        print(f" Ошибка при создании таблиц: {e}")
        raise
    finally:
        if conn:
            await conn.close()
            
async def save_to_db(user: User):
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        
        await conn.execute('''
            INSERT INTO users (user_id) 
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING;
        ''', str(user.name))
            
        await conn.execute('''
            INSERT INTO user_health_data 
            (user_id, weight, height, age, activity, city, water_goal, calorie_goal)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
        ''', str(user.name), user.weight, user.height, user.age, 
              user.activity, user.city, user.water_norm, user.calories_norm)
            
        print(f" Пользователь {user.name} сохранен в базу данных")
            
    except Exception as e:
        print(f"Ошибка при сохранении пользователя {user['user_id']}: {e}")
        raise
    finally:
        if conn:
            await conn.close()

async def show_tables():
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        
        # Получаем список таблиц
        tables = await conn.fetch('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        ''')
        
        print("\n📊 Список таблиц:")
        for table in tables:
            print(f"  - {table['table_name']}")
            
            # Получаем структуру таблицы
            columns = await conn.fetch('''
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position;
            ''', table['table_name'])
            
            for col in columns:
                print(f"    * {col['column_name']} ({col['data_type']}) - nullable: {col['is_nullable']}")
            print()
            
    except Exception as e:
        print(f"❌ Ошибка при получении информации о таблицах: {e}")
    finally:
        if conn:
            await conn.close()

async def get_user_profile(user_id):
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        print(f'user_id is {user_id}')
        result = await conn.fetchrow('''
            SELECT 
                ud.user_id,
                ud.weight,
                ud.height,
                ud.age,
                ud.city,
                ud.activity,
                ud.water_goal,
                ud.calorie_goal,
                ud.logged_water,
                ud.logged_calories,
                ud.burned_calories,
                ud.record_date
            FROM user_health_data ud
            WHERE ud.user_id = $1 
            ORDER BY ud.record_date DESC, ud.created_at DESC
            LIMIT 1;
        ''', str(user_id))
        
        print(f'Профиль найден: {result}')
        
        if result:
            return dict(result)
        return None
        
    except Exception as e:
        print(f"❌ Ошибка при получении профиля пользователя {user_id}: {e}")
        return None
    finally:
        if conn:
            await conn.close()

async def log_water(user_id: int, water_ml: int):
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)

        today_record = await conn.fetchrow('''
            SELECT id FROM user_health_data 
            WHERE user_id = $1 AND record_date = CURRENT_DATE;
        ''', str(user_id))
        print(f'today_record: {today_record}')
        if today_record:
            await conn.execute('''
                UPDATE user_health_data 
                SET logged_water = logged_water + $2, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1 AND record_date = CURRENT_DATE;
            ''', str(user_id), water_ml)
        else:
            last_record = await conn.fetchrow('''
                SELECT weight, height, age, city, water_goal, calorie_goal
                FROM user_health_data 
                WHERE user_id = $1 
                ORDER BY record_date DESC 
                LIMIT 1;
            ''', str(user_id))
            print(f'last_record: {last_record}')
            if last_record:
                await conn.execute('''
                    INSERT INTO user_health_data 
                    (user_id, weight, height, age, city, water_goal, calorie_goal, logged_water, record_date)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_DATE);
                ''', str(user_id), 
                    last_record['weight'], 
                    last_record['height'], 
                    last_record['age'],
                    last_record['city'],
                    last_record['water_goal'],
                    last_record['calorie_goal'],
                    water_ml)
            else:
                await conn.execute('''
                    INSERT INTO user_health_data 
                    (user_id, logged_water, record_date)
                    VALUES ($1, $2, CURRENT_DATE);
                ''', str(user_id), water_ml)
        
        print(f"Вода {water_ml} мл добавлена для пользователя {user_id}")
        return True
        
    except Exception as e:
        print(f"Ошибка при добавлении воды: {e}")
        return False
    finally:
        if conn:
            await conn.close()


async def log_calories(user_id: int, calories: float, food_name: str = None):
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)

        today_record = await conn.fetchrow('''
            SELECT id FROM user_health_data 
            WHERE user_id = $1 AND record_date = CURRENT_DATE;
        ''', str(user_id))
        
        if today_record:
            # Обновляем существующую запись
            await conn.execute('''
                UPDATE user_health_data 
                SET logged_calories = logged_calories + $2, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1 AND record_date = CURRENT_DATE;
            ''', str(user_id), calories)
        else:
            # Создаем новую запись на сегодня
            # Сначала получаем последнюю запись пользователя для копирования целей
            last_record = await conn.fetchrow('''
                SELECT weight, height, age, city, water_goal, calorie_goal
                FROM user_health_data 
                WHERE user_id = $1 
                ORDER BY record_date DESC 
                LIMIT 1;
            ''', str(user_id))
            
            if last_record:
                await conn.execute('''
                    INSERT INTO user_health_data 
                    (user_id, weight, height, age, city, water_goal, calorie_goal, logged_calories, record_date)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_DATE);
                ''', str(user_id), 
                    last_record['weight'], 
                    last_record['height'], 
                    last_record['age'],
                    last_record['city'],
                    last_record['water_goal'],
                    last_record['calorie_goal'],
                    calories)
            else:
                await conn.execute('''
                    INSERT INTO user_health_data 
                    (user_id, logged_calories, record_date)
                    VALUES ($1, $2, CURRENT_DATE);
                ''', str(user_id), calories)
        if food_name:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS food_history (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    food_name VARCHAR(200) NOT NULL,
                    calories FLOAT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_user_food
                        FOREIGN KEY(user_id) 
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );
            ''')
            
            await conn.execute('''
                INSERT INTO food_history (user_id, food_name, calories)
                VALUES ($1, $2, $3);
            ''', str(user_id), food_name, calories)
        return True
        
    except Exception:
        print(f"Ошибка при добавлении калорий")
    finally:
        if conn:
            await conn.close()



async def log_activity(user_id: int, activity_type: str, duration_minutes: int):
    try:
        # Словарь для расчета калорий по типу активности
        activity_calories_per_30min = {
            'бег': 300,
            'спортивная ходьба': 400,
            'ходьба': 400,
            'плавание': 600,
            'силовая тренировка': 300,
            'йога': 150,
            'велосипед': 300,
            'футбол': 400,
            'баскетбол': 350,
            'теннис': 350
        }
        
        activity_lower = activity_type.lower()
        
        calories_per_30min = None
        for key in activity_calories_per_30min:
            if key in activity_lower or activity_lower in key:
                calories_per_30min = activity_calories_per_30min[key]
                break
        
        # Если не нашли точного совпадения, используем среднее значение
        if calories_per_30min is None:
            calories_per_30min = 300  # Среднее значение
            print(f"⚠️ Тип активности '{activity_type}' не найден, используем среднее значение")
        
        # Рассчитываем сожженные калории
        calories_burned = int((calories_per_30min / 30) * duration_minutes)
        
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        
        # 1. Добавляем запись в лог активности
        await conn.execute('''
            INSERT INTO activity_logs 
            (user_id, activity_type, duration_minutes, calories_burned, activity_date)
            VALUES ($1, $2, $3, $4, CURRENT_DATE);
        ''', str(user_id), activity_type, duration_minutes, calories_burned)
        
        # 2. Обновляем burned_calories в user_health_data за сегодня
        # Проверяем, есть ли запись на сегодня
        today_record = await conn.fetchrow('''
            SELECT id FROM user_health_data 
            WHERE user_id = $1 AND record_date = CURRENT_DATE;
        ''', str(user_id))
        
        if today_record:
            # Обновляем существующую запись
            await conn.execute('''
                UPDATE user_health_data 
                SET burned_calories = burned_calories + $2,
                    net_calories = logged_calories - (burned_calories + $2),
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1 AND record_date = CURRENT_DATE;
            ''', str(user_id), calories_burned)
        else:
            # Создаем новую запись на сегодня
            # Сначала получаем последнюю запись пользователя
            last_record = await conn.fetchrow('''
                SELECT weight, height, age, city, water_goal, calorie_goal, logged_calories
                FROM user_health_data 
                WHERE user_id = $1 
                ORDER BY record_date DESC 
                LIMIT 1;
            ''', str(user_id))
            
            if last_record:
                logged_calories = last_record.get('logged_calories', 0)
                net_calories = logged_calories - calories_burned
                
                await conn.execute('''
                    INSERT INTO user_health_data 
                    (user_id, weight, height, age, city, water_goal, calorie_goal, 
                     burned_calories, net_calories, logged_calories, record_date)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, CURRENT_DATE);
                ''', str(user_id), 
                    last_record['weight'], 
                    last_record['height'], 
                    last_record['age'],
                    last_record['city'],
                    last_record['water_goal'],
                    last_record['calorie_goal'],
                    calories_burned,
                    net_calories,
                    logged_calories)
            else:
                # Если нет предыдущих записей
                await conn.execute('''
                    INSERT INTO user_health_data 
                    (user_id, burned_calories, net_calories, record_date)
                    VALUES ($1, $2, -$2, CURRENT_DATE);
                ''', str(user_id), calories_burned)
        
        print(f"✅ Активность '{activity_type}' ({duration_minutes} мин) добавлена. Сожжено: {calories_burned} ккал")
        
        return {
            'calories_burned': calories_burned,
            'activity_type': activity_type,
            'duration_minutes': duration_minutes
        }
        
    except Exception as e:
        print(f"❌ Ошибка при записи активности: {e}")
        return None
    finally:
        if conn:
            await conn.close()

async def get_today_activities(user_id: int):
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        
        results = await conn.fetch('''
            SELECT 
                activity_type,
                duration_minutes,
                calories_burned,
                created_at::time as time
            FROM activity_logs 
            WHERE user_id = $1 AND activity_date = CURRENT_DATE
            ORDER BY created_at DESC;
        ''', str(user_id))
        
        return [dict(row) for row in results]
        
    except Exception as e:
        print(f"❌ Ошибка при получении активностей: {e}")
        return []
    finally:
        if conn:
            await conn.close()

async def get_activity_statistics(user_id: int, days: int = 7):
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        
        # Общая статистика
        total_stats = await conn.fetchrow('''
            SELECT 
                COUNT(*) as total_activities,
                SUM(duration_minutes) as total_minutes,
                SUM(calories_burned) as total_calories_burned
            FROM activity_logs 
            WHERE user_id = $1 AND activity_date >= CURRENT_DATE - $2;
        ''', str(user_id), days)
        
        # Статистика по типам активности
        activity_stats = await conn.fetch('''
            SELECT 
                activity_type,
                COUNT(*) as count,
                SUM(duration_minutes) as total_minutes,
                SUM(calories_burned) as total_calories
            FROM activity_logs 
            WHERE user_id = $1 AND activity_date >= CURRENT_DATE - $2
            GROUP BY activity_type
            ORDER BY total_calories DESC;
        ''', str(user_id), days)
        
        return {
            'total': dict(total_stats) if total_stats else {},
            'by_type': [dict(row) for row in activity_stats]
        }
        
    except Exception as e:
        print(f" Ошибка при получении статистики активности: {e}")
        return {}
    finally:
        if conn:
            await conn.close()

async def recalculate_net_calories(user_id: int):
    
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        
        await conn.execute('''
            UPDATE user_health_data 
            SET net_calories = logged_calories - burned_calories,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1 AND record_date = CURRENT_DATE;
        ''', str(user_id))
        
        print(f"Чистые калории пересчитаны для пользователя {user_id}")
        return True
        
    except Exception as e:
        print(f"Ошибка при пересчете чистых калорий: {e}")
        return False
    finally:
        if conn:
            await conn.close()


async def clear_all_tables():
    
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        await conn.execute('delete from user_health_data;')
        await conn.execute('delete from users;')
        print("Все таблицы успешно очищены")
        
    except Exception:
        print(f"Ошибка при очистке таблиц")
    finally:
        if conn:
            await conn.close()

if __name__ == "__main__":
    asyncio.run(create_tables())
    asyncio.run(clear_all_tables())
    asyncio.run(show_tables())