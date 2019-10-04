from selenium import webdriver

import lxml.html
import lxml
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
    :return: лист названий организаций, цен закупки, ссылок на аукционы
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
                    logger.error(e)
                finally:
                    driver.close()
            pages = int(pages[len(pages) - 1])
        if num < pages:
            return result + zakupki(num + 1, log, address_1, address_2, pages)
        else:
            return result
    else:
        log.error('status code: ' + str(response.status_code))


def more_info(link, ministry, real_price, log):
    """
    Запрос дополнительных сведений об аукционе по ссылке
    :param link: ссылка (не прямая)
    :param ministry: Название заказчика (получено в zakupki)
    :param real_price: Цена по результатам (получено в zakupki)
    :param log: логгер
    :return:
    """
    log.debug('ask for ' + link)
    tree = None
    result = None
    response = requests.get('http://zakupki.gov.ru' + link)
    if response.status_code == 200:
        tree = lxml.html.fromstring(response.text)
    else:
        log.error('status code: ' + str(response.status_code))
        driver = webdriver.Firefox()
        log.info('try to use firefox')
        try:
            driver.get('http://zakupki.gov.ru' + link)
            tree = lxml.html.fromstring(driver.page_source)
        except Exception as e:
            log.error(e)
        finally:
            driver.close()
    if tree is not None:
        place = tree.xpath('//td[text()="Место нахождения"]/../td/text()')[1].split(',')[2][:]
        cond = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]/div/@id')
        if cond[len(cond) - 1][0:22] == 'purchaseObjectTruTable':  # для обычных закупок
            del cond
            nodes = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]//tr[not (@*)]')
            result = []
            code, good_group_name, unit, quantity, price, cost = None, None, None, None, None, None
            for i in nodes:
                single_node = lxml.html.fromstring(lxml.etree.tostring(i, pretty_print=False))
                string = single_node.xpath('//td/text()')
                if len(string) > 2:
                    code = re.sub(r'[^.0-9]', '', string[1])
                    good_group_name = re.sub(r'(\n)|(\s\s)', '', string[2])
                    unit = re.sub(r'(\n)|(\s\s)', '', string[3])
                    quantity = float(re.sub(r'[^,0-9]', '', string[4]).translate(str.maketrans(',', '.')))
                    price = float(re.sub(r'[^,0-9]', '', string[6]).translate(str.maketrans(',', '.')))
                    cost = float(re.sub(r'[^,0-9]', '', string[7]).translate(str.maketrans(',', '.')))
                else:
                    result.append([place, code, re.sub(r'(\n)|(\s\s)', '', string[1]),
                                   good_group_name, unit, quantity, price, cost, ministry, real_price])
            total = float(re.sub(r'[^,0-9]', '', tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]/'
                                                            '/tr[@class="tdTotal"]/td[@class="alignCenter"]/text()')[
                0]).
                          translate(str.maketrans(',', '.')))
            nodes = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]//tr[@class="toggleTr displayNone"]')
            if len(nodes) == len(result):
                for i in range(len(nodes)):
                    single_node = lxml.html.fromstring(lxml.etree.tostring(nodes[i], pretty_print=False))
                    temp = single_node.xpath('//td[@class="alignRight"]/text()')
                    temp2 = single_node.xpath('//td[not (@*)]/text()')
                    if len(temp) == len(temp2):
                        for j in range(len(temp2)):
                            temp2[j] = float(re.sub(r'[^,0-9]', '', temp2[j]).translate(str.maketrans(',', '.')))
                        amount = sum(temp2)
                    else:
                        amount = result[i][5] - 100

                    if amount == result[i][5]:
                        for j in range(len(temp)):
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]), temp2[j] / amount]
                    else:
                        for j in range(len(temp)):
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]), None]
                    result[i].append(temp)
                    result[i].append(total)
                    del temp, temp2, amount
            else:
                for i in range(len(result)):
                    result[i].append(None)
                    result[i].append(total)
            log.debug('record loaded')
        elif cond[len(cond)-1][0:22] == 'medTable':  # для медицины
            del cond
            nodes = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]//table[contains(@class, "orderMedTable")]'
                               '/tbody/tr[not (@*)]')
            result = []
            code, good_name, unit, quantity, price, cost = 'MED', None, None, None, None, None
            for i in nodes:
                single_node = lxml.html.fromstring(lxml.etree.tostring(i, pretty_print=False))
                if 'delimTr' in single_node.xpath('//td/@class'):
                    continue
                string = single_node.xpath('//td/text()')
                good_name = re.sub(r'(\n)|(\s\s)', '', string[1])
                unit = re.sub(r'(\n)|(\s\s)', '', string[4])
                quantity = float(re.sub(r'[^,0-9]', '', string[5]).translate(str.maketrans(',', '.')))
                price = float(re.sub(r'[^,0-9]', '', string[6]).translate(str.maketrans(',', '.')))
                cost = float(re.sub(r'[^,0-9]', '', string[7]).translate(str.maketrans(',', '.')))
                result.append([place, code, good_name, None, unit, quantity, price, cost])
            nodes = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]//tr[@class="toggleTr displayNone"]')

            total = float(re.sub(r'[^,0-9]', '', tree.xpath('//td[text()="Начальная (максимальная) цена контракта"]'
                                                            '/../td/text()')[1]).translate(str.maketrans(',', '.')))
            if len(nodes) == len(result):
                for i in range(len(nodes)):
                    single_node = lxml.html.fromstring(lxml.etree.tostring(nodes[i], pretty_print=False))
                    temp = single_node.xpath('//td[@class="alignRight"]/text()')
                    temp2 = single_node.xpath('//td[not (@*)]/text()')
                    if len(temp) == len(temp2):
                        for j in range(len(temp2)):
                            temp2[j] = float(re.sub(r'[^,0-9]', '', temp2[j]).translate(str.maketrans(',', '.')))
                        amount = sum(temp2)
                    else:
                        amount = result[i][5]-100

                    if amount == result[i][5]:
                        for j in range(len(temp)):
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]), temp2[j]/amount]
                    else:
                        for j in range(len(temp)):
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]), None]
                    result[i].append(temp)
                    result[i].append(total)
                    del temp, temp2, amount
            else:
                for i in range(len(result)):
                    result[i].append(None)
                    result[i].append(total)
            temp = tree.xpath('//h2[contains(text(),"Сведения о наименовании")]/../div//td/text()')[3::4]
            if len(temp) == len(result):
                for i in range(len(temp)):
                    result[i][3] = re.sub(r'(\n)|(\s\s)', '', temp[i])
        else:
            log.warning('table has not been detected')

    else:
        log.error('page ' + link + 'did not downloaded')
    return result


if __name__ == '__main__':
    logging.config.fileConfig('log_config')
    logger = logging.getLogger("root")
    logger.info("program started")
    cache = load()
    # list_of_tenders = zakupki(1, logger.getChild('get_links'), cache[0], cache[1])
    # more_info(zakupki(1, logger.getChild('get_links'), cache[0], cache[1], pages=1)[0][2][0],
    #           logger.getChild('more_info'))
