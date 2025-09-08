"""
Migration script to import data from old_datas JSON files into the new database models.
This script handles the conversion from the old Django-style data to the new SQLAlchemy models.
Uses async/await for better performance with large datasets.
"""
import asyncio
import json
import sys
import time
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from portal.container import Container
from portal.libs.database import Session
from portal.libs.logger import logger
from portal.models import (
    PortalConference, PortalConferenceInstructors, PortalEventSchedule,
    PortalFaqCategory, PortalFaq, PortalFcmDevice, PortalFcmUserDevice,
    PortalFeedback, PortalInstructor, PortalLocation, PortalUser, PortalUserProfile, PortalUserThirdPartyAuth, PortalTestimony, PortalWorkshop, PortalWorkshopRegistration,
)


class AsyncDataMigrator:
    """Async data migration class to handle importing JSON data into database models"""

    def __init__(self):
        self.container = Container()
        self.session: Optional[Session] = None
        self.old_data_path = Path("old_datas")
        self.migration_stats = {
            "success": 0,
            "errors": 0,
            "skipped": 0,
            "details": []
        }
        self.batch_size = 100  # Process records in batches for better performance
        # Get current timestamp for records without created_at/updated_at
        self.current_timestamp = datetime.now()
        # Base timestamp for sequence calculation
        self.base_timestamp = time.time()
        # Load workshop time slots mapping
        self.workshop_time_slots = self.load_workshop_time_slots()
        self.provider_id = uuid.UUID("3025cf66-45e8-4cc7-acf1-1098129bbdec")

    async def __aenter__(self):
        # Get db_session from container
        postgres_connection = self.container.postgres_connection()
        self.session = self.container.db_session(postgres_connection=postgres_connection)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def log_migration(self, table_name: str, action: str, record_id: str, status: str, error: str = None):
        """Log migration details"""
        self.migration_stats["details"].append(
            {
                "table": table_name,
                "action": action,
                "record_id": record_id,
                "status": status,
                "error": error
            }
        )

        if status == "success":
            self.migration_stats["success"] += 1
        elif status == "error":
            self.migration_stats["errors"] += 1
        else:
            self.migration_stats["skipped"] += 1

    def convert_boolean(self, value: Any) -> bool:
        """Convert string boolean to Python boolean"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('t', 'true', '1', 'yes')
        return bool(value)

    def convert_datetime(self, value: str) -> Optional[datetime]:
        """Convert string datetime to Python datetime"""
        if not value:
            return None
        try:
            normalized = value.replace('Z', '+00:00')
            # Normalize timezone like +00 to +00:00 or -08 to -08:00
            if re.search(r"[+-]\d{2}$", normalized):
                normalized = normalized + ":00"
            return datetime.fromisoformat(normalized)
        except (ValueError, AttributeError):
            return None

    def convert_uuid(self, value: str) -> Optional[uuid.UUID]:
        """Convert string UUID to Python UUID"""
        if not value:
            return None
        try:
            return uuid.UUID(value)
        except (ValueError, AttributeError):
            return None

    def calculate_sequence(self, sort_order: Any, index: int = 0) -> float:
        """Calculate sequence value combining sort_order with timestamp to maintain original order"""
        # Convert sort_order to float, default to 0 if invalid
        try:
            sort_value = float(sort_order) if sort_order is not None else 0.0
        except (ValueError, TypeError):
            sort_value = 0.0

        # Combine base timestamp with sort_order and index to maintain order
        # Use small increments to preserve original sort_order priority
        sequence = self.base_timestamp + (sort_value * 0.001) + (index * 0.000001)
        return sequence

    def load_json_file(self, filename: str) -> List[Dict[str, Any]]:
        """Load JSON data from file"""
        file_path = self.old_data_path / filename
        if not file_path.exists():
            logger.warning(f"File {filename} not found")
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} records from {filename}")
                return data
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return []

    def load_workshop_time_slots(self) -> Dict[str, Dict[str, Any]]:
        """Load workshop time slots and create a mapping dictionary with id as key"""
        data = self.load_json_file("portal_workshop_time_slot.json")
        time_slots_dict = {}

        for record in data:
            if self.convert_boolean(record.get("is_removed", False)):
                continue
            time_slots_dict[record["id"]] = record

        logger.info(f"Loaded {len(time_slots_dict)} workshop time slots for mapping")
        return time_slots_dict

    async def process_batch(
        self, records: List[Dict[str, Any]], table_name: str,
        record_processor, model_class, skip_removed: bool = True, conflict: dict = None, skip_error: bool = False
    ):
        """Process a batch of records asynchronously"""
        # Set default conflict handling if not provided
        if conflict is None:
            conflict = {
                "method": "do_update",
                "constraint": "pk_" + model_class.__tablename__,
                "set_": None  # Will be set to data during execution
            }

        for index, record in enumerate(records):
            if skip_removed and self.convert_boolean(record.get("is_removed", False)):
                self.log_migration(table_name, "insert", record.get("id", "unknown"), "skipped")
                continue

            try:
                data = record_processor(record, index)
                if data:
                    # Create a copy of conflict dict to avoid modifying the original
                    conflict_params = conflict.copy()

                    if conflict_params.get("method") == "do_nothing":
                        # Remove method from params to avoid passing it to on_conflict_do_nothing
                        conflict_params.pop("method", None)
                        await self.session.insert(model_class).values(**data).on_conflict_do_nothing(**conflict_params).execute()
                    else:
                        # Default to do_update
                        conflict_params.pop("method", None)
                        # Set the data to update if not specified
                        if conflict_params.get("set_") is None:
                            conflict_params["set_"] = data
                        await self.session.insert(model_class).values(**data).on_conflict_do_update(**conflict_params).execute()

                    self.log_migration(table_name, "insert", record.get("id", "unknown"), "success")
            except Exception as e:
                self.log_migration(table_name, "insert", record.get("id", "unknown"), "error", str(e))
                if skip_error:
                    continue
                raise e

    async def migrate_locations(self):
        """Migrate location data"""
        logger.info("=== Migrating Locations ===")
        data = self.load_json_file("portal_location.json")

        def process_location_record(record, index):
            return {
                "id": self.convert_uuid(record["id"]),
                "name": record["name"],
                "address": record.get("address"),
                "floor": record.get("floor"),
                "room_number": record.get("room_number"),
                "latitude": record.get("latitude"),
                "longitude": record.get("longitude"),
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
                "description": record.get("description"),
                "remark": record.get("remark")
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(batch, "portal_location", process_location_record, PortalLocation)

            # Commit after all locations are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} locations")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate locations: {e}")
            raise

    async def migrate_instructors(self):
        """Migrate instructor data"""
        logger.info("=== Migrating Instructors ===")
        data = self.load_json_file("portal_instructor.json")

        def process_instructor_record(record, index):
            return {
                "id": self.convert_uuid(record["id"]),
                "name": record["name"],
                "title": record.get("title"),
                "bio": record.get("bio"),
                "sequence": self.calculate_sequence(record.get("sort_order"), index),
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
                "description": record.get("description"),
                "remark": record.get("remark")
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(batch, "portal_instructor", process_instructor_record, PortalInstructor)

            # Commit after all instructors are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} instructors")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate instructors: {e}")
            raise

    async def migrate_conferences(self):
        """Migrate conference data"""
        logger.info("=== Migrating Conferences ===")
        data = self.load_json_file("portal_conference.json")

        def process_conference_record(record, index):
            return {
                "id": self.convert_uuid(record["id"]),
                "title": record["title"],
                "start_date": datetime.strptime(record["start_date"], "%Y-%m-%d").date(),
                "end_date": datetime.strptime(record["end_date"], "%Y-%m-%d").date(),
                "is_active": self.convert_boolean(record.get("active", True)),
                "location_id": self.convert_uuid(record.get("location_id")),
                "timezone": "Asia/Taipei",  # 預設時區，因為 JSON 中沒有此欄位
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
                "description": record.get("description"),
                "remark": record.get("remark")
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(batch, "portal_conference", process_conference_record, PortalConference)

            # Commit after all conferences are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} conferences")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate conferences: {e}")
            raise

    async def migrate_conference_instructors(self):
        """Migrate conference instructors data"""
        logger.info("=== Migrating Conference Instructors ===")
        data = self.load_json_file("portal_conference_instructors.json")

        def process_conference_instructor_record(record, index):
            return {
                "conference_id": self.convert_uuid(record["conference_id"]),
                "instructor_id": self.convert_uuid(record["instructor_id"]),
                "is_primary": self.convert_boolean(record.get("is_primary", False)),
                "sequence": self.calculate_sequence(record.get("sort_order"), index)
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(
                    batch, "portal_conference_instructors",
                    process_conference_instructor_record, PortalConferenceInstructors, skip_removed=False
                )

            # Commit after all conference instructors are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} conference instructors")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate conference instructors: {e}")
            raise

    async def migrate_event_schedules(self):
        """Migrate event schedule data"""
        logger.info("=== Migrating Event Schedules ===")
        data = self.load_json_file("portal_event_schedule.json")

        def process_event_schedule_record(record, index):
            return {
                "id": self.convert_uuid(record["id"]),
                "conference_id": self.convert_uuid(record["conference_id"]),
                "title": record["title"],
                "start_datetime": self.convert_datetime(record.get("start_time")),
                "end_datetime": self.convert_datetime(record.get("start_time")),
                "timezone": record.get("time_zone", "Asia/Taipei"),
                "text_color": record.get("text_color"),
                "background_color": record.get("background_color"),
                "sequence": self.calculate_sequence(record.get("sort_order"), index),
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
                "description": record.get("description"),
                "remark": record.get("remark")
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(batch, "portal_event_schedule", process_event_schedule_record, PortalEventSchedule)

            # Commit after all event schedules are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} event schedules")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate event schedules: {e}")
            raise

    async def migrate_faq_categories(self):
        """Migrate FAQ category data"""
        logger.info("=== Migrating FAQ Categories ===")
        data = self.load_json_file("portal_faq_category.json")

        def process_faq_category_record(record, index):
            return {
                "id": self.convert_uuid(record["id"]),
                "name": record["name"],
                "sequence": self.calculate_sequence(record.get("sort_order"), index),
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
                "description": record.get("description"),
                "remark": record.get("remark")
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(batch, "portal_faq_category", process_faq_category_record, PortalFaqCategory)

            # Commit after all FAQ categories are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} FAQ categories")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate FAQ categories: {e}")
            raise

    async def migrate_faqs(self):
        """Migrate FAQ data"""
        logger.info("=== Migrating FAQs ===")
        data = self.load_json_file("portal_faq.json")

        def process_faq_record(record, index):
            return {
                "id": self.convert_uuid(record["id"]),
                "category_id": self.convert_uuid(record["category_id"]),
                "question": record["question"],
                "answer": record["answer"],
                "related_link": record.get("related_link"),
                "sequence": self.calculate_sequence(record.get("sort_order"), index),
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
                "description": record.get("description"),
                "remark": record.get("remark")
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(batch, "portal_faq", process_faq_record, PortalFaq)

            # Commit after all FAQs are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} FAQs")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate FAQs: {e}")
            raise

    async def migrate_fcm_devices(self):
        """Migrate FCM device data"""
        logger.info("=== Migrating FCM Devices ===")
        data = self.load_json_file("portal_fcm_device.json")

        def process_fcm_device_record(record, index):
            if not record.get("token"):
                return None
            return {
                "id": self.convert_uuid(record["id"]),
                "device_key": record["device_id"],
                "token": record["token"],
                "expired_at": self.convert_datetime(record.get("expired_at")),
                "additional_data": record.get("additional_data"),
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
                "description": record.get("description"),
                "remark": record.get("remark")
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(batch, "portal_fcm_device", process_fcm_device_record, PortalFcmDevice)

            # Commit after all FCM devices are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} FCM devices")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate FCM devices: {e}")
            raise

    async def migrate_fcm_user_devices(self):
        """Migrate FCM user device data"""
        logger.info("=== Migrating FCM User Devices ===")
        data = self.load_json_file("portal_fcm_device_accounts.json")

        def process_fcm_user_device_record(record, index):
            return {
                "user_id": self.convert_uuid(record["account_id"]),
                "device_id": self.convert_uuid(record["fcmdevice_id"])
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(
                    batch, "portal_fcm_user_device",
                    process_fcm_user_device_record, PortalFcmUserDevice,
                    skip_removed=False,
                    conflict={
                        "method": "do_nothing",
                        "constraint": f"uq_{PortalFcmUserDevice.__tablename__}_{PortalFcmUserDevice.user_id.name}_{PortalFcmUserDevice.device_id.name}"
                    },
                    skip_error=True
                )

            # Commit after all FCM user devices are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} FCM user devices")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate FCM user devices: {e}")
            raise

    async def migrate_feedback(self):
        """Migrate feedback data"""
        logger.info("=== Migrating Feedback ===")
        data = self.load_json_file("portal_feedback.json")

        def process_feedback_record(record, index):
            return {
                "id": self.convert_uuid(record["id"]),
                "name": record["name"],
                "email": record.get("email"),
                "message": record["message"],
                "status": record.get("status", 1),  # Assuming 1 is PENDING
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
                "description": record.get("description"),
                "remark": record.get("remark")
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(batch, "portal_feedback", process_feedback_record, PortalFeedback)

            # Commit after all feedback records are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} feedback records")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate feedback: {e}")
            raise

    async def migrate_testimonies(self):
        """Migrate testimony data"""
        logger.info("=== Migrating Testimonies ===")
        data = self.load_json_file("portal_testimony.json")

        def process_testimony_record(record, index):
            return {
                "id": self.convert_uuid(record["id"]),
                "name": record["name"],
                "phone_number": record.get("phone_number"),
                "share": self.convert_boolean(record.get("share", False)),
                "message": record["message"],
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
                "description": record.get("description"),
                "remark": record.get("remark")
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(batch, "portal_testimony", process_testimony_record, PortalTestimony)

            # Commit after all testimonies are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} testimonies")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate testimonies: {e}")
            raise

    async def migrate_users(self):
        """Migrate user data"""
        logger.info("=== Migrating Users ===")
        data = self.load_json_file("portal_account.json")

        try:
            for record in data:
                try:
                    # Insert user
                    user_data = {
                        "id": self.convert_uuid(record["id"]),
                        "phone_number": record["phone_number"],
                        "email": record.get("email"),
                        "is_active": self.convert_boolean(record.get("is_active", True)),
                        "verified": self.convert_boolean(record.get("verified", False)),
                        "last_login_at": self.convert_datetime(record.get("last_login")),
                        "created_at": self.current_timestamp,
                        "updated_at": self.current_timestamp,
                        "created_by": record.get("created_by", "system"),
                        "updated_by": record.get("updated_by", "system"),
                        "remark": record.get("remark")
                    }
                    await self.session.insert(PortalUser).values(**user_data).on_conflict_do_update(
                        constraint="pk_portal_user",
                        set_=user_data
                    ).execute()

                    self.log_migration("portal_user", "insert", record["id"], "success")

                    # Create user profile if display_name, gender, or is_service exists
                    if record.get("display_name") or record.get("gender") or record.get("is_service") is not None:
                        profile_data = {
                            "id": uuid.uuid4(),
                            "user_id": self.convert_uuid(record["id"]),
                            "display_name": record.get("display_name"),
                            "gender": record.get("gender"),
                            "is_ministry": self.convert_boolean(record.get("is_service", False)),
                            "created_at": self.current_timestamp,
                            "updated_at": self.current_timestamp,
                            "created_by": record.get("created_by", "system"),
                            "updated_by": record.get("updated_by", "system"),
                            "description": record.get("description")
                        }
                        await self.session.insert(PortalUserProfile).values(**profile_data).on_conflict_do_update(
                            index_elements=["user_id"],
                            set_=profile_data
                        ).execute()

                        self.log_migration("portal_user_profile", "insert", record["id"], "success")

                except Exception as e:
                    self.log_migration("portal_user", "insert", record.get("id", "unknown"), "error", str(e))
                    logger.error(f"Error migrating user {record.get('id')}: {e}")

                # Commit after all users are processed
                await self.session.commit()
                logger.info(f"✓ Successfully migrated {len(data)} users")

        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate users: {e}")
            raise

    async def migrate_user_third_party_auth(self):
        """Migrate user third-party auth data"""
        logger.info("=== Migrating User Third Party Auth ===")
        data = self.load_json_file("portal_account_auth_provider.json")

        def process_third_party_auth_record(record, index):
            extra = record.get("extra_data")
            additional_data = None
            if isinstance(extra, dict):
                additional_data = extra
            elif isinstance(extra, str) and extra:
                try:
                    additional_data = json.loads(extra)
                except Exception:
                    additional_data = None

            return {
                "id": self.convert_uuid(record["id"]),
                "user_id": self.convert_uuid(record["account_id"]),
                "provider_id": self.provider_id,
                "provider_uid": record.get("provider_id"),
                "access_token": record.get("access_token"),
                "refresh_token": record.get("refresh_token"),
                "token_expires_at": self.convert_datetime(record.get("token_expires_at")),
                "additional_data": json.dumps(additional_data) if additional_data else None,
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(
                    batch,
                    "portal_user_third_party_auth",
                    process_third_party_auth_record,
                    PortalUserThirdPartyAuth,
                )

            # Commit after all third-party auth records are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} user third-party auth records")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate user third-party auth: {e}")
            raise

    async def migrate_workshops(self):
        """Migrate workshop data"""
        logger.info("=== Migrating Workshops ===")
        data = self.load_json_file("portal_workshop.json")

        def process_workshop_record(record, index):
            # Get time slot data using time_slot_id
            time_slot_id = record.get("time_slot_id")
            time_slot_data = self.workshop_time_slots.get(time_slot_id, {})

            return {
                "id": self.convert_uuid(record["id"]),
                "title": record["title"],
                "start_datetime": self.convert_datetime(time_slot_data.get("start_datetime")),
                "end_datetime": self.convert_datetime(time_slot_data.get("end_datetime")),
                "conference_id": self.convert_uuid(record["conference_id"]),
                "location_id": self.convert_uuid(record.get("location_id")),
                "participants_limit": record.get("participants_limit"),
                "slido_url": record.get("slido_url"),
                "timezone": time_slot_data.get("time_zone", "Asia/Taipei"),
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
                "description": record.get("description"),
                "remark": record.get("remark")
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(batch, "portal_workshop", process_workshop_record, PortalWorkshop)

            # Commit after all workshops are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} workshops")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate workshops: {e}")
            raise

    async def migrate_workshop_registrations(self):
        """Migrate workshop registration data"""
        logger.info("=== Migrating Workshop Registrations ===")
        data = self.load_json_file("portal_workshop_registration.json")

        def process_workshop_registration_record(record, index):
            return {
                "id": self.convert_uuid(record["id"]),
                "workshop_id": self.convert_uuid(record["workshop_id"]),
                "user_id": self.convert_uuid(record["account_id"]),
                "registered_at": self.convert_datetime(record.get("registered_at")),
                "unregistered_at": self.convert_datetime(record.get("unregistered_at")),
                "created_at": self.current_timestamp,
                "updated_at": self.current_timestamp,
                "created_by": record.get("created_by", "system"),
                "updated_by": record.get("updated_by", "system"),
                "description": record.get("description"),
                "remark": record.get("remark")
            }

        try:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                await self.process_batch(
                    batch, "portal_workshop_registration",
                    process_workshop_registration_record, PortalWorkshopRegistration, skip_removed=False
                )

            # Commit after all workshop registrations are processed
            await self.session.commit()
            logger.info(f"✓ Successfully migrated {len(data)} workshop registrations")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"✗ Failed to migrate workshop registrations: {e}")
            raise

    async def run_migration(self):
        """Run the complete migration process"""
        logger.info("Starting async data migration from old_datas to new database models...")

        # Migrate in dependency order
        # await self.migrate_users()
        await self.migrate_user_third_party_auth()
        # await self.migrate_locations()
        # await self.migrate_instructors()
        # await self.migrate_conferences()
        # await self.migrate_conference_instructors()
        # await self.migrate_event_schedules()
        # await self.migrate_faq_categories()
        # await self.migrate_faqs()
        # await self.migrate_fcm_devices()
        # await self.migrate_fcm_user_devices()
        # await self.migrate_feedback()
        # await self.migrate_testimonies()
        # await self.migrate_workshops()
        # await self.migrate_workshop_registrations()

        # Print migration summary
        logger.info("=" * 50)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Success: {self.migration_stats['success']}")
        logger.info(f"Errors: {self.migration_stats['errors']}")
        logger.info(f"Skipped: {self.migration_stats['skipped']}")

        if self.migration_stats['errors'] > 0:
            logger.error("Error Details:")
            for detail in self.migration_stats['details']:
                if detail['status'] == 'error':
                    logger.error(f"  {detail['table']} - {detail['record_id']}: {detail['error']}")

        # Save detailed log to file
        with open('migration_log.json', 'w', encoding='utf-8') as f:
            json.dump(self.migration_stats, f, indent=2, default=str)
        logger.info("Detailed migration log saved to: migration_log.json")


async def main():
    """Main async function to run the migration"""
    try:
        async with AsyncDataMigrator() as migrator:
            await migrator.run_migration()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
