from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.shelter import CurrentShelterManager
from app.db.session import get_database_session
from app.schemas.pet_photos import PetPhotoRead
from app.services.pet_photos import (
    InvalidPetPhotoError,
    PetPhotoNotFoundError,
    PetPhotoPersistenceError,
    PetPhotoStorageError,
    create_pet_photo,
    validate_pet_image,
)

router = APIRouter(prefix="/pets", tags=["pet photos"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post(
    "/{pet_id}/photos",
    response_model=PetPhotoRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pet_photo(
    pet_id: UUID,
    image_file: Annotated[
        UploadFile,
        File(description="A JPEG, PNG, or WebP image up to 5 MB."),
    ],
    alt_text: Annotated[
        str,
        Form(description="Short accessible description of the image."),
    ],
    current_shelter_manager: CurrentShelterManager,
    database_session: DatabaseSession,
) -> PetPhotoRead:
    """
    Upload one photo for a pet belonging to the manager's shelter.
    """
    try:
        # UploadFile is read asynchronously because it originates from
        # a multipart HTTP request. The service then receives plain bytes.
        contents = await image_file.read()
    finally:
        # Always close the temporary uploaded file, including validation errors.
        await image_file.close()

    try:
        validated_image = validate_pet_image(contents)

        photo = create_pet_photo(
            database_session,
            pet_id=pet_id,
            shelter_id=current_shelter_manager.shelter_id,
            image=validated_image,
            alt_text=alt_text,
        )
    except InvalidPetPhotoError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except PetPhotoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found in your shelter.",
        ) from error
    except PetPhotoStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Photo storage is temporarily unavailable.",
        ) from error
    except PetPhotoPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The photo could not be saved.",
        ) from error

    return PetPhotoRead.model_validate(photo)
