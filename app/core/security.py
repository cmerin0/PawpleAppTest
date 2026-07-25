from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()    # Argon2 settings recommended by pwdlib are appropriate for new password hashes.    

def hash_password(password: str) -> str:
    """Create a secure, one-way password hash for database storage."""
    return password_hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Check whether a supplied password matches its stored hash."""
    return password_hasher.verify(password, password_hash)