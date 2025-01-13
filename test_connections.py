from pymongo import MongoClient
import redis
import sys

def test_mongodb():
    try:
        client = MongoClient('mongodb://localhost:27017')
        print("MongoDB успешно подключен")
        print(client.server_info())
        return True
    except Exception as e:
        print(f"Соединение с MongoDB не удалось: {e}")
        return False

def test_redis():
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        print("Redis успешно подключен")
        print(f"Redis ping: {r.ping()}")
        return True
    except Exception as e:
        print(f"Соединение с Redis не удалось: {e}")
        return False

if __name__ == "__main__":
    print("Проверка подключений...")
    mongo_ok = test_mongodb()
    redis_ok = test_redis()
    
    if mongo_ok and redis_ok:
        print("\nВсе соединения успешны!")
        sys.exit(0)
    else:
        print("\nНекоторые соединения не удались!")
        sys.exit(1)