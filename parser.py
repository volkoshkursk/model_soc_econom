from selenium import webdriver
from selenium.webdriver.firefox.options import Options

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
                options = Options()
                options.headless = True
                driver = webdriver.Firefox(options=options)
                try:
                    driver.get('http://zakupki.gov.ru/epz/contract/quicksearch/search.html?')
                    driver.find_element_by_xpath('//ul[@class="pages"]//a[@data-pagenumber="2"]').click()
                    address_1, address_2 = save(driver.current_url)
                    log.info('address saved')
                    del address_update
                except Exception as exc:
                    logger.error(exc)
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
        log.warning('status code: ' + str(response.status_code))
        options = Options()
        options.headless = True
        try:
            driver = webdriver.Firefox(options=options)
        except Exception:
            driver = webdriver.Firefox()
        log.info('try to use firefox')
        try:
            driver.get('http://zakupki.gov.ru' + link)
            if 'Сайт временно недоступен' in driver.title:
                log.error('site unavailable')
            else:
                tree = lxml.html.fromstring(driver.page_source)
        except Exception as exc:
            log.error(exc)
        finally:
            driver.close()
    if tree is not None:
        place = tree.xpath('//td[text()="Место нахождения"]/../td/text()')[1].split(',')[2][:]
        cond = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]/div/@id')
        if cond[len(cond) - 1][0:22] == 'purchaseObjectTruTable':  # для обычных закупок
            del cond
            nodes = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]//tr[not (@*)]')
            head = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]//tr[@class="tdHead"]/td/text()')
            head = set(map(lambda x: re.sub(r'[^A-Za-zА-Яа-я]', '', x), head))
            # в таблице могут быть не все окна
            result = []
            code, good_group_name, unit, quantity, price, cost = 'NULL', 'NULL', 'NULL', 'NULL', 'NULL', 'NULL'
            if 'Кодпозиции' in head:
                code_cond = 1
            else:
                code_cond = 0
            if 'Наименованиетовараработыуслуги' in head:
                good_group_name_cond = 1
            else:
                good_group_name_cond = 0
            if 'Единица' in head:
                unit_cond = 1
            else:
                unit_cond = 0
            if 'Количество' in head:
                quantity_cond = 1
            else:
                quantity_cond = 0
            if 'Ценазаедизм' in head:
                price_cond = 1
            else:
                price_cond = 0
            if 'Стоимость' in head:
                cost_cond = 1
            else:
                cost_cond = 0
            for ii in nodes:
                single_node = lxml.html.fromstring(lxml.etree.tostring(ii, pretty_print=False))
                string = single_node.xpath('//td/text()')
                if len(string) > 3:
                    if code_cond:
                        code = re.sub(r'[^-.0-9]', '', string[1])
                        if code == '':
                            code = re.sub(r'[^-.0-9]', '', single_node.xpath('//td[@class="alignLeft"]/a/text()')[0])
                        if code == '':
                            code = 'NULL'
                    if good_group_name_cond:
                        good_group_name = re.sub(r'(\n)|(\s\s)', '', string[1 + code_cond])
                        if good_group_name == '':
                            good_group_name = re.sub(r'(\n)|(\s\s)', '',
                                                     string[len(string)-cost_cond-2-price_cond-quantity_cond-unit_cond])
                        if good_group_name == '':
                            good_group_name = 'NULL'
                    if unit_cond:
                        unit = re.sub(r'(\n)|(\s\s)', '', string[len(string)-cost_cond-2-price_cond-quantity_cond])
                        # unit = re.sub(r'(\n)|(\s\s)', '', string[1 + code_cond + good_group_name_cond])
                        # if unit == '' or unit == good_group_name:
                        #     unit = re.sub(r'(\n)|(\s\s)', '', string[len(string)-
                        #                                              cost_cond-2-price_cond-quantity_cond])
                        if unit == '' or unit == good_group_name:
                            unit = 'NULL'
                    if quantity_cond:
                        quantity = re.sub(r'[^,0-9]', '', string[1 + code_cond + good_group_name_cond + unit_cond]). \
                            translate(str.maketrans(',', '.'))
                        if quantity == '':
                            quantity = re.sub(r'[^,0-9]', '', string[len(string)-cost_cond-2-price_cond]).translate(
                                        str.maketrans(',', '.'))
                            quantity = float(quantity)
                    if price_cond:
                        price = float(re.sub(r'[^,0-9]', '', string[len(string)-1-cost_cond])
                                        .translate(str.maketrans(',', '.')))
                    if cost_cond:
                        cost = float(re.sub(r'[^,0-9]', '', string[len(string)-1])
                                     .translate(str.maketrans(',', '.')))
                elif len(string) > 0 and 'Наименованиетовараработыуслуги' == re.sub(r'[^A-Za-zА-Яа-я]', '', string[0]):
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
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]).translate(str.maketrans('"', "»")),
                                       temp2[j] / amount]
                    else:
                        for j in range(len(temp)):
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]).translate(str.maketrans('"', "»")), None]
                    result[ii].append(temp)
                    result[ii].append(total)
                    result[ii].append(link)
                    del temp, temp2, amount
            else:
                for ii in range(len(result)):
                    result[ii].append('NULL')
                    result[ii].append(total)
                    result[ii].append(link)
            log.debug('record loaded')
        elif cond[len(cond) - 1][0:22] == 'medTable':  # для медицины
            del cond
            nodes = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]//table[contains(@class, "orderMedTable")]'
                               '/tbody/tr[not (@*)]')
            head = tree.xpath('//div[contains(@class,"addingTbl col6Tbl")]//tr[@class="tdHead"]/td/text()')
            head = set(map(lambda x: re.sub(r'[^A-Za-zА-Яа-я]', '', x), head))
            result = []
            code, good_name, unit, quantity, price, cost = 'MED', 'NULL', 'NULL', 'NULL', 'NULL', 'NULL'
            if 'Международноенепатентованное' in head:
                good_name_cond = 1
            else:
                good_name_cond = 0
            if 'Сведенияолекарственныхформах' in head:
                unit_cond = 1
            else:
                unit_cond = 0
            if 'Количество' in head:
                quantity_cond = 1
            else:
                quantity_cond = 0
            if 'Ценазаедизм' in head:
                price_cond = 1
            else:
                price_cond = 0
            if 'Стоимость' in head:
                cost_cond = 1
            else:
                cost_cond = 0
            for ii in nodes:
                # если в режиме мед таблицы будет падать по причине смены вёрстки - перепишу
                single_node = lxml.html.fromstring(lxml.etree.tostring(ii, pretty_print=False))
                if 'delimTr' in single_node.xpath('//td/@class'):
                    continue
                string = single_node.xpath('//td/text()')
                if good_name_cond:
                    good_name = re.sub(r'(\n)|(\s\s)', '', string[1])
                if unit_cond:
                    unit = re.sub(r'(\n)|(\s\s)', '', string[4])
                if quantity_cond:
                    quantity = float(re.sub(r'[^,0-9]', '', string[5]).translate(str.maketrans(',', '.')))
                if price_cond:
                    price = float(re.sub(r'[^,0-9]', '', string[6]).translate(str.maketrans(',', '.')))
                if cost_cond:
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
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]).translate(str.maketrans('"', "»")),
                                       temp2[j] / amount]
                    else:
                        for j in range(len(temp)):
                            temp[j] = [re.sub(r'(\n)|(\s\s)', '', temp[j]).translate(str.maketrans('"', "»")), None]
                    result[ii].append(temp)
                    result[ii].append(total)
                    result[ii].append(link)
                    del temp, temp2, amount
            else:
                for ii in range(len(result)):
                    result[ii].append('NULL')
                    result[ii].append(total)
                    result[ii].append(link)
            temp = tree.xpath('//h2[contains(text(),"Сведения о наименовании")]/../div//td/text()')[3::4]
            if len(temp) == len(result):
                for ii in range(len(temp)):
                    result[ii][3] = re.sub(r'(\n)|(\s\s)', '', temp[ii])
            log.debug('medical record loaded')
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
    list_of_tenders = zakupki(1, logger.getChild('get_links'), cache[0], cache[1])
    logger.info('got links')
    conn = sqlite3.connect('collection.db')
    logger.info('db is opened')
    cursor = conn.cursor()
    cursor.execute("select link,ministry,real_price from inp")
    from_db = cursor.fetchall()
    saved = [set(), set()]  # [set of links, set of tuples (ministry + real_price)]
    for i in from_db:
        saved[0].add(i[0])
        saved[1].add((i[1], i[2]))
    logger.debug('data is ' + str(saved))
    command = ''
    logger.info('total link: ' + str(len(list_of_tenders)))
    for i in range(len(list_of_tenders)):
        print(str(i) + '/' + str(len(list_of_tenders)))
        if len(list_of_tenders[i][2]) > 0 and list_of_tenders[i][2][0] not in saved[0]:
            info = []
            try:
                info = more_info(list_of_tenders[i][2], list_of_tenders[i][1], list_of_tenders[i][0],
                                 logger.getChild('more_info'))
            except Exception as e:
                logger.error(e)
            for record in info:
                command = "INSERT into inp values (" + "'" + str(record[0]) + "','" + str(record[1]) + "','" + \
                           str(record[2]) + "','" + str(record[3]) + "','" + str(record[4]) + "'," + str(record[5]) + \
                           ',' + str(record[6]) + ',' + str(record[7]) + ",'" + str(record[8]) + "'," + str(record[9]) \
                           + ',"' + str(record[10]) + '",' + str(record[11]) + ",'" + str(record[12]) + "'); \n"
                logger.debug(command)
                cursor.execute(command)
                logger.info('sent to db')
            del info
        elif (list_of_tenders[i][1], list_of_tenders[i][0]) not in saved[1] and len(list_of_tenders[i][2]) == 0:
            command = "INSERT into inp values (" + "NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,'" + \
                       str(list_of_tenders[i][1]) + "'," + str(list_of_tenders[i][0]) + ", NULL, NULL, NULL); \n"
            logger.debug(command)
            cursor.execute(command)
            logger.info('sent to db')
        else:
            logger.debug('info found in db')
        if i % 10 == 0 and i != 0:
            conn.commit()
            logger.info('commited')

    conn.close()
    logger.info(':-)')
