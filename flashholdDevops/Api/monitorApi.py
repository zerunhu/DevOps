from django.conf import settings
import os
import requests
import json

class MonitorApi(object):
    def __init__(self):
        self.api_url = settings.PROMETHEUS_URL

    def get_global_memory(self):
        data = {"query":"1-sum(:node_memory_MemFreeCachedBuffers_bytes:sum{}) / sum(:node_memory_MemTotal_bytes:sum{})"}
        url = os.path.join(self.api_url,"api/v1/query")
        res = requests.post(url,data=data)
        data = json.loads(res.text)
        return data["data"]["result"][0]["value"][1]

    def get_namespace_memory(self):
        rsn = {}
        # data = {"query":"sum(container_memory_rss{container_name!=''}) by (namespace)"}
        data = {"query":"sum(container_memory_rss{container_name!=''}) by (namespace)"}
        # url = os.path.join(self.api_url,"api/v1/query")
        url = "{}/{}".format(self.api_url, "api/v1/query")
        try:
            res = requests.post(url,data=data)
            data = json.loads(res.text)
            datas = data["data"]["result"]
            for data in datas:
                rsn[data["metric"]["namespace"]] = data["value"][1]
        except:
            rsn=None
        return rsn

    def get_pods_memory(self,namespace=""):
        rsn = {}
        if namespace:
            data = {"query":"sum(container_memory_rss{{container_name!='',namespace='{}'}}) by (pod_name)"
                .format(namespace)}
        else:
            data = {"query": "sum(container_memory_rss{container_name!=''}) by (pod_name)"}
        url = os.path.join(self.api_url,"api/v1/query")
        res = requests.post(url,data=data)
        data = json.loads(res.text)
        datas = data["data"]["result"]
        for data in datas:
            rsn[data["metric"]["pod_name"]] = data["value"][1]
        return rsn

    def get_global_cpu(self):
        data = {"query":"1 - avg(rate(node_cpu_seconds_total{mode='idle'}[1m]))"}
        url = os.path.join(self.api_url,"api/v1/query")
        res = requests.post(url,data=data)
        data = json.loads(res.text)
        return data["data"]["result"][0]["value"][1]

    def get_namespace_cpu(self):
        rsn = {}
        data = {"query":"sum(rate(container_cpu_usage_seconds_total{}[5m]))by (namespace)"}
        url = "{}/{}".format(self.api_url,"api/v1/query")
        try:
            res = requests.post(url,data=data)
            data = json.loads(res.text)
            datas = data["data"]["result"]
            for data in datas:
                try:
                    rsn[data["metric"]["namespace"]]=data["value"][1]
                except:
                    continue
        except:
            rsn=None
        return rsn

    def get_pods_cpu(self,namespace):
        rsn = {}
        if namespace:
            data = {"query":"sum(rate(container_cpu_usage_seconds_total"
                            "{{namespace='{}'}}[5m]))by (pod_name)".format(namespace)}
        else:
            data = {"query":"sum(namespace_pod_name_container_name:container_cpu_usage_seconds_total"
                            ":sum_rate{}) by (pod_name)"}
        url = "{}/{}".format(self.api_url,"api/v1/query")
        res = requests.post(url,data=data)
        data = json.loads(res.text)
        datas = data["data"]["result"]
        for data in datas:
            rsn[data["metric"]["pod_name"]]=data["value"][1]
        print rsn
        return rsn


if __name__ == "__main__":
    l = MonitorApi()
    l.get_pods_cpu()
