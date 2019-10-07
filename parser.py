from selenium import webdriver

import lxml.html
import lxml
import lxml.etree
import requests
import re
import sqlite3

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
    for ii in range(len(url[1])):
        if url[1][ii] not in {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}:
            url[1] = url[1][ii:]
            break
    with open('cache', 'w') as f:
        for ii in url:
            f.write(ii + '\n')
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
        for ii in objects:
            single = lxml.html.fromstring(lxml.etree.tostring(ii, pretty_print=False))  # только нужный нам кусочек
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
    link = link[0]
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
            head = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]//tr[@class="tdHead"]/td/text()')
            # в таблице могут быть не все окна
            result = []
            code, good_group_name, unit, quantity, price, cost = None, None, None, None, None, None
            if 'Код позиции' in head:
                code = True
            if 'Наименование товара, работы, услуги' in head:
                good_group_name = True
            if 'Единица' in head:
                unit = True
            if 'Количество' in head:
                quantity = True
            if 'Цена за ед.изм.' in head:
                price = True
            if 'Стоимость' in head:
                cost = True
            for ii in nodes:
                single_node = lxml.html.fromstring(lxml.etree.tostring(ii, pretty_print=False))
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
                for ii in range(len(nodes)):
                    single_node = lxml.html.fromstring(lxml.etree.tostring(nodes[ii], pretty_print=False))
                    temp = single_node.xpath('//td[@class="alignRight"]/text()')
                    temp2 = single_node.xpath('//td[not (@*)]/text()')
                    if len(temp) == len(temp2):
                        for j in range(len(temp2)):
                            temp2[j] = float(re.sub(r'[^,0-9]', '', temp2[j]).translate(str.maketrans(',', '.')))
                        amount = sum(temp2)
                    else:
                        amount = result[ii][5] - 100

                    if amount == result[ii][5]:
                        for j in range(len(temp)):
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]), temp2[j] / amount]
                    else:
                        for j in range(len(temp)):
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]), None]
                    result[ii].append(temp)
                    result[ii].append(total)
                    result[ii].append(link)
                    del temp, temp2, amount
            else:
                for ii in range(len(result)):
                    result[ii].append(None)
                    result[ii].append(total)
                    result[ii].append(link)
            log.debug('record loaded')
        elif cond[len(cond) - 1][0:22] == 'medTable':  # для медицины
            del cond
            nodes = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]//table[contains(@class, "orderMedTable")]'
                               '/tbody/tr[not (@*)]')
            result = []
            code, good_name, unit, quantity, price, cost = 'MED', None, None, None, None, None
            for ii in nodes:
                single_node = lxml.html.fromstring(lxml.etree.tostring(ii, pretty_print=False))
                if 'delimTr' in single_node.xpath('//td/@class'):
                    continue
                string = single_node.xpath('//td/text()')
                good_name = re.sub(r'(\n)|(\s\s)', '', string[1])
                unit = re.sub(r'(\n)|(\s\s)', '', string[4])
                quantity = float(re.sub(r'[^,0-9]', '', string[5]).translate(str.maketrans(',', '.')))
                price = float(re.sub(r'[^,0-9]', '', string[6]).translate(str.maketrans(',', '.')))
                cost = float(re.sub(r'[^,0-9]', '', string[7]).translate(str.maketrans(',', '.')))
                result.append([place, code, good_name, None, unit, quantity, price, cost, ministry, real_price])
            nodes = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]//tr[@class="toggleTr displayNone"]')

            total = float(re.sub(r'[^,0-9]', '', tree.xpath('//td[text()="Начальная (максимальная) цена контракта"]'
                                                            '/../td/text()')[1]).translate(str.maketrans(',', '.')))
            if len(nodes) == len(result):
                for ii in range(len(nodes)):
                    single_node = lxml.html.fromstring(lxml.etree.tostring(nodes[ii], pretty_print=False))
                    temp = single_node.xpath('//td[@class="alignRight"]/text()')
                    temp2 = single_node.xpath('//td[not (@*)]/text()')
                    if len(temp) == len(temp2):
                        for j in range(len(temp2)):
                            temp2[j] = float(re.sub(r'[^,0-9]', '', temp2[j]).translate(str.maketrans(',', '.')))
                        amount = sum(temp2)
                    else:
                        amount = result[ii][5] - 100

                    if amount == result[ii][5]:
                        for j in range(len(temp)):
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]), temp2[j] / amount]
                    else:
                        for j in range(len(temp)):
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]), None]
                    result[ii].append(temp)
                    result[ii].append(total)
                    result[ii].append(link)
                    del temp, temp2, amount
            else:
                for ii in range(len(result)):
                    result[ii].append(None)
                    result[ii].append(total)
                    result[ii].append(link)
            temp = tree.xpath('//h2[contains(text(),"Сведения о наименовании")]/../div//td/text()')[3::4]
            if len(temp) == len(result):
                for ii in range(len(temp)):
                    result[ii][3] = re.sub(r'(\n)|(\s\s)', '', temp[ii])
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
    list_of_tenders = zakupki(1, logger.getChild('get_links'), cache[0], cache[1], pages=1)
    logger.info('got links')
    conn = sqlite3.connect('collection.db')
    logger.debug('db is opened')
    cursor = conn.cursor()
    cursor.execute("select link,ministry,real_price from inp")
    from_db = cursor.fetchall()
    saved = [set(), set()]  # [set of links, set of tuples (ministry + real_price)]
    for i in from_db:
        saved[0].add(i[0])
        saved[1].add((i[1], i[2]))
    logger.debug('data is ' + str(saved))
    command = ''
    logger.debug('total link: ' + str(len(list_of_tenders)))
    for i in range(len(list_of_tenders)):
        if len(list_of_tenders[i][2]) > 0 and list_of_tenders[i][2][0] not in saved[0]:
            info = more_info(list_of_tenders[i][2], list_of_tenders[i][1], list_of_tenders[i][0],
                             logger.getChild('more_info'))
            command += "INSERT into inp values (" + "'" + str(info[0]) + "','" + str(info[1]) + "','" + str(info[2]) + \
                       "','" + str(info[3]) + "','" + str(info[4]) + "'," + str(info[5]) + ',' + str(info[6]) + ',' +\
                       str(info[7]) + ",'" + str(info[8]) + "'," + str(info[9]) + ",'" + str(info[10]) + "'," + \
                       str(info[11]) + ",'" + str(info[12]) + "'); \n"
        elif (list_of_tenders[i][1], list_of_tenders[i][0]) not in saved[1] and len(list_of_tenders[i][2]) == 0:
            command += "INSERT into inp values (" + "NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,'" + \
                       str(list_of_tenders[i][2]) + "'," + str(list_of_tenders[i][1]) + ", NULL, NULL, NULL); \n"
        else:
            logger.debug('info found in db')
        if i % 10 == 0 and i != 0:
            cursor.execute(command)
            logger.info('sent to db')
        if i % 100 == 0 and i != 0:
            conn.commit()
            logger.info('commit')

    conn.close()
    logger.info(':-)')
