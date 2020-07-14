#coding=utf-8
import dns.query
import dns.tsigkeyring
import dns.update
from django.conf import settings
import sys


class DnsApi(object):
    def __init__(self):
        self.keyring = dns.tsigkeyring.from_text({
        'rndc-key': 'orvLyDHg6euVz89htLeRMQ=='
    })

    def update(self,domain="", hostIP=""):
        if domain == "":
            return False

        update = dns.update.Update('flashhold.com', keyring=self.keyring)
        if hostIP:
            update.replace(domain, 300, 'A', hostIP)
        else:
            update.replace(domain, 300, 'A', settings.DNS_HOST)

        response = dns.query.tcp(update, settings.DNS_HOST)
        print response

    def delete(self,domain=""):
        if domain == "":
            return False

        update = dns.update.Update('flashhold.com', keyring=self.keyring)
        update.delete(domain, 'A')
        response = dns.query.tcp(update, settings.DNS_HOST)
        print response

# if __name__ == "__main__":
#     l = DnsApi()
    # l.update(domain="deploy-1572415190")
