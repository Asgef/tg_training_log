import logging
from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.application.repositories import ISetEntryRepository
from src.domain.models import SetEntry

logger = logging.getLogger(__name__)


class SetEntryRepository(ISetEntryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: Any) -> Optional[SetEntry]:
        try:
            stmt = select(SetEntry).where(SetEntry.id == item_id)
            result = await self.session.execute(stmt)
            set_entry = result.scalar_one_or_none()
            if set_entry:
                logger.debug(f"Retrieved set entry {item_id}.")
            else:
                logger.debug(f"Set entry {item_id} not found.")
            return set_entry
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_by_id for set entry {item_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_by_id for set entry {item_id}: {e}",
                exc_info=True,
            )
            raise

    async def add(self, set_entry: SetEntry) -> SetEntry:
        try:
            self.session.add(set_entry)
            await self.session.commit()
            await self.session.refresh(set_entry)
            logger.info(
                f"Added new set entry {set_entry.id} for session {set_entry.session_id}."
            )
            return set_entry
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in add set entry for session {set_entry.session_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in add set entry for session {set_entry.session_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def update(self, set_entry: SetEntry) -> SetEntry:
        try:
            await self.session.commit()
            await self.session.refresh(set_entry)
            logger.info(f"Updated set entry {set_entry.id}.")
            return set_entry
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in update set entry {set_entry.id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in update set entry {set_entry.id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def delete(self, item_id: Any) -> None:
        try:
            set_entry = await self.get_by_id(item_id)
            if set_entry:
                await self.session.delete(set_entry)
                await self.session.commit()
                logger.info(f"Deleted set entry {item_id}.")
            else:
                logger.warning(f"Attempted to delete non-existent set entry {item_id}.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in delete set entry {item_id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in delete set entry {item_id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise

    async def add_set_entry(self, set_entry: SetEntry) -> SetEntry:
        # This method is redundant with add(), but required by interface
        return await self.add(set_entry)
