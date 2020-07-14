import requests
import os
import sys
def check_url(url=""):
    if not url:
        return False
    url = "http://{}".format(url)
    for i in range(3):
        try:
            Check = requests.head(url, timeout=5)
            print os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, "ok, ask for {}, http code: {} ".format(url, Check.status_code)
            return True
        except:
            continue
    return False