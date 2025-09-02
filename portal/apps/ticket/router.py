"""
Ticket router
"""
import numpy as np
import pandas as pd
import phonenumbers
import pytz
from dateutil import parser
from portal.config import settings
from fastapi import APIRouter, Request, UploadFile
from firebase_admin import auth
from firebase_admin.auth import PhoneNumberAlreadyExistsError, UserRecord
from phonenumbers.phonenumberutil import NumberParseException
from pydantic import BaseModel

from portal.apps.account.models import Account, AccountAuthProvider
from portal.apps.ticket.models import TicketRegisterDetail, Ticket
from portal.libs.consts.enums import Provider, Gender
from portal.libs.logger import logger
from portal.libs.utils.async_worker import concurrency_worker

router = APIRouter()


IDENTITY_MAPPING = {
    "主任牧師": "senior_pastor",
    "牧師": "pastor",
    "傳道": "evangelist",
    "神學生": "theology_student",
    "事工負責人": "ministry_leader",
    "會眾": "congregant"
}


class UserInfo(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True
    }
    firebase_user: UserRecord
    exist: bool
    wrong_phone_number: bool


@router.post(
    path="/ticket_register_detail/upload_csv"
)
async def upload_csv(
    request: Request,
    csv_file: UploadFile
):
    """

    :param request:
    :param csv_file:
    :return:
    """
    try:
        raw_df = pd.read_csv(csv_file.file)
        raw_df = raw_df.replace({np.nan: None})
        records = raw_df.to_dict(orient="records")
        # logger.info("record count: %s", len(records))
        # records = records[0:3]
        # create firebase user
        records = [record for record in records if record.get("訂單編號") and record.get("票號")]
        tasks = []
        for record in records:
            if not record.get("訂單編號") and not record.get("票號"):
                continue
            participant_phone_number = record.get("參加人電話")
            participant_phone_number = str(int(participant_phone_number)) if participant_phone_number else None
            tasks.append(create_or_get_firebase_user(participant_phone_number))
        user_infos: list[UserInfo] = await concurrency_worker(tasks)
        for record, user_info in zip(records, user_infos):
            if not user_info:
                continue
            record.setdefault("user_info", user_info)

        record_df = pd.DataFrame(records)
        record_df = record_df.replace({np.nan: None})

        # bulk create account
        # account_result = [Account, Account, Account]
        account_results = await bulk_create_account_objs(records)
        account_mapping = {str(account.phone_number): account for account in account_results}
        pre_convert_records = []
        for _, row in record_df.iterrows():
            temp_record = row.get("user_info")
            if not temp_record:
                continue
            if account := account_mapping.get(temp_record.firebase_user.phone_number):
                pre_convert_records.append({**row, "account": account})

        # bulk create account auth
        await bulk_create_account_auth(records)
        # bulk create ticket register detail
        ticket_register_detail_objs = [
            await create_ticket_register_detail_obj(convert_record)
            for convert_record in pre_convert_records
        ]
        result = await TicketRegisterDetail.objects.abulk_create(objs=ticket_register_detail_objs, ignore_conflicts=True)
        logger.info(f"result count: {len(result)}")
    except Exception as e:
        logger.exception(e)


async def create_or_get_firebase_user(phone_number: str = None) -> UserInfo:
    """

    :param phone_number:
    :return:
    """
    if not phone_number:
        user_record = auth.get_user_by_phone_number(settings.FIREBASE_TEST_PHONE_NUMBER)
        return UserInfo(firebase_user=user_record, exist=False, wrong_phone_number=True)
    try:
        parse_phone_num = phonenumbers.parse(number=f"+{phone_number}")
        international_number = phonenumbers.format_number(parse_phone_num, phonenumbers.PhoneNumberFormat.E164)
    except Exception as e:
        logger.exception(e)
        user_record = auth.get_user_by_phone_number(settings.FIREBASE_TEST_PHONE_NUMBER)
        return UserInfo(firebase_user=user_record, exist=False, wrong_phone_number=True)

    try:
        user_record = auth.create_user(phone_number=international_number)
        return UserInfo(firebase_user=user_record, exist=False, wrong_phone_number=False)
    except PhoneNumberAlreadyExistsError:
        user_record = auth.get_user_by_phone_number(international_number)
        return UserInfo(firebase_user=user_record, exist=True, wrong_phone_number=False)
    except Exception as e:
        user_record = auth.get_user_by_phone_number(settings.FIREBASE_TEST_PHONE_NUMBER)
        return UserInfo(firebase_user=user_record, exist=False, wrong_phone_number=True)


async def create_ticket_register_detail_obj(convert_record: dict) -> TicketRegisterDetail:
    """

    :param convert_record:
    :return:
    """
    remark = ""
    account = convert_record["account"]
    user_info: UserInfo = convert_record["user_info"]
    try:
        ticket_name = str(convert_record["票券名稱"]).split(" PASS")[0]
    except Exception:
        ticket_name = "Regular"
        remark += f"------\n票券名稱導入錯誤: {convert_record.get('票券名稱')}"
    try:
        ticket = await Ticket.objects.filter(title__contains=ticket_name).afirst()
        utc8_registered_at = parser.parse(convert_record["報名時間(GTM+8)"])
        registered_at = pytz.timezone("Asia/Taipei").localize(utc8_registered_at)
        utc_registered_at = registered_at.astimezone(pytz.utc)
        account_obj = await Account.objects.filter(phone_number=account.phone_number).afirst()
        participant_phone_number = convert_record.get("參加人電話")
        participant_phone_number = str(int(participant_phone_number)) if participant_phone_number else None
        if user_info.exist:
            remark += f"------\n參加人: {convert_record.get('參加人姓名')}\n參加人電話: {participant_phone_number}\n(訂購人可能買兩張以上票券)\n"
        if user_info.wrong_phone_number:
            remark += f"------\n錯誤電話號碼: {participant_phone_number}"
        order_person_phone_number = convert_record.get("訂購人電話")
        return TicketRegisterDetail(
            ticket_number=convert_record.get("票號"),
            ticket=ticket,
            account=account_obj,
            belong_church=convert_record.get("所屬教會"),
            identity=IDENTITY_MAPPING.get(convert_record.get("所屬教會身份")),
            registered_at=utc_registered_at,
            order_person_name=convert_record.get("訂購人姓名"),
            order_person_phone_number=str(int(order_person_phone_number)) if order_person_phone_number else None,
            order_person_email=convert_record.get("訂購人Email"),
            remark=remark
        )
    except Exception as e:
        logger.error(e)
        logger.info(f"convert_record: {convert_record}")


async def bulk_create_account_objs(records: list[dict]) -> list[Account]:
    """

    :param records:
    :return:
    """
    account_objs = []
    for record in records:
        if not record.get("user_info"):
            continue
        user_info = record["user_info"]
        firebase_user: UserRecord = user_info.firebase_user
        if "男" in record.get("性別"):
            gender = Gender.MALE
        elif "女" in record.get("性別"):
            gender = Gender.FEMALE
        else:
            gender = Gender.UNKNOWN
        if firebase_user.phone_number == settings.FIREBASE_TEST_PHONE_NUMBER:
            account_obj = Account(phone_number=firebase_user.phone_number)
        else:
            account_obj = Account(
                phone_number=firebase_user.phone_number,
                display_name=record.get("參加人姓名"),
                gender=gender.value
            )
        account_objs.append(account_obj)
    account_results = await Account.objects.abulk_create(objs=account_objs, ignore_conflicts=True)
    return account_results


async def bulk_create_account_auth(records: list[dict]):
    """

    :param records:
    :return:
    """
    account_auth_objs = []
    for record in records:
        if not record.get("user_info"):
            continue
        user_info: UserInfo = record["user_info"]
        firebase_user: UserRecord = user_info.firebase_user
        account_obj = await Account.objects.filter(phone_number=firebase_user.phone_number).afirst()
        account_auth_objs.append(
            AccountAuthProvider(
                account=account_obj,
                provider=Provider.FIREBASE.value,
                provider_id=firebase_user.uid
            )
        )
    await AccountAuthProvider.objects.abulk_create(objs=account_auth_objs, ignore_conflicts=True)
