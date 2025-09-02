"""
Import CSV Command
"""
import asyncio
import csv
from collections import defaultdict
from typing import Awaitable, Callable, List, Optional
from urllib.parse import urljoin

import pandas as pd
import phonenumbers
from portal.config import settings
from django.core.management.base import BaseCommand
from pydantic import BaseModel
from firebase_admin import auth
from firebase_admin.auth import PhoneNumberAlreadyExistsError, UserRecord

from portal.apps.account.models import Account, AccountAuthProvider
from portal.libs.consts.enums import Provider


class AccountInfo(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True
    }
    name: Optional[str] = None
    english_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    team: Optional[str] = None
    firebase_user: Optional[UserRecord] = None
    error: bool = False


class Command(BaseCommand):
    """
    Command to import accounts from a CSV file.
    """

    help = "Import accounts from a CSV file."

    def handle(self, *args, **options):
        """
        Handle the command.
        """
        self.stdout.write(self.style.SUCCESS(f"Importing accounts..."))
        asyncio.run(self.import_accounts())
        self.stdout.write(self.style.SUCCESS("Accounts imported successfully."))

    async def import_accounts(self):
        """

        :return:
        """
        csv_file_path = "temp_files/conference_service_list.csv"
        raw_df = pd.read_csv(filepath_or_buffer=csv_file_path, dtype=str)
        raw_df = raw_df.replace({pd.NA: None})

        records = raw_df.to_dict(orient="records")
        invalid_records = []
        tasks = []
        for record in records:
            tasks.append(self.create_or_get_firebase_user(record))

        results: list[AccountInfo] = await asyncio.gather(*tasks)

        account_objs = []
        for result in results:
            if result.error:
                invalid_records.append(result)
                continue
            else:
                account_objs.append(
                    await self.create_account(result)
                )

        with open("temp_files/未匯入資料.csv", "w", newline="", encoding="utf-8") as file:
            csv_writer = csv.writer(file)
            csv_writer.writerow(["中文姓名", "英文名", "Email", "電話", "團隊"])
            for invalid_record in invalid_records:
                csv_writer.writerow([
                    invalid_record.name,
                    invalid_record.english_name,
                    invalid_record.email,
                    invalid_record.phone_number,
                    invalid_record.team
                ])
        self.stdout.write(self.style.SUCCESS(f"Invalid records: {len(invalid_records)}"))
        self.stdout.write(self.style.SUCCESS(f"Account objects created: {len(account_objs)}"))

    async def create_or_get_firebase_user(
        self,
        record: dict,
    ) -> AccountInfo:
        """
        Create or get firebase user.
        :param record:
        :return:
        """
        name: str = record.get("name")
        english_name: str = record.get("english_name")
        email: str = record.get("email")
        phone_number: str = record.get("phone")
        team: str = record.get("team")
        account_info = AccountInfo(
            name=name,
            english_name=english_name,
            email=email,
            phone_number=phone_number,
            team=team
        )
        if not email or not phone_number:
            account_info.error = True
            return account_info

        if not phone_number.startswith("09"):
            account_info.error = True
            return account_info

        phone_number = "+886" + phone_number[1:]

        try:
            parse_phone_num = phonenumbers.parse(number=phone_number)
            if not phonenumbers.is_valid_number(parse_phone_num):
                account_info.error = True
                return account_info
            if not phonenumbers.is_possible_number(parse_phone_num):
                account_info.error = True
                return account_info
            international_phone_number = phonenumbers.format_number(parse_phone_num, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            account_info.error = True
            return account_info

        try:
            firebase_user = auth.create_user(phone_number=international_phone_number)
            account_info.phone_number = international_phone_number
            account_info.firebase_user = firebase_user
            return account_info
        except PhoneNumberAlreadyExistsError:
            firebase_user = auth.get_user_by_phone_number(phone_number=international_phone_number)
            account_info.phone_number = international_phone_number
            account_info.firebase_user = firebase_user
            return account_info
        except Exception as e:
            print(f"Error creating user: {e}")
            account_info.error = True
            return account_info

    async def create_account(self, account_info: AccountInfo) -> Account:
        """
        Bulk create account objects.
        :param account_info:
        :return:
        """
        account_obj = await Account.objects.filter(phone_number=account_info.phone_number).afirst()
        if account_obj:
            if account_obj.email != account_info.email:
                account_obj.email = account_info.email
            account_obj.is_service = True
            if account_obj.remark is not None:
                account_obj.remark += f"\n{account_info.team}"
            else:
                account_obj.remark = account_info.team
            await account_obj.asave()
            return account_obj
        display_name = account_info.name if not account_info.english_name else f"{account_info.name} ({account_info.english_name})"
        account_obj = await Account.objects.acreate(
            display_name=display_name,
            email=account_info.email,
            phone_number=account_info.phone_number,
            is_service=True,
            remark=account_info.team,
        )
        await AccountAuthProvider.objects.acreate(
            account=account_obj,
            provider=Provider.FIREBASE.value,
            provider_id=account_info.firebase_user.uid
        )
        return account_obj
