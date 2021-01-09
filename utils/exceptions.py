class SignupsException(Exception):
    """Base class for PvP Signups exceptions."""


class CancelBooking(SignupsException):
    """User requested or timeout based booking cancellation."""


class BadConfig(SignupsException):
    """Value in config.json invalid."""


class ChannelNotFound(SignupsException):
    """Channel lookup exception."""


class MessageNotFound(SignupsException):
    """Message lookup exception"""


class InvalidTokenResponse(SignupsException):
    """Unsuccessful access token retrieval."""


class RequestFailed(SignupsException):
    """An action the user has requested has failed, class paramater is sent back to the user as str."""


class BookingUntaken(SignupsException):
    """Booking was not taken and will be moved to the untaken boosts board"""


class UnsupportedInstanceType(SignupsException):
    """Booking instance type is not supported"""
