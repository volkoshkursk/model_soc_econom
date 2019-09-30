from selenium import webdriver

import lxml.html
import lxml.etree
import requests
import re

import logging.config


def load():
    """
    Загрузка ссылки из файла
    :return: части ссылки для дальнейшего их использования в zakupki()
    """
    res = []
    with open('cache') as f:
        for line in f:
            res.append(line[:-1])
    return res


def save(url):
    """
    Сохранение ссылки в файл
    :param url: ссылка
    :return: части ссылки для дальнейшего их использования в zakupki()
    """
    url = url.split('pageNumber=')
    url[0] += 'pageNumber='
    for i in range(len(url[1])):
        if url[1][i] not in {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}:
            url[1] = url[1][i:]
            break
    with open('cache', 'w') as f:
        for i in url:
            f.write(i + '\n')
    return url[0], url[1]


def zakupki(num, log, address_1, address_2, pages=None):
    """
    получаем название покупателей, цены контрактов (реальные) и ссылки на закупки с сайта zakupki.gov.ru
    :param address_1: часть ссылки до номера старницы
    :param address_2: часть ссылки после номера старницы
    :param num: номер страницы в поиске
    :param log: логгер
    :param pages: (опционально) сколько всего страниц
    :return: лист ссылок на аукционы
    """
    log.info('ask for ' + str(num) + ' page')
    print(num)
    response = requests.get(address_1 + str(num) + address_2)
    address_update = False
    result = []
    if response.status_code != 200 or 'Поиск не дал результатов' in response.text:
        response = requests.get('http://zakupki.gov.ru/epz/contract/quicksearch/search.html?')
        pages = None
        address_update = True
    if response.status_code == 200:
        tree = lxml.html.fromstring(response.text)
        objects = tree.xpath('//div[contains(@class, "registerBox")]//tr')
        for i in objects:
            single = lxml.html.fromstring(lxml.etree.tostring(i, pretty_print=False))  # только нужный нам кусочек
            # страницы (данные только об одном аукционе)
            real_price = int(
                re.sub(r'[^0-9]', '', single.xpath('//td[@class="tenderTd"]//strong/text()')[0])) + 0.01 * int(
                single.xpath('//td[@class="tenderTd"]//strong/span/text()')[0][1:])
            name = re.sub(r'[\n]', '', str(single.xpath('//dd[@class="nameOrganization"]/a/text()')[0]))
            link = single.xpath('//td[@class="descriptTenderTd"]'
                                '//a[contains(@class, "displayInlineBlockUsual widthAutoUsual")]/@href')
            result.append([real_price, name, link])
        if pages is None:
            pages = tree.xpath('//ul[@class="pages"]//span/text()')
            if address_update:
                log.info('updating address via Webdriver')
                driver = webdriver.Firefox()
                try:
                    driver.get('http://zakupki.gov.ru/epz/contract/quicksearch/search.html?')
                    driver.find_element_by_xpath('//ul[@class="pages"]//a[@data-pagenumber="2"]').click()
                    address_1, address_2 = save(driver.current_url)
                    log.info('address saved')
                    del address_update
                except Exception as e:
                    if logger is not None:
                        logger.error(e)
                    else:
                        print(e)
                finally:
                    driver.close()
            pages = int(pages[len(pages) - 1])
        if num < pages:
            return result + zakupki(num + 1, log, address_1, address_2, pages)
        else:
            return result
    else:
        log.error('status code: ' + str(response.status_code))


if __name__ == '__main__':
    logging.config.fileConfig('log_config')
    logger = logging.getLogger("root")
    logger.info("program started")
    cache = load()
    print(len(zakupki(1, logger.getChild('get_links'), cache[0], cache[1])))
