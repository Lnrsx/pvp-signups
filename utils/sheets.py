import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import CellNotFound
from utils.misc import get_logger
from utils import exceptions
from utils.config import cfg

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
#
# This file is no longer in use, as payments are handled by another bot
#
# ---------------------------------------------------------------------------


class SheetManager:
    """Represents a GSpread client manager

    Attributes
    -----------
    agcm: :class:`AsyncioGspreadClientManager`
        The client used to access the sheet, requires a google sheet service account JSON file at data/serviceacct_spreadsheet.json,
        instructions on how to get that can be found here: https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account
    """
    def __init__(self):
        self.agcm = gspread_asyncio.AsyncioGspreadClientManager(self._get_creds, gspread_delay=0.0)

    @staticmethod
    def _get_creds():
        return ServiceAccountCredentials.from_json_keyfile_name(
            "data/serviceacct_spreadsheet.json",
            [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/spreadsheets",
            ],
        )

    async def open_sheet(self):
        """:class:`AsyncioGspreadWorksheet`: Gets the google sheet worksheet from the ID and worksheet index in the config"""
        agc = await self.agcm.authorize()
        sh = await agc.open_by_key(cfg.settings["google_sheet_id"])
        return await sh.get_worksheet(cfg.settings["worksheet_index"])

    async def add_pending_booking(self, booking_columns):
        """Appends the booking columns given to the end of the sheet

        Parameters
        -----------
        booking_columns: :class:`list`
            A list of the fields being added to the booking (list index 0 is filled at column 'A' etc).
        """
        sheet1 = await self.open_sheet()
        await sheet1.append_rows([booking_columns], value_input_option='USER_ENTERED')

    async def get_pending_booking(self, booking):
        """List[gspread.models.Cell]: Returns a list of the cells present on the row of the booking given from ID

        Raises
        -------
        RequestFailed
            Either the booking has already been completed, or the booking is not present on the sheet
        """
        try:
            sheet1 = await self.open_sheet()
            booking_cell = await sheet1.find(booking.id)
            booking_row = await sheet1.range(f"A{booking_cell.row}:L{booking_cell.row}")
            assert booking_row[0].value == 'Pending', "Booking has already been completed"
            return booking_row
        except CellNotFound:
            logger.error("SheetManager failed to find a booking that should be there")
            raise exceptions.RequestFailed(f"Spreadsheet data is missing booking ``{booking.id}``, which should be there - please contact management")
        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))

    async def update_booking(self, booking_cells):
        """Updates the booking cells with the new values of :class:`Booking`"""
        sheet1 = await self.open_sheet()
        await sheet1.update_cells(booking_cells, value_input_option='USER_ENTERED')

    async def grab_sheet(self):
        """Gets all bookings from the sheet, used to validate sheet with internal cache"""
        sheet1 = await self.open_sheet()
        sheetinfo = await sheet1.get_all_values()
        del sheetinfo[0]
        return sheetinfo


sheets = SheetManager()
