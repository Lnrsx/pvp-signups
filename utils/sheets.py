import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import CellNotFound
from utils.utils import get_logger
from utils import exceptions
from utils.config import cfg

logger = get_logger(__name__)


class SheetManager(object):
    def __init__(self):
        self.agcm = gspread_asyncio.AsyncioGspreadClientManager(self.get_creds, gspread_delay=0.0)

    @staticmethod
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

    async def open_sheet(self):
        agc = await self.agcm.authorize()
        sh = await agc.open_by_key(cfg.settings["google_sheet_id"])
        return await sh.get_worksheet(cfg.settings["worksheet_index"])

    async def add_pending_booking(self, booking_columns):
        sheet1 = await self.open_sheet()
        return await sheet1.append_rows([booking_columns], value_input_option='USER_ENTERED')

    async def get_pending_booking(self, booking):
        try:
            sheet1 = await self.open_sheet()
            booking_cell = await sheet1.find(booking.id)
            booking_row = await sheet1.range(f"A{booking_cell.row}:L{booking_cell.row}")
            assert booking_row[0].value == 'pending', "Booking has already been completed"
            return booking_row
        except CellNotFound:
            logger.error("SheetManager failed to find a booking that should be there")
            raise exceptions.RequestFailed(f"Spreadsheet data is missing booking ``{booking.id}``, which should be there - please contact management")
        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))

    async def update_booking(self, booking_cells):
        sheet1 = await self.open_sheet()
        return await sheet1.update_cells(booking_cells, value_input_option='USER_ENTERED')


sheets = SheetManager()
