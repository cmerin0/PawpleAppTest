from fastapi import FastAPI

from app.api.routes.users import router as users_router

def create_application() -> FastAPI:
    """Create and configure the Pawple API application."""
    application = FastAPI(
        title="Pawple API",
        version="0.1.0",
        description="API for Pawple, a pet-adoption platform.",
    )

    application.include_router(users_router, prefix="/api/v1",)

    return application

# Create the FastAPI application instance.
app = create_application()