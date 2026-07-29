from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.shelter import CurrentShelterManager
from app.db.session import get_database_session
from app.schemas.pet_photos import PetPhotoPublicRead, PetPhotoRead
from app.services.pet_photos import (
    InvalidPetPhotoError,
    PetPhotoNotFoundError,
    PetPhotoPersistenceError,
    PetPhotoStorageError,
    PublicPetNotFoundError,
    create_pet_photo,
    create_pet_photo_download_url,
    validate_pet_image,
)
from app.services.pet_photos import (
    list_public_pet_photos as list_public_pet_photo_records,
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


@router.get(
    "/{pet_id}/photos",
    response_model=list[PetPhotoPublicRead],
)
def list_public_pet_photos(
    pet_id: UUID,
    database_session: DatabaseSession,
) -> list[PetPhotoPublicRead]:
    """
    Return ordered photos for a publicly available pet.

    This endpoint does not require authentication because available pets
    are part of public adoption discovery.
    """
    try:
        photos = list_public_pet_photo_records(
            database_session,
            pet_id=pet_id,
        )

        return [
            PetPhotoPublicRead(
                id=photo.id,
                pet_id=photo.pet_id,
                alt_text=photo.alt_text,
                sort_order=photo.sort_order,
                created_at=photo.created_at,
                url=create_pet_photo_download_url(
                    object_key=photo.object_key,
                ),
            )
            for photo in photos
        ]
    except PublicPetNotFoundError as error:
        # Draft or non-existent pets intentionally produce the same response.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found.",
        ) from error
    except PetPhotoStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Photo storage is temporarily unavailable.",
        ) from error
