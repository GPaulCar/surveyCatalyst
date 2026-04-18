from core.db import build_backend

backend = build_backend()
print("healthcheck:", backend.healthcheck())
backend.close()
