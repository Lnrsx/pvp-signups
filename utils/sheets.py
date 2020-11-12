import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials
from utils.dictionaries import booking_override_users
from gspread.exceptions import CellNotFound
from utils.utils import get_logger
from utils import exceptions
logger = get_logger(__name__)


def get_creds():
    # To obtain a service account JSON file, follow these steps:
    # https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account
    return ServiceAccountCredentials.from_json_keyfile_name(
        "data/serviceacct_spreadsheet.json",
        [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )


# Google sheets limits API requests to 100 per 100 seconds
# if this limit is passed, the bot wont be able to access the sheet
agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds, gspread_delay=0.0)


async def open_sheet():
    agc = await agcm.authorize()
    sh = await agc.open_by_key('1jV0xyaXeJNM-Bz9yvEakIUuPz35Etsak6gqEXBu0w0Q')
    return await sh.get_worksheet(0)


async def add_pending_booking(booking_columns):
    sheet1 = await open_sheet()
    return await sheet1.append_rows([booking_columns], value_input_option='USER_ENTERED')


async def get_pending_booking(booking):
    try:
        sheet1 = await open_sheet()
        booking_cell = await sheet1.find(booking.id)
        booking_row = await sheet1.range(f"A{booking_cell.row}:L{booking_cell.row}")
        assert booking_row[0].value == 'pending', "Booking has already been completed"
        assert booking_row[7].value in str(booking.author) or booking_override_users, "Insufficient permissions"
        return booking_row
    except CellNotFound:
        raise exceptions.RequestFailed("Spreadsheet data is corrupted, please contact management")


async def update_booking(booking_cells):
    sheet1 = await open_sheet()
    return await sheet1.update_cells(booking_cells, value_input_option='USER_ENTERED')
