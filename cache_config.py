"""
إعدادات التخزين المؤقت - Caching Configuration
"""

from flask_caching import Cache

# إعدادات التخزين المؤقت
cache_config = {
    'CACHE_TYPE': 'SimpleCache',  # استخدم 'RedisCache' للإنتاج
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 دقائق
}

# للإنتاج مع Redis:
# cache_config = {
#     'CACHE_TYPE': 'RedisCache',
#     'CACHE_REDIS_HOST': 'localhost',
#     'CACHE_REDIS_PORT': 6379,
#     'CACHE_REDIS_DB': 0,
#     'CACHE_DEFAULT_TIMEOUT': 300
# }

cache = Cache()

def init_cache(app):
    """تهيئة التخزين المؤقت"""
    cache.init_app(app, config=cache_config)
    return cache

# دوال مساعدة للتخزين المؤقت
def get_cached_stats():
    """الحصول على الإحصائيات من الكاش"""
    from flask import current_app
    return cache.get('dashboard_stats')

def set_cached_stats(stats, timeout=300):
    """حفظ الإحصائيات في الكاش"""
    cache.set('dashboard_stats', stats, timeout=timeout)
    return stats

def clear_cache():
    """مسح جميع البيانات المؤقتة"""
    cache.clear()
    print('✅ تم مسح الكاش')
