import requests
from bs4 import BeautifulSoup
import urllib
from sites.mouser import Mouser
import re
import json
from sites.Festo import Festo


class Scrapper(Mouser):
    def scrap_newark(self, partNumber):
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        }
        try:
            url = 'https://www.newark.com/webapp/wcs/stores/servlet/AjaxSearchLookAhead?storeId=10194&catalogId=15003&langId=-1&searchTerm='
            response = requests.get(url + str(partNumber), headers=headers)

            soup = BeautifulSoup(response.text, 'lxml')
            table = soup.find('table', class_="searchBoxResultTable")
            tr = table.find_all('tr')[0]
            url_prod = tr.find('td', class_="leftcolumn").find(
                'a', id="searchResultProductList").attrs['href']

            response_prod = requests.get(url_prod, headers=headers)
            soup_prod = BeautifulSoup(response_prod.text, 'lxml')

            partNumber = re.findall(r'\bsku: "(.+?)"', response_prod.text)
            partName = re.findall(r"\bd: '(.+?)'", response_prod.text)
            brand = re.findall(r'\bm: "(.+?)"', response_prod.text)
            ds = soup_prod.find(
                'a', {'data-dtm-eventinfo': "Technical Data Sheet"})
            st = soup_prod.find('span', class_="availTxtMsg").text or ''

            rohs_table = soup_prod.find(
                'table', class_='details-table-desktop')
            for tr in rohs_table.find_all('tr'):
                if 'RoHS Compliant' in tr.find('th').text:
                    rohs_stat = tr.find(
                        'td', class_="rohsDescription").contents[0] or ''
                    break

            result = {
                'Results': 'Found',
                'status': re.sub(r'\d', '', st).strip() or None,
                'partNumber': partNumber[0] if partNumber else None,
                'partName': partName[0] if partName else None,
                'dataSheet': ds.attrs['href'] if ds else None,
                'brand': brand[0] if brand else None,
                'RoHSCompliantStatus': rohs_stat.strip()
            }
        except Exception as e:
            print('part number is not found on server')
            return {"status": 404}

        return result

    def scrap_3m(self, productNumber):
        print('hello world', productNumber)
        url = 'https://www.3m.com/3M/en_US/p/?Ntt=' + str(productNumber)
        response = requests.get(url,
                                headers={'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'})
        matches = re.search(
            r'window.__INITIAL_DATA = ({.+})', response.text).group(1)
        matches_list = json.loads(matches)['items']
        try:
            headers = {
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'en-US,en;q=0.9,uk-UA;q=0.8,uk;q=0.7,ru;q=0.6',
                'cache-control': 'max-age=0',
                'connection': 'keep-alive',
                'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            }
            prod_url = matches_list[0].get('url')
            response_page = requests.get(prod_url, headers=headers)

            safety_sheets = []
            soup = BeautifulSoup(response_page.text, 'lxml')
            tab_divs = soup.find_all('div', class_='MMM--dataGroup-hd')
            for div in tab_divs:
                if div.find('div', text='Safety Data Sheets'):
                    safety_links = div.find_all('a')
                    for a in safety_links:
                        safety_sheets.append(a.attrs['href'])

            disc_notice = soup.find('div', text="Discontinuation Notices")
            if disc_notice:
                status = 'discontinued'
            else:
                status = 'active'

            re_stock_no = re.search(
                r'<em>(.+?)</em>', matches_list[0].get('stockNumber'))
            if re_stock_no:
                stock_no = re_stock_no.group(1)
            else:
                stock_no = productNumber

            result = {
                'Results': 'Found',
                'status': status,
                'productNumber': stock_no,
                'partName': soup.find('h1').text,
                'safetyDataSheetURL': safety_sheets

            }
        except Exception as e:
            print('part number is not found on server')
            return {"status": 404}

        return result

    def scrap_ti(self, partnumber):
        print(partnumber)
        url = 'https://www.ti.com/product/' + str(partnumber)
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')
        datasheet = soup.find('a', navtitle="data sheet") or ''
        try:
            result = {
                'Results': 'Found',
                'status': soup.find('ti-product-status').find('a').text,
                'Partnumber': soup.find('ti-main-panel').attrs["gpn"],
                'partName': soup.find('h2').text,
                'CertificateDeclaration': None,
                'DataSheetURL': ('https://www.ti.com' + datasheet.attrs["href"]) if datasheet else None
            }
        except Exception as e:
            print('part number is not found on server')
            return {"status": 404}

        return result

    def find_Supplier(self, partnumber):

        def Check_Response(supplier, response, foundlist):
            try:
                if response["Results"] == "Found":
                    foundlist.append(supplier)
            except Exception as e:
                pass

        suppliers = []

        # Checking the response of the scraped data from the two websites.
        response = self.scrap_festo(partnumber)
        Check_Response("festo", response, suppliers)

        response = self.scrap_Arrow(partnumber)
        Check_Response("arrow", response, suppliers)

        response = self.scrap_omron(partnumber)
        Check_Response("omron", response, suppliers)

        response = self.scrap_Rscomponents(partnumber)
        Check_Response("RS-components", response, suppliers)

        response = self.scrap_Maxim(partnumber)
        Check_Response("maxim", response, suppliers)

        response = self.scrap_Molex(partnumber)
        Check_Response("molex", response, suppliers)

        response = self.scrap_Wago(partnumber)
        Check_Response("wago", response, suppliers)

        response = self.scrap_Te(partnumber)
        Check_Response("Te", response, suppliers)

        response = self.scrap_Phoenix(partnumber)
        Check_Response("phoenix", response, suppliers)

        response = self.scrap_onsemi(partnumber)
        Check_Response("onsemi", response, suppliers)

        response = self.scrap_mouser(partnumber)
        Check_Response("mouser", response, suppliers)

        response = self.scrap_3m(partnumber)
        Check_Response("scrap_3m", response, suppliers)

        response = self.scrap_ti(partnumber)
        Check_Response("scrap_ti", response, suppliers)

        response = self.scrap_murata(partnumber)
        Check_Response("scrap_murata", response, suppliers)

        response = self.scrap_newark(partnumber)
        Check_Response("scrap_newark", response, suppliers)

        response = self.scrap_festo(partnumber)
        Check_Response("scrap_festo", response, suppliers)

        return suppliers



if __name__ == '__main__':
    scraper = Scrapper()
    print(scraper.scrap_festo("8046265"))
