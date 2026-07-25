"""CLI entrypoint for loading demo data into the configured database."""

import asyncio

from api.database import async_session
from api.seeders.demo_data import seed_demo_data


async def _main() -> None:
    async with async_session() as session:
        await seed_demo_data(session)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
