import asyncio

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

        while True:
            password = input("Enter the password: ")
            if not password:
                continue
            break
        user_data = {"login": login, "password": password}
        admin = await create_admin(db, user_data)
        if admin:
            print("Admin created successfully")


if __name__ == "__main__":
    asyncio.run(main())
