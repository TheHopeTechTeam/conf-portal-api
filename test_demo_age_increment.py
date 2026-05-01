"""
Simple script to verify numeric increment update on Demo.age.
"""

import asyncio
from uuid import UUID

from portal.libs.database import Session
from portal.models import Demo


DEMO_ID = UUID("ba0cbff0-47e1-4f98-b84a-a11377490b63")
AGE_INCREMENT = 1


async def main() -> None:
    """
    Increment Demo.age by AGE_INCREMENT, verify, then restore.
    """
    session = Session()
    try:
        before_age = await (
            session.select(Demo.age)
            .where(Demo.id == DEMO_ID)
            .fetchval()
        )
        if before_age is None:
            print(f"Demo id not found: {DEMO_ID}")
            return

        print(f"Before age: {before_age}")
        await (
            session.update(Demo)
            .values(age=Demo.age + AGE_INCREMENT)
            .where(Demo.id == DEMO_ID)
            .execute()
        )
        await session.commit()

        after_increment_age = await (
            session.select(Demo.age)
            .where(Demo.id == DEMO_ID)
            .fetchval()
        )
        print(f"After +{AGE_INCREMENT}: {after_increment_age}")

        # await (
        #     session.update(Demo)
        #     .values(age=Demo.age - AGE_INCREMENT)
        #     .where(Demo.id == DEMO_ID)
        #     .execute()
        # )
        # await session.commit()

        restored_age = await (
            session.select(Demo.age)
            .where(Demo.id == DEMO_ID)
            .fetchval()
        )
        print(f"Restored age: {restored_age}")
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
