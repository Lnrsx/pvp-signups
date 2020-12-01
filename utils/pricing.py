from bisect import bisect
from utils.config import cfg


def set_rating(bracket, current_rating, end_rating) -> str:
    price, _pricing, brackets = 0, cfg.pricing['set_rating'][bracket], cfg.pricing['brackets']
    # while the current rating is below the end rating's pricing bracket, jumps to the next bracket and adds the price of that rating
    while bisect(brackets, current_rating) < bisect(brackets, end_rating):
        # adds the difference between current rating to the end of the bracket * pricing of the bracket
        price += (brackets[bisect(brackets, current_rating)] - current_rating) * _pricing[bisect(brackets, current_rating) - 1]
        # updates the rating accordingly
        current_rating = brackets[bisect(brackets, current_rating)]

    # when the current rating is in the same pricing bracket as the end rating, adds the product of the difference and pricing of the bracket
    if bisect(brackets, current_rating) == bisect(brackets, end_rating):
        price += (end_rating - current_rating) * _pricing[bisect(brackets, current_rating) - 1]

    return price


def one_win(bracket, current_rating) -> str:
    pricing = cfg.pricing['one_win'][bracket]
    if current_rating > cfg.pricing['one_win_brackets'][-1]:
        current_rating = cfg.pricing['one_win_brackets'][-1]

    return pricing[bisect(cfg.pricing['one_win_brackets'], current_rating) - 1]


def hourly(bracket) -> str:
    return cfg.pricing['hourly'][bracket]
