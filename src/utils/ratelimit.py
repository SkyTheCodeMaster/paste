from aiohttplimiter import Limiter, default_keyfunc

limiter = Limiter(keyfunc=default_keyfunc)