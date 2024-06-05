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

    def scrap_murata(self, partNumber):
        try:
            url = 'https://www.murata.com/en-us/products/productdetail?partno=' + partNumber
            response = requests.get(url)
            series_re = re.search(r'Series=(.+?)(,| /)', response.text)
            print("---------hello world------------", response)
            if series_re:
                series = series_re.group(1)
            else:
                series = partNumber

            soup = BeautifulSoup(response.text, 'lxml')
            status_icons = soup.find('ul', class_='detail-status-icon')
            for icon in status_icons.find_all('li'):
                status_img_link = icon.find('img').attrs['src']
                if 'avairable' in status_img_link:
                    status = 'available'
                    break
                elif 'discontinued' in status_img_link:
                    status = 'discontinued'
                    break
                elif 'planneddiscontinue' in status_img_link:
                    status = 'to be discontinued'
                    break
                elif 'nrnd' in status_img_link:
                    status = 'not recommended for new design'
                    break

            def search_doc_link(type_: list, section):
                docs_divs = soup.find_all('div', class_="detail-sidenavi")
                for dd in docs_divs:
                    if dd.find('h2', text=section):
                        for doc_a in dd.find_all('a'):
                            for t in type_:
                                if t in doc_a.text:
                                    doc_link = doc_a.attrs['href']
                                if not doc_link.startswith('http'):
                                    return 'https://murata.com/' + doc_link
                                else:
                                    return doc_link

            dsheet = search_doc_link(
                ['Data Sheet', 'Specifications Sheet'], 'Details')
            rohs_url = search_doc_link(['RoHS'], 'Related Links')
            reach_url = search_doc_link(['REACH'], 'Related Links')

            for pdf_list_url in {rohs_url, reach_url}:
                response_pdflist = requests.get(pdf_list_url)
                soup_pdf = BeautifulSoup(response_pdflist.text, 'lxml')

            rohs, reach = (None, None)

            for table in soup_pdf.find_all('table', class_="m-table_table"):
                links_pdf = []
                for tbody in table.find_all('tbody'):
                    for tr in table.find_all('tr'):
                        tds = tr.find_all('td')
                        if tds:
                            series_pdf = tds[0].text.split()[0].rstrip('*')
                            links_pdf.append(
                                (series_pdf, tds[1].find('a').attrs['href']))
                            links_pdf = sorted(
                                links_pdf, key=lambda x: -len(x[0]))

                for sr_pdf, pdf_link in links_pdf:
                    if sr_pdf in series:
                        if '-rohs-' in tds[1].find('a').attrs['href'] and rohs is None:
                            rohs = 'https://www.murata.com' + pdf_link
                        elif '-reach-' in tds[1].find('a').attrs['href'] and reach is None:
                            reach = 'https://www.murata.com' + pdf_link

            result = {
                'Results': 'Found',
                'status': status,
                'partNumber': partNumber,
                'partName': soup.find('h1').text.strip(),
                'DataSheet': dsheet,
                'RoHS': rohs,
                'REACH': reach
            }

        except Exception as e:
            print('part number is not found on server')
            return {"status": 404}

        return result

    def scrap_festo(self, partnumber):
        # print(partnumber)
        url = "https://www.festo.com/ca/en/search/autocomplete/SearchBoxComponent?term=" + \
            str(partnumber)

        try:
            # request part information from Festo server
            res = requests.request("GET", url)
        except:
            return {"status": 404}

        response = json.loads(res.text)

        results = response['pagination']['totalNumberOfResults']

        # handle the returns depending on how many parts are found
        if results == 0:
            # no parts have been found
            print(f'part number {partnumber} is not found on server')
            return {"status": 404}

        elif results > 1:
            # more than one part has been found, search for exact match
            part = Festo().multiple_results(response, partnumber)
            # make sure error message is correctly handled if no exact match is found
            if part == {"status": 404}:
                return part

        elif results == 1:
            # exactly one part has been found
            part = response['products'][0]

        # search if part is on SVHC / Exemption list
        dsl_found = Festo().substances.loc[Festo(
        ).substances['Identifier'] == str(part['code'])]

        # extract the wanted part information
        result = {

            # search result
            'Results': 'found',

            # Festo Part Number
            'FestoPartNumber': part['code'],

            # Festo Part Name
            'FestoPartName': part['name'],

            # Festo Order Code
            "FestoOrderCode": part['orderCode'],

            # Part link
            "PartURL": f"https://www.festo.com/ca/en{str(part['url'])}",

            # ROHS information
            'ROHS exemption': " / ".join(str(v) for v in dsl_found['ROHS Exemption:']),

            # SVHC substance
            'SVHC contained:': " / ".join(str(v) for v in dsl_found['SVHC contained:']),

            # SVHC CAS
            'SVHC CAS number': " / ".join(str(v) for v in dsl_found['CAS:']),

            # SCIP number
            'SCIP number': " / ".join(str(v) for v in dsl_found['SCIP number']),

            # Article name
            'Article name': " / ".join(str(v) for v in dsl_found['Article name']),

            # Last updated
            'Last updated': " / ".join(str(v) for v in dsl_found['Last Updated'])
        }

        return result

    def scrap_onsemi(self, partnumber):
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36'
        }
        try:
            response = requests.get(
                "https://www.onsemi.com/PowerSolutions/MaterialComposition.do?searchParts=" + urllib.parse.quote(str(partnumber), safe=''), headers=headers)
            data = BeautifulSoup(response.text, 'lxml')
            table = data.find(id="MaterialCompositionTable")
            pn = table.tbody.tr.td.find_next('td').text
            status = table.tbody.tr.td.find_next('td').find_next('td').text
            hf = table.tbody.tr.td.find_next(
                'td').find_next('td').find_next('td').text
            excempt = table.tbody.tr.td.find_next('td').find_next(
                'td').find_next('td').find_next('td').text
            links = table.find_all('a', href=True)
            declaration = "https://www.onsemi.com" + links[5]['href']
            lead = "not found"
            if len(excempt) > 1:
                lead = table.tbody.tr.td.find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next(
                    'td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').find_next('td').text

            return {"Results": "Found", "SPN_grabbed": pn, "Status": status, "HF": hf, "Excemption": excempt, "Declaration": declaration, "Lead(Cas No:7439-92-1)": lead}

        except Exception as e:
            return {"status": 404}

    def scrap_Maxim(self, partnumber):
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36'
        }
        # part = re.sub.replace(":", "/", partnumber)
        # print(part)
        url = requests.get(
            "https://www.maximintegrated.com/en/qa-reliability/emmi/content-lookup/product-content-info.html?partNumber=" + urllib.parse.quote(str(partnumber)), headers=headers)
        soup = BeautifulSoup(url.text, 'lxml')
        try:
            table = soup.find(id="productcontentinfo")
            Rohs_Compliance = table.tbody.tr.td.find_next('td').text
            Rohs2_compliance = table.tbody.tr.td.find_next(
                'tr').td.find_next('td').text
            Halogen_compliance = table.tbody.tr.find_next(
                'tr').find_next('tr').td.find_next('td').text
            Reach_Compliance = table.tbody.tr.find_next('tr').find_next(
                'tr').find_next('tr').td.find_next('td').text
            print(Rohs_Compliance, Rohs2_compliance,
                  Halogen_compliance, Reach_Compliance)
            return {"Results": "Found", "Partnumber": part, "Rohs_Compliance": Rohs_Compliance, "Rohs2_compliance": Rohs2_compliance, "Halogen_compliance": Halogen_compliance, "Reach_Compliance": Reach_Compliance}
        except Exception as e:
            print(e)
            return {"status": 404}

    def scrap_Molex(self, partnumber):
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36'
        }
        url = "https://www.molex.com/molex/search/partSearch?query=" + \
            urllib.parse.quote(str(partnumber), safe="") + "&pQuery="
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')
        try:
            partname = soup.find(
                "div", class_="col-md-10").find("h1").text
            status = soup.find("p", class_="info").find(
                "span", class_="green").text
            series = soup.find("a", class_='text-link').text
            rohs = soup.find(
                "div", id="tab-environmental").find_all("p")[1].text
            reach = soup.find(
                "div", id="tab-environmental").find_all("p")[3].text
            halogen = soup.find(
                "div", id="tab-environmental").find_all("p")[4].text
            link = soup.find(
                "div", id="tab-environmental").find_all("p")[8].find("a", href=True)
            declaration = link['href']
            return {"Results": "Found", "PArtname": partname, "Status": status, "Series": series, "ROHS": rohs, "REACH": reach, "HALOGEN": halogen, "Declaration": declaration}
        except Exception as e:

            return {"status": 404}

    def scrap_Phoenix(self, partnumber):
        try:
            url = "https://www.phoenixcontact.com/customer/api/v1/product-compliance/products?_locale=en-CA&_realm=ca&offset=0&requestedSize=11"
            reporturl = "https://www.phoenixcontact.com/customer/api/v1/product-compliance/report/guid?_locale=en-CA&_realm=ca"

            # payload = "{\"searchItems\":[\"1084745\"]}"
            payload = '{\"searchItems\":[\"' + \
                urllib.parse.quote(str(partnumber)) + '\"]}'
            headers = {
                'authority': 'www.phoenixcontact.com',
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'en-US,en;q=0.9,de;q=0.8',
                'cache-control': 'no-cache',
                'content-type': 'application/json;charset=UTF-8',
                'origin': 'https://www.phoenixcontact.com',
                'pragma': 'no-cache',
                'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36', }
            response = requests.request(
                "POST", url, headers=headers, data=payload)
            report_response = requests.request(
                "POST", reporturl, headers=headers, data=payload)
            link = "https://www.phoenixcontact.com/customer/api/v1/product-compliance/report/guid/" + \
                report_response.text + "?_locale=en-US&_realm=us"

            res = response.json()

            for results in res['items'].values():

                if results["validItem"] == False:
                    return {"status": 404}
                else:
                    return results
        except Exception as e:
            print(e)
            return {status: 404}

    def scrap_Rscomponents(self, partnumber):
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36'
        }
        try:
            url = "https://export.rsdelivers.com/productlist/search?query=" + \
                urllib.parse.quote(str(partnumber))

            r = requests.get(url, headers=headers)
            data = BeautifulSoup(r.text, 'lxml')
            partName = data.find(
                "h1", class_='product-detail-page-component_title__HAXxV').text

            manufacturerName = data.find("div", class_='pill-component-module_grey__38ctb').find_next(
                "div", class_='pill-component-module_grey__38ctb').text

            mpn = data.find("div", class_='pill-component-module_grey__38ctb').find_next(
                "div", class_='pill-component-module_grey__38ctb').find_next("div", class_='pill-component-module_grey__38ctb').text

            return {"Results": "Found", "Partnumber": partnumber, "mpn": mpn, "partName": partName, "manufacturerName": manufacturerName}
        except Exception as e:
            print(e)
            return {"status": 404}

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
