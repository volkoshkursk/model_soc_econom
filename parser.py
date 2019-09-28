from selenium import webdriver

import lxml.html
import lxml.etree
import requests

import logging.config


def load():
    res = []
    with open('cache') as f:
        for line in f:
            res.append(line[:-1])
    return res


def save(url):
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
    получаем ссылки на закупки с сайта zakupki.gov.ru
    :param address_1:
    :param address_2:
    :param num: номер страницы в поиске
    :param log: логгер
    :param pages: (опционально) сколько всего страниц
    :return: лист ссылок на аукционы
    """
    log.info('ask for ' + str(num) + ' page')
    print(num)
    response = requests.get(address_1 + str(num) + address_2)
    address_update = False
    if response.status_code != 200 or 'Поиск не дал результатов' in response.text:
        response = requests.get('http://zakupki.gov.ru/epz/contract/quicksearch/search.html?')
        pages = None
        address_update = True
    if response.status_code == 200:
        tree = lxml.html.fromstring(response.text)
        objects = tree.xpath('//div[contains(@class, "registerBox")]//tr')
        links = tree.xpath('//div[contains(@class, "registerBox")]//td[@class="descriptTenderTd"]'
                           '//a[contains(@class, "displayInlineBlockUsual widthAutoUsual")]/@href')
        log.debug('got ' + str(len(links)) + ' links')
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
            return links + zakupki(num + 1, log, address_1, address_2, pages)
        else:
            return links
    else:
        log.error('status code: ' + str(response.status_code))


if __name__ == '__main__':
    logging.config.fileConfig('log_config')
    logger = logging.getLogger("root")
    logger.info("program started")
    cache = load()
    print(len(zakupki(1, logger.getChild('get_links'), cache[0], cache[1])))
