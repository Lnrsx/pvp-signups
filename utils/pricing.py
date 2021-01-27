from bisect import bisect
from utils.config import ipricing


def set_rating(instname, bracket, current_rating, end_rating):
    price = 0
    _pricing = ipricing[instname].set_rating[bracket]
    brackets = ipricing[instname].brackets
    end_rating_bracket = bisect(brackets, end_rating)

    while bisect(brackets, current_rating) < end_rating_bracket:
        rating_to_next_bracket = brackets[bisect(brackets, current_rating)] - current_rating
        current_bracket_price = _pricing[bisect(brackets, current_rating) - 1]
        price += rating_to_next_bracket * current_bracket_price
        current_rating = brackets[bisect(brackets, current_rating)]

    if bisect(brackets, current_rating) == bisect(brackets, end_rating):
        current_bracket_price = _pricing[bisect(brackets, current_rating) - 1]
        price += (end_rating - current_rating) * current_bracket_price

    return price


def one_win(instname, bracket, current_rating):
    pricing = ipricing[instname].one_win[bracket]
    if current_rating > ipricing[instname].one_win_brackets[-1]:
        current_rating = ipricing[instname].one_win_brackets[-1]

    return pricing[bisect(ipricing[instname].one_win_brackets, current_rating) - 1]


def hourly(instname, bracket):
    return ipricing[instname].hourly[bracket]
