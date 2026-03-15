try:
    from app.core.config import get_settings
    print("✓ config OK")
except Exception as e:
    print(f"✗ config: {e}")

try:
    from app.core.event_bus import event_bus
    print("✓ event_bus OK")
except Exception as e:
    print(f"✗ event_bus: {e}")

try:
    from app.db.database import init_db
    print("✓ database OK")
except Exception as e:
    print(f"✗ database: {e}")

try:
    from app.services.scheduler import start_scheduler
    print("✓ scheduler OK")
except Exception as e:
    print(f"✗ scheduler: {e}")

try:
    from app.services.orchestrator import orchestrator
    print("✓ orchestrator OK")
except Exception as e:
    print(f"✗ orchestrator: {e}")

try:
    from app.api.routes import router
    print("✓ routes OK")
except Exception as e:
    print(f"✗ routes: {e}")

try:
    from app.api.websocket import router as ws_router
    print("✓ websocket OK")
except Exception as e:
    print(f"✗ websocket: {e}")

try:
    from main import app
    print("✓ main app OK")
except Exception as e:
    print(f"✗ main: {e}")
