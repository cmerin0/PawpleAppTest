from fastapi import FastAPI

from app.api.routes.adopter_profiles import router as adopter_profiles_router
from app.api.routes.adoption_applications import (
    applications_router,
    pet_application_router,
    shelter_applications_router,
)
from app.api.routes.auth import router as auth_router
from app.api.routes.pet_photos import router as pet_photos_router
from app.api.routes.pets import (
    public_router as pets_router,
)
from app.api.routes.pets import (
    shelter_router as shelter_pets_router,
)
from app.api.routes.shelters import router as shelters_router
from app.api.routes.users import router as users_router

# The main entry point for the Pawple API application.
# This module sets up the FastAPI application instance

prefix = "/api/v1"


# Create the FastAPI application instance and include
# the routers for different API endpoints.
def create_application() -> FastAPI:
    application = FastAPI(
        title="Pawple API",
        version="0.1.0",
        description="API for Pawple, a pet-adoption platform.",
    )

    application.include_router(users_router, prefix=prefix)
    application.include_router(auth_router, prefix=prefix)
    application.include_router(shelters_router, prefix=prefix)
    application.include_router(pets_router, prefix=prefix)
    application.include_router(shelter_pets_router, prefix=prefix)
    application.include_router(adopter_profiles_router, prefix=prefix)
    application.include_router(applications_router, prefix=prefix)
    application.include_router(pet_application_router, prefix=prefix)
    application.include_router(shelter_applications_router, prefix=prefix)
    application.include_router(pet_photos_router, prefix=prefix)
    return application


# Create the FastAPI application instance.
app = create_application()
