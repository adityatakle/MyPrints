import platform
import requests
import time
import os
import subprocess
import win32print

shop_id=1
url = f'https://5cqwb04t-8000.inc1.devtunnels.ms/my_shop/script_connect/{shop_id}'
requests.post(url, headers={'Shop-token':Shop_token, 'os':os.name})

