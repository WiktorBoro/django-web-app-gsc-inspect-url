import httplib2
from ..models import CredentialsModel

import gspread
from googleapiclient.discovery import build
from celery import shared_task
from re import match
from json import loads

from google.oauth2 import credentials


@shared_task(bind=True)
def start_inspect(self, token, sheets_url):
    GscIndexInspect(token=token, sheets_url=sheets_url)


class GscIndexInspect:
    def __init__(self, sheets_url, token):
        self.token = token
        self.sheets_token = match('https:\/\/docs.google.com\/spreadsheets\/d\/([^\/]+)\/.*', sheets_url).groups()[0]
        self.authorization_gsc()
        self.authorization_sheets()
        self.get_url_from_sheets_and_save_to_sheets()

    def authorization_sheets(self):
        credentials_sheets = sheets_cred

        gc = gspread.service_account_from_dict(credentials_sheets)

        self.sh = gc.open_by_key(self.sheets_token)
        self.rows = self.sh.sheet1

        self.colA = self.rows.col_values(1)

    def authorization_gsc(self):
        credentials_dict = loads(CredentialsModel.objects.get(token=self.token).credential)

        credentials_ = credentials.Credentials(
            credentials_dict['token'],
            refresh_token=credentials_dict['refresh_token'],
            id_token=credentials_dict['id_token'],
            token_uri=credentials_dict['token_uri'],
            client_id=credentials_dict['client_id'],
            client_secret=credentials_dict['client_secret'],
            scopes=[credentials_dict['scopes']],
        )

        self.webmasters_service = build('searchconsole', 'v1', credentials=credentials_)

    def index_inspect(self, url, site):
        request = {
              "inspectionUrl": url,
              "siteUrl": site,
              "languageCode": "en-US"
        }
        response = self.webmasters_service.urlInspection().index().inspect(body=request).execute()
        return response

    def get_url_from_sheets_and_save_to_sheets(self):
        row_num = 1
        self.rows.update_cell(row_num, 1, "URL")
        self.rows.update_cell(row_num, 2, "Coverage state")
        self.rows.update_cell(row_num, 3, "Indexing state")
        self.rows.update_cell(row_num, 4, "Last crawl time")
        self.rows.update_cell(row_num, 5, "Page fetch state")
        self.rows.update_cell(row_num, 6, "Google canonical")
        self.rows.update_cell(row_num, 7, "User canonical")
        self.rows.update_cell(row_num, 8, "Crawled as")
        self.rows.update_cell(row_num, 9, "Detected micro data")
        self.rows.update_cell(row_num, 10, "Mobile usability result")

        row_num = 2
        for url in self.colA:
            if match('^http.*', url):
                try:
                    domain = match(r'(https?:\/\/[^\/]+\/)', url)
                    response = self.index_inspect(url, domain.groups()[0])
                except:
                    response = {'inspectionResult':
                                    {'indexStatusResult': {'coverageState': 'ERROR', 'indexingState': 'ERROR'}}}
                try:
                    coverage_state = response['inspectionResult']['indexStatusResult']['coverageState']
                except KeyError:
                    coverage_state = "No data"
                try:
                    indexing_state = response['inspectionResult']['indexStatusResult']['indexingState']
                except KeyError:
                    indexing_state = "No data"
                try:
                    last_crawl_time = response['inspectionResult']['indexStatusResult']['lastCrawlTime']
                except KeyError:
                    last_crawl_time = "No data"
                try:
                    page_fetch_state = response['inspectionResult']['indexStatusResult']['pageFetchState']
                except KeyError:
                    page_fetch_state = "No data"
                try:
                    google_canonical = response['inspectionResult']['indexStatusResult']['googleCanonical']
                except KeyError:
                    google_canonical = "No data"
                try:
                    user_canonical = response['inspectionResult']['indexStatusResult']['userCanonical']
                except KeyError:
                    user_canonical = "No data"
                try:
                    crawled_as = response['inspectionResult']['indexStatusResult']['crawledAs'] + ' bot'
                except KeyError:
                    crawled_as = "No data"
                try:
                    detected_micro_data = ''
                    for i in response['inspectionResult']['richResultsResult']['detectedItems']:
                        detected_micro_data += str(i)+'\n'
                except KeyError:
                    detected_micro_data = "No data"

                try:
                    mobile_usability_result = str(response['inspectionResult']['mobileUsabilityResult'])
                except KeyError:
                    mobile_usability_result = "No data"

                self.rows.update_cell(row_num, 2, coverage_state)
                self.rows.update_cell(row_num, 3, indexing_state)
                self.rows.update_cell(row_num, 4, last_crawl_time)
                self.rows.update_cell(row_num, 5, page_fetch_state)
                self.rows.update_cell(row_num, 6, google_canonical)
                self.rows.update_cell(row_num, 7, user_canonical)
                self.rows.update_cell(row_num, 8, crawled_as)
                self.rows.update_cell(row_num, 9, detected_micro_data)
                self.rows.update_cell(row_num, 10, mobile_usability_result)
                row_num += 1
        CredentialsModel.objects.filter(token=self.token).delete()