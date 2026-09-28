import requests

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://www.niftyindices.com/reports/historical-data',
    'X-Requested-With': 'XMLHttpRequest'
})

r1 = s.get('https://www.niftyindices.com/reports/historical-data')
print("Initial GET status:", r1.status_code)

payload = {"cinfo": "{'name':'NIFTY 50','startDate':'01-Jan-2020','endDate':'10-Jan-2020','indexName':'NIFTY 50'}"}

r2 = s.post('https://www.niftyindices.com/Backpage.aspx/getHistoricaldatatabletoString', json=payload)
print("POST status:", r2.status_code)
print("POST text:", r2.text[:200])
