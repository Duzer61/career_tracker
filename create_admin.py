import asyncio
import getpass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash, get_user_by_login
from app.db.database import get_session
from app.db.models import User


async def create_admin(db: AsyncSession, user_data: dict) -> User:
    """
    Create a new user.
    """
    hashed_password = get_password_hash(user_data["password"])
    admin = User(login=user_data["login"], hashed_password=hashed_password, is_admin=True)
    db.add(admin)
    try:
        await db.commit()
        await db.refresh(admin)
        return admin
    except IntegrityError:
        await db.rollback()
        raise ValueError(f"User with login '{user_data['login']}' already exists")


async def input_password() -> str:
    """
    Input password from the console.
    """
    password = ""
    while not password:
        password1 = getpass.getpass("Enter the password: ")
        if not password1:
            continue
        password2 = getpass.getpass("Re-enter the password: ")
        if password1 == password2:
            password = password1
            break
        print("Passwords do not match. Try again.")
    return password


async def main():
    """
    Create an administrator.
    """
    print("\n*****Creating an administrator*****\n")

    async for db in get_session():
        while True:
            login = input("Enter the name of the administrator: ")
            existing_user = await get_user_by_login(db, login)
            if existing_user:
                print("User already exists. Choose a different username")
                continue
            if login:
                break
        print()
        password = await input_password()
        user_data = {"login": login, "password": password}
        admin = await create_admin(db, user_data)
        if admin:
            print("Admin created successfully")


if __name__ == "__main__":
    asyncio.run(main())
