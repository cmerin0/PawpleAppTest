CREATE EXTENSION IF NOT EXISTS pgcrypto;

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM users
        WHERE email = 'owner@pawple.local'
    ) THEN
        RAISE EXCEPTION
            'Seed data already exists. This script is intentionally one-time only.';
    END IF;
END $$;

-- All seed accounts use this password:
-- Pawple123!
-- The hash is compatible with the API's pwdlib Argon2 configuration.
INSERT INTO users (
    id,
    email,
    password_hash,
    display_name,
    is_platform_admin
)
VALUES
    (
        gen_random_uuid(),
        'admin@pawple.local',
        '$argon2id$v=19$m=65536,t=3,p=4$h9Mn1+MbgRlutYU9yUaBNw$jriBesFMSh1RK1coaK/i6ym3i2ziAQtAJAhmu53dHR8',
        'Pat Platform Admin',
        TRUE
    ),
    (
        gen_random_uuid(),
        'owner@pawple.local',
        '$argon2id$v=19$m=65536,t=3,p=4$h9Mn1+MbgRlutYU9yUaBNw$jriBesFMSh1RK1coaK/i6ym3i2ziAQtAJAhmu53dHR8',
        'Olivia Owner',
        FALSE
    ),
    (
        gen_random_uuid(),
        'manager@pawple.local',
        '$argon2id$v=19$m=65536,t=3,p=4$h9Mn1+MbgRlutYU9yUaBNw$jriBesFMSh1RK1coaK/i6ym3i2ziAQtAJAhmu53dHR8',
        'Marco Manager',
        FALSE
    ),
    (
        gen_random_uuid(),
        'staff@pawple.local',
        '$argon2id$v=19$m=65536,t=3,p=4$h9Mn1+MbgRlutYU9yUaBNw$jriBesFMSh1RK1coaK/i6ym3i2ziAQtAJAhmu53dHR8',
        'Sofia Staff',
        FALSE
    ),
    (
        gen_random_uuid(),
        'dallas-owner@pawple.local',
        '$argon2id$v=19$m=65536,t=3,p=4$h9Mn1+MbgRlutYU9yUaBNw$jriBesFMSh1RK1coaK/i6ym3i2ziAQtAJAhmu53dHR8',
        'Daniel Dallas Owner',
        FALSE
    ),
    (
        gen_random_uuid(),
        'alice@pawple.local',
        '$argon2id$v=19$m=65536,t=3,p=4$h9Mn1+MbgRlutYU9yUaBNw$jriBesFMSh1RK1coaK/i6ym3i2ziAQtAJAhmu53dHR8',
        'Alice Adopter',
        FALSE
    ),
    (
        gen_random_uuid(),
        'bob@pawple.local',
        '$argon2id$v=19$m=65536,t=3,p=4$h9Mn1+MbgRlutYU9yUaBNw$jriBesFMSh1RK1coaK/i6ym3i2ziAQtAJAhmu53dHR8',
        'Bob Adopter',
        FALSE
    ),
    (
        gen_random_uuid(),
        'carla@pawple.local',
        '$argon2id$v=19$m=65536,t=3,p=4$h9Mn1+MbgRlutYU9yUaBNw$jriBesFMSh1RK1coaK/i6ym3i2ziAQtAJAhmu53dHR8',
        'Carla Adopter',
        FALSE
    );

INSERT INTO adopter_profiles (
    id,
    user_id,
    phone
)
SELECT
    gen_random_uuid(),
    users.id,
    profile_data.phone
FROM (
    VALUES
        ('alice@pawple.local', '512-555-0181'),
        ('bob@pawple.local', '512-555-0182'),
        ('carla@pawple.local', '512-555-0183')
) AS profile_data(email, phone)
JOIN users
    ON users.email = profile_data.email;

INSERT INTO shelters (
    id,
    name,
    slug,
    email,
    phone,
    city,
    state
)
VALUES
    (
        gen_random_uuid(),
        'Pawple Rescue Austin',
        'pawple-rescue-austin',
        'austin@pawple-rescue.local',
        '512-555-0100',
        'Austin',
        'TX'
    ),
    (
        gen_random_uuid(),
        'Dallas Pet Haven',
        'dallas-pet-haven',
        'dallas@pawple.local',
        '214-555-0100',
        'Dallas',
        'TX'
    );

INSERT INTO shelter_members (
    shelter_id,
    user_id,
    role
)
SELECT
    shelters.id,
    users.id,
    membership_data.role
FROM (
    VALUES
        ('pawple-rescue-austin', 'owner@pawple.local', 'owner'),
        ('pawple-rescue-austin', 'manager@pawple.local', 'manager'),
        ('pawple-rescue-austin', 'staff@pawple.local', 'staff'),
        ('dallas-pet-haven', 'dallas-owner@pawple.local', 'owner')
) AS membership_data(shelter_slug, user_email, role)
JOIN shelters
    ON shelters.slug = membership_data.shelter_slug
JOIN users
    ON users.email = membership_data.user_email;

INSERT INTO pets (
    id,
    shelter_id,
    name,
    species,
    breed,
    sex,
    size,
    description,
    status,
    published_at
)
SELECT
    gen_random_uuid(),
    shelters.id,
    pet_data.name,
    pet_data.species,
    pet_data.breed,
    pet_data.sex,
    pet_data.size,
    pet_data.description,
    pet_data.status,
    CASE
        WHEN pet_data.status = 'draft' THEN NULL
        ELSE NOW()
    END
FROM (
    VALUES
        (
            'pawple-rescue-austin',
            'Luna',
            'Dog',
            'Labrador Retriever',
            'Female',
            'Large',
            'Available Pet with Alice''s submitted application.',
            'available'
        ),
        (
            'pawple-rescue-austin',
            'Milo',
            'Cat',
            'Domestic Shorthair',
            'Male',
            'Small',
            'Available Pet dismissed by Alice; Bob has a draft.',
            'available'
        ),
        (
            'pawple-rescue-austin',
            'Bella',
            'Dog',
            'Beagle',
            'Female',
            'Medium',
            'Available Pet with Carla''s contacted application.',
            'available'
        ),
        (
            'pawple-rescue-austin',
            'Rocky',
            'Dog',
            'Boxer',
            'Male',
            'Large',
            'Pending Pet with Alice''s approved application.',
            'pending'
        ),
        (
            'pawple-rescue-austin',
            'Coco',
            'Cat',
            'Siamese',
            'Female',
            'Small',
            'Already adopted Pet.',
            'adopted'
        ),
        (
            'pawple-rescue-austin',
            'Shadow',
            'Dog',
            'Mixed Breed',
            'Male',
            'Medium',
            'Draft Pet ready to publish manually.',
            'draft'
        ),
        (
            'pawple-rescue-austin',
            'Daisy',
            'Dog',
            'Golden Retriever',
            'Female',
            'Large',
            'Unavailable Pet with a withdrawn application.',
            'unavailable'
        ),
        (
            'dallas-pet-haven',
            'Pepper',
            'Cat',
            'Tuxedo',
            'Female',
            'Small',
            'Available Dallas Pet with Bob''s submitted application.',
            'available'
        ),
        (
            'dallas-pet-haven',
            'Max',
            'Dog',
            'Australian Shepherd',
            'Male',
            'Medium',
            'Draft Pet owned by Dallas Pet Haven.',
            'draft'
        ),
        (
            'dallas-pet-haven',
            'Nova',
            'Cat',
            'Maine Coon',
            'Female',
            'Large',
            'Adopted Dallas Pet.',
            'adopted'
        )
) AS pet_data(
    shelter_slug,
    name,
    species,
    breed,
    sex,
    size,
    description,
    status
)
JOIN shelters
    ON shelters.slug = pet_data.shelter_slug;

INSERT INTO pet_dismissals (
    user_id,
    pet_id
)
SELECT
    users.id,
    pets.id
FROM (
    VALUES
        ('alice@pawple.local', 'pawple-rescue-austin', 'Milo'),
        ('bob@pawple.local', 'pawple-rescue-austin', 'Luna'),
        ('carla@pawple.local', 'dallas-pet-haven', 'Pepper')
) AS dismissal_data(user_email, shelter_slug, pet_name)
JOIN users
    ON users.email = dismissal_data.user_email
JOIN shelters
    ON shelters.slug = dismissal_data.shelter_slug
JOIN pets
    ON pets.shelter_id = shelters.id
    AND pets.name = dismissal_data.pet_name;

INSERT INTO adoption_applications (
    id,
    pet_id,
    applicant_user_id,
    status,
    contact_phone,
    message,
    consent_at,
    submitted_at
)
SELECT
    gen_random_uuid(),
    pets.id,
    users.id,
    application_data.status,
    CASE
        WHEN application_data.status = 'draft' THEN NULL
        ELSE '512-555-0199'
    END,
    CASE
        WHEN application_data.status = 'draft' THEN NULL
        ELSE 'I can provide a safe and loving home.'
    END,
    CASE
        WHEN application_data.status = 'draft' THEN NULL
        ELSE NOW()
    END,
    CASE
        WHEN application_data.status = 'draft' THEN NULL
        ELSE NOW()
    END
FROM (
    VALUES
        (
            'pawple-rescue-austin',
            'Luna',
            'alice@pawple.local',
            'submitted'
        ),
        (
            'pawple-rescue-austin',
            'Milo',
            'bob@pawple.local',
            'draft'
        ),
        (
            'pawple-rescue-austin',
            'Bella',
            'carla@pawple.local',
            'contacted'
        ),
        (
            'pawple-rescue-austin',
            'Bella',
            'alice@pawple.local',
            'submitted'
        ),
        (
            'pawple-rescue-austin',
            'Rocky',
            'alice@pawple.local',
            'approved'
        ),
        (
            'pawple-rescue-austin',
            'Coco',
            'bob@pawple.local',
            'approved'
        ),
        (
            'pawple-rescue-austin',
            'Daisy',
            'alice@pawple.local',
            'withdrawn'
        ),
        (
            'dallas-pet-haven',
            'Pepper',
            'bob@pawple.local',
            'submitted'
        )
) AS application_data(
    shelter_slug,
    pet_name,
    applicant_email,
    status
)
JOIN shelters
    ON shelters.slug = application_data.shelter_slug
JOIN pets
    ON pets.shelter_id = shelters.id
    AND pets.name = application_data.pet_name
JOIN users
    ON users.email = application_data.applicant_email;

INSERT INTO application_status_events (
    id,
    application_id,
    from_status,
    to_status,
    changed_by_user_id,
    note,
    created_at
)
SELECT
    gen_random_uuid(),
    applications.id,
    event_data.from_status,
    event_data.to_status,
    changed_by_user.id,
    event_data.note,
    NOW() - (event_data.minutes_ago * INTERVAL '1 minute')
FROM (
    VALUES
        (
            'pawple-rescue-austin',
            'Luna',
            'alice@pawple.local',
            NULL,
            'draft',
            'alice@pawple.local',
            'Draft application created.',
            60
        ),
        (
            'pawple-rescue-austin',
            'Luna',
            'alice@pawple.local',
            'draft',
            'submitted',
            'alice@pawple.local',
            'Application submitted.',
            59
        ),
        (
            'pawple-rescue-austin',
            'Milo',
            'bob@pawple.local',
            NULL,
            'draft',
            'bob@pawple.local',
            'Draft application created.',
            58
        ),
        (
            'pawple-rescue-austin',
            'Bella',
            'carla@pawple.local',
            NULL,
            'draft',
            'carla@pawple.local',
            'Draft application created.',
            57
        ),
        (
            'pawple-rescue-austin',
            'Bella',
            'carla@pawple.local',
            'draft',
            'submitted',
            'carla@pawple.local',
            'Application submitted.',
            56
        ),
        (
            'pawple-rescue-austin',
            'Bella',
            'carla@pawple.local',
            'submitted',
            'reviewing',
            'manager@pawple.local',
            'Application is being reviewed.',
            55
        ),
        (
            'pawple-rescue-austin',
            'Bella',
            'carla@pawple.local',
            'reviewing',
            'contacted',
            'manager@pawple.local',
            'Applicant was contacted.',
            54
        ),
        (
            'pawple-rescue-austin',
            'Bella',
            'alice@pawple.local',
            NULL,
            'draft',
            'alice@pawple.local',
            'Draft application created.',
            53
        ),
        (
            'pawple-rescue-austin',
            'Bella',
            'alice@pawple.local',
            'draft',
            'submitted',
            'alice@pawple.local',
            'Application submitted.',
            52
        ),
        (
            'pawple-rescue-austin',
            'Rocky',
            'alice@pawple.local',
            NULL,
            'draft',
            'alice@pawple.local',
            'Draft application created.',
            51
        ),
        (
            'pawple-rescue-austin',
            'Rocky',
            'alice@pawple.local',
            'draft',
            'submitted',
            'alice@pawple.local',
            'Application submitted.',
            50
        ),
        (
            'pawple-rescue-austin',
            'Rocky',
            'alice@pawple.local',
            'submitted',
            'reviewing',
            'manager@pawple.local',
            'Application is being reviewed.',
            49
        ),
        (
            'pawple-rescue-austin',
            'Rocky',
            'alice@pawple.local',
            'reviewing',
            'contacted',
            'manager@pawple.local',
            'Applicant was contacted.',
            48
        ),
        (
            'pawple-rescue-austin',
            'Rocky',
            'alice@pawple.local',
            'contacted',
            'approved',
            'manager@pawple.local',
            'Application approved; pet moved to pending.',
            47
        ),
        (
            'pawple-rescue-austin',
            'Coco',
            'bob@pawple.local',
            NULL,
            'draft',
            'bob@pawple.local',
            'Draft application created.',
            46
        ),
        (
            'pawple-rescue-austin',
            'Coco',
            'bob@pawple.local',
            'draft',
            'submitted',
            'bob@pawple.local',
            'Application submitted.',
            45
        ),
        (
            'pawple-rescue-austin',
            'Coco',
            'bob@pawple.local',
            'submitted',
            'reviewing',
            'manager@pawple.local',
            'Application is being reviewed.',
            44
        ),
        (
            'pawple-rescue-austin',
            'Coco',
            'bob@pawple.local',
            'reviewing',
            'contacted',
            'manager@pawple.local',
            'Applicant was contacted.',
            43
        ),
        (
            'pawple-rescue-austin',
            'Coco',
            'bob@pawple.local',
            'contacted',
            'approved',
            'manager@pawple.local',
            'Application approved; pet moved to pending.',
            42
        ),
        (
            'pawple-rescue-austin',
            'Coco',
            'bob@pawple.local',
            'approved',
            'approved',
            'manager@pawple.local',
            'Adoption completed; pet marked adopted.',
            41
        ),
        (
            'pawple-rescue-austin',
            'Daisy',
            'alice@pawple.local',
            NULL,
            'draft',
            'alice@pawple.local',
            'Draft application created.',
            40
        ),
        (
            'pawple-rescue-austin',
            'Daisy',
            'alice@pawple.local',
            'draft',
            'submitted',
            'alice@pawple.local',
            'Application submitted.',
            39
        ),
        (
            'pawple-rescue-austin',
            'Daisy',
            'alice@pawple.local',
            'submitted',
            'withdrawn',
            'alice@pawple.local',
            'Application withdrawn by applicant.',
            38
        ),
        (
            'dallas-pet-haven',
            'Pepper',
            'bob@pawple.local',
            NULL,
            'draft',
            'bob@pawple.local',
            'Draft application created.',
            37
        ),
        (
            'dallas-pet-haven',
            'Pepper',
            'bob@pawple.local',
            'draft',
            'submitted',
            'bob@pawple.local',
            'Application submitted.',
            36
        )
) AS event_data(
    shelter_slug,
    pet_name,
    applicant_email,
    from_status,
    to_status,
    actor_email,
    note,
    minutes_ago
)
JOIN shelters
    ON shelters.slug = event_data.shelter_slug
JOIN pets
    ON pets.shelter_id = shelters.id
    AND pets.name = event_data.pet_name
JOIN users AS applicant_user
    ON applicant_user.email = event_data.applicant_email
JOIN adoption_applications AS applications
    ON applications.pet_id = pets.id
    AND applications.applicant_user_id = applicant_user.id
JOIN users AS changed_by_user
    ON changed_by_user.email = event_data.actor_email;

COMMIT;