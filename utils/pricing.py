from bisect import bisect

set_rating_pricing = {
    "2v2": [650, 1700, 2100, 2550, 3400, 3800, 4250, 5100, 5950, 6800],
    "3v3": [1300, 3400, 4250, 5100, 6800, 7650, 8500, 10200, 11900, 13600]
}
one_win_pricing = {
    "2v2": [50000, 65000, 80000, 100000],
    "3v3": [100000, 130000, 160000, 200000]
}
hourly_pricing = {
    "2v2": 325000,
    "3v3": 650000
}

brackets = [0, 1500, 1600, 1700, 1800, 1900, 2000, 2100, 2200, 2300, 2401]
one_win_brackets = [0, 1800, 2100, 2400, 3501]


def set_rating_price(bracket, current_rating, end_rating):
    price, pricing = 0, set_rating_pricing[bracket]
    # while the current rating is below the end rating's pricing bracket, jumps to the next bracket and adds the price of that rating
    while bisect(brackets, current_rating) < bisect(brackets, end_rating):
        # adds the difference between current rating to the end of the bracket * pricing of the bracket
        price += (brackets[bisect(brackets, current_rating)] - current_rating) * pricing[bisect(brackets, current_rating) - 1]
        # updates the rating accordingly
        current_rating = brackets[bisect(brackets, current_rating)]

    # when the current rating is in the same pricing bracket as the end rating, adds the product of the difference and pricing of the bracket
    if bisect(brackets, current_rating) == bisect(brackets, end_rating):
        price += (end_rating - current_rating) * pricing[bisect(brackets, current_rating) - 1]

    return price


def one_win_price(bracket, current_rating):
    pricing = one_win_pricing[bracket]
    if current_rating > one_win_brackets[-1]:
        current_rating = one_win_brackets[-1]

    return pricing[bisect(one_win_brackets, current_rating) - 1]


def hourly_price(bracket):
    return hourly_pricing[bracket]
