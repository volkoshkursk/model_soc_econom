from selenium import webdriver
from collections import namedtuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import logging.config


def yandex(name, logger=None):
    if logger is not None:
        logger = logger.getChild('yandex')
    driver = webdriver.Firefox()
    try:
        pass
    except Exception as e:
        if logger is not None:
            logger.error(e)
        else:
            print(e)
    finally:
        driver.close()

    driver.get("https://yandex.ru/images/")

    assert "Яндекс" in driver.title
