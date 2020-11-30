import discord
import logging


def base_embed(description, title=''):
    return discord.Embed(
        title=title,
        description=description,
        colour=discord.Colour.purple()
    )


def get_logger(name):
    _logger = logging.getLogger(name)
    if not _logger.handlers:
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
        _logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        _logger.addHandler(console_handler)
        _logger.propagate = False
    return _logger
