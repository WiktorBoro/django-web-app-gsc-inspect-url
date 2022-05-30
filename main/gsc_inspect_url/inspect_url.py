import httplib2
from ..models import CredentialsModel

import gspread
from googleapiclient.discovery import build
from celery import shared_task
from re import match


@shared_task(bind=True)
def start_inspect(token, sheets_url):
    GscIndexInspect(token=token, sheets_url=sheets_url)


class GscIndexInspect:
    def __init__(self, sheets_url, token):
        self.token = token
        self.sheets_token = match('https:\/\/docs.google.com\/spreadsheets\/d\/([^\/]+)', sheets_url).groups()[0]
        self.authorization_gsc()
        self.authorization_sheets()
        self.get_url_from_sheets_and_save_to_sheets()

    def authorization_sheets(self):
        credentials = CredentialsModel.objects.get(token='googlesheetscredNcQfTjWnZr4u7x')

        gc = gspread.service_account_from_dict(credentials_sheets)

        self.sh = gc.open_by_key(self.sheets_token)
        rows = self.sh.sheet1

        self.colA = rows.col_values(1)

    def authorization_gsc(self):
        credentials = CredentialsModel.objects.get(token=self.token)
        http = httplib2.Http()
        http = credentials.authorize(http)

        self.webmasters_service = build('searchconsole', 'v1', http=http)

    def index_inspect(self, url, site):
        request = {
              "inspectionUrl": url,
              "siteUrl": site,
              "languageCode": "en-US"
        }
        response = self.webmasters_service.urlInspection().index().inspect(body=request).execute()
        return response

    def get_url_from_sheets_and_save_to_sheets(self):
        row_num = 0

        for url in self.colA:
            if match('^http.*', url):
                domain = match(r'(https?:\/\/[^\/]+\/)', url)
                response = self.index_inspect(url, domain.groups()[0])
                coverage_state = response['inspectionResult']['indexStatusResult']['coverageState']
                indexing_state = response['inspectionResult']['indexStatusResult']['indexingState']
                try:
                    mobile_usability_result = str(response['inspectionResult']['mobileUsabilityResult'])
                except KeyError:
                    mobile_usability_result = ""

                self.sh.update_cell(row_num, 2, coverage_state)
                self.sh.update_cell(row_num, 3, indexing_state)
                self.sh.update_cell(row_num, 4, mobile_usability_result)
                row_num += 1
        CredentialsModel.objects.filter(token=self.token).delete()