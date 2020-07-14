# coding=utf-8
# https://raw.githubusercontent.com/kubernetes-client/python/master/kubernetes/client/apis/core_v1_api.py

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from django.conf import settings
import os
import sys
import datetime
from time import strptime,strftime,mktime
import time
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class K8sApi(object):

    def __init__(self):
        self.token = settings.KUBERNETES_TOKEN
        self.host = settings.KUBERNETES_HOST
        configuration = client.Configuration()
        configuration.host = self.host
        configuration.verify_ssl = False
        configuration.api_key = {"authorization": "Bearer " + self.token}
        client.Configuration.set_default(configuration)

    def make_string(self, request):
        for key, value in request.items():
            request[key] = str(value)
        return request

    def list_nodes(self):
        v1 = client.CoreV1Api()
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args=v1.list_node())

    def create_namespace(self, namespace, user="", group=""):
        api_instance = client.CoreV1Api()
        body = client.V1Namespace()
        if user and group:
            body.metadata = client.V1ObjectMeta(name=namespace,labels={"user": user,"group": group,"platform": "devops"})
        else:
            body.metadata = client.V1ObjectMeta(name=namespace)
        try:
            api_response = api_instance.create_namespace(body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->create_namespace: %s\n" % e)

    def delete_namespace(self, namespace):
        api_instance = client.CoreV1Api()
        body = client.V1DeleteOptions()
        try:
            api_response = api_instance.delete_namespace(namespace, grace_period_seconds=0)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)
        except ApiException as e:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, "Exception when calling CoreV1Api->delete_namespace: %s\n" % e)

    def delete_pod(self, name="", namespace=""):
        api_instance = client.CoreV1Api()
        pretty = True  # str | If 'true', then the output is pretty printed. (optional)
        body = client.V1DeleteOptions()  # V1DeleteOptions |  (optional)
        grace_period_seconds = 56
        try:
            api_response = api_instance.delete_namespaced_pod(name, namespace, pretty=pretty, body=body,
                                                              grace_period_seconds=grace_period_seconds)
            return {"rsn":0,"msg":api_response}
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)


        except ApiException as e:
            return {"rsn": 1,"msg":e}
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->delete_namespaced_pod: %s\n" % e)

    def replace_configreplace_config_map_map(self, body=None, name="tcp-services", namespace="ingress-nginx"):
        api_instance = client.CoreV1Api()
        body = client.V1ConfigMap(data=body)
        meta_name = client.V1ObjectMeta(name=name)
        body.metadata = meta_name
        try:
            api_response = api_instance.replace_namespaced_config_map(name, namespace, body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->replace_config_map: %s\n" % e)

    def get_last_pod_log(self, namespace="", name="",pod_name="" ):
        api_instance = client.CoreV1Api()
        pretty = True
        try:
            obj = api_instance.read_namespaced_pod_log(pod_name, namespace, pretty=pretty, tail_lines=5000,previous=True,container=name)
            return obj
        except ApiException as e:

            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling ExtensionsV1beta1Api->read_namespaced_pod_log: %s\n" % e)


    def get_pod_laststatus(self, namespace="", name=""):
        api_instance = client.CoreV1Api()
        label_selector = 'app.kubernetes.io/name=%s' % (
            name,)  # str | A selector to restrict the list of returned objects by their labels. Defaults to everything. (optional)
        timeout_seconds = 56  # int | Timeout for the list/watch call. This limits the duration of the call, regardless of any activity or inactivity. (optional)

        try:
            obj = api_instance.list_namespaced_pod(namespace,
                                                   label_selector=label_selector,
                                                   timeout_seconds=timeout_seconds)
            if obj:
                for item in obj.items:
                    if item.status.reason != "Evicted":
                        # return item.metadata.name
                        try:
                            laststatus = item.status.container_statuses[0].last_state.terminated
                        except:
                            laststatus = None
                        data = {}
                        if laststatus:
                            xtime = laststatus.finished_at
                            t= strptime(str(xtime).split("+")[0],'%Y-%m-%d %H:%M:%S')
                            tlist = list(t)
                            tlist[3]+=8
                            if tlist[3] >= 24:
                                tlist[3]-=24
                                tlist[2]+=1
                            time = strftime('%Y-%m-%d %H:%M:%S', tuple(tlist))
                            data["pod_name"] = item.metadata.name
                            data["exit_code"] = laststatus.exit_code
                            data["message"] = laststatus.message
                            data["reason"] = laststatus.reason
                            data["signal"] = laststatus.signal
                            data["stop_time"] = time
                        return dict(data)
        except ApiException as e:
            print("Exception when calling CoreV1Api->list_namespaced_pod: %s\n" % e)

    def get_pod_name(self,namespace="", name=""):
        api_instance = client.CoreV1Api()
        label_selector = 'app.kubernetes.io/name=%s' % (name,)
        timeout_seconds = 56
        try:
            obj = api_instance.list_namespaced_pod(namespace,label_selector=label_selector,
                                                   timeout_seconds=timeout_seconds)
            if obj:
                for item in obj.items:
                    if item.status.reason != "Evicted":
                        return item.metadata.name
        except ApiException as e:
            print("Exception when calling CoreV1Api->list_namespaced_pod: {}".format(e))



    def create_ingress(self, data=None, namespace=""):
        api_instance = client.ExtensionsV1beta1Api()
        body = client.V1beta1Ingress()
        body.metadata = client.V1ObjectMeta(name=data["name"], annotations={"kubernetes.io/ingress.class": "nginx"})

        backend = client.V1beta1IngressBackend(service_name=data["service_name"], service_port=data["service_port"])
        path = client.V1beta1HTTPIngressPath(path="/", backend=backend)
        rule_value = client.V1beta1HTTPIngressRuleValue(paths=[path])
        rule = client.V1beta1IngressRule(host=data['domain'], http=rule_value)
        spec = client.V1beta1IngressSpec(rules=[rule])
        body.spec = spec

        try:
            api_response = api_instance.create_namespaced_ingress(namespace, body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->create_namespaced_ingress: %s\n" % e)

    def create_canary_ingress(self, data=None, namespace="", weight=""):
        api_instance = client.ExtensionsV1beta1Api()
        body = client.V1beta1Ingress()
        body.metadata = client.V1ObjectMeta(
            name="canary-%s" % data["name"],
            annotations={
                "kubernetes.io/ingress.class": "nginx",
                "nginx.ingress.kubernetes.io/canary": "true",
                "nginx.ingress.kubernetes.io/canary-weight": weight
            }
        )

        backend = client.V1beta1IngressBackend(service_name=data["service_name"], service_port=data["service_port"])
        path = client.V1beta1HTTPIngressPath(path="/", backend=backend)
        rule_value = client.V1beta1HTTPIngressRuleValue(paths=[path])
        rule = client.V1beta1IngressRule(host=data['domain'], http=rule_value)
        spec = client.V1beta1IngressSpec(rules=[rule])
        body.spec = spec

        try:
            api_response = api_instance.create_namespaced_ingress(namespace, body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->create_namespaced_ingress: %s\n" % e)

    def create_ab_ingress(self, data=None, namespace="", header=""):
        api_instance = client.ExtensionsV1beta1Api()
        body = client.V1beta1Ingress()
        body.metadata = client.V1ObjectMeta(
            name="ab-%s" % data["name"],
            annotations={
                "kubernetes.io/ingress.class": "nginx",
                "nginx.ingress.kubernetes.io/canary": "true",
                "nginx.ingress.kubernetes.io/canary-by-header": "version",
                "nginx.ingress.kubernetes.io/canary-by-header-value": header,
            }
        )

        backend = client.V1beta1IngressBackend(service_name=data["service_name"], service_port=data["service_port"])
        path = client.V1beta1HTTPIngressPath(path="/", backend=backend)
        rule_value = client.V1beta1HTTPIngressRuleValue(paths=[path])
        rule = client.V1beta1IngressRule(host=data['domain'], http=rule_value)
        spec = client.V1beta1IngressSpec(rules=[rule])
        body.spec = spec

        try:
            api_response = api_instance.create_namespaced_ingress(namespace, body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->create_ab_ingress: %s\n" % e)

    def patch_canary_ingress(self, data=None, namespace="", weight=""):
        api_instance = client.ExtensionsV1beta1Api()
        body = client.V1beta1Ingress()
        name = "canary-%s" % data["name"]
        body.metadata = client.V1ObjectMeta(
            name=name,
            annotations={
                "kubernetes.io/ingress.class": "nginx",
                "nginx.ingress.kubernetes.io/canary": "true",
                "nginx.ingress.kubernetes.io/canary-weight": weight
            }
        )

        backend = client.V1beta1IngressBackend(service_name=data["service_name"], service_port=data["service_port"])
        path = client.V1beta1HTTPIngressPath(path="/", backend=backend)
        rule_value = client.V1beta1HTTPIngressRuleValue(paths=[path])
        rule = client.V1beta1IngressRule(host=data['domain'], http=rule_value)
        spec = client.V1beta1IngressSpec(rules=[rule])
        body.spec = spec

        try:
            api_response = api_instance.patch_namespaced_ingress(name, namespace, body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->patch_namespaced_ingress: %s\n" % e)

    def patch_service(self, namespace="", name=""):
        v1 = client.CoreV1Api()

        body = {
            "spec": {
                "type": "NodePort"
            }
        }

        portList = []
        try:
            api_response = v1.patch_namespaced_service(namespace=namespace, name=name, body=body)
            for ports in api_response.spec.ports:
                portList.append("{}:{}".format(ports.port, ports.node_port))

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->patch_namespaces_service: %s\n" % e)

        return portList

    def patch_ab_ingress(self, data=None, namespace="", header=""):
        api_instance = client.ExtensionsV1beta1Api()
        body = client.V1beta1Ingress()
        name = "ab-%s" % data["name"]
        body.metadata = client.V1ObjectMeta(
            name=name,
            annotations={
                "kubernetes.io/ingress.class": "nginx",
                "nginx.ingress.kubernetes.io/canary": "true",
                "nginx.ingress.kubernetes.io/canary-by-header": "version",
                "nginx.ingress.kubernetes.io/canary-by-header-value": header,
            }
        )

        backend = client.V1beta1IngressBackend(service_name=data["service_name"], service_port=data["service_port"])
        path = client.V1beta1HTTPIngressPath(path="/", backend=backend)
        rule_value = client.V1beta1HTTPIngressRuleValue(paths=[path])
        rule = client.V1beta1IngressRule(host=data['domain'], http=rule_value)
        spec = client.V1beta1IngressSpec(rules=[rule])
        body.spec = spec

        try:
            api_response = api_instance.patch_namespaced_ingress(name, namespace, body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->patch_ab_ingress: %s\n" % e)

    def delete_ingress(self, name="", namespace=""):
        api_instance = client.ExtensionsV1beta1Api()
        body = client.V1DeleteOptions()
        try:
            api_response = api_instance.delete_namespaced_ingress(name, namespace, body=body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->delete_namespaced_ingress: %s\n" % e)

    def delete_canary_ingress(self, name="", namespace=""):
        api_instance = client.ExtensionsV1beta1Api()
        body = client.V1DeleteOptions()
        try:
            name = "canary-%s" % name
            api_response = api_instance.delete_namespaced_ingress(name, namespace, body=body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling ExtensionsV1beta1Api->delete_namespaced_ingress: %s\n" % e)

    def delete_ab_ingress(self, name="", namespace=""):
        api_instance = client.ExtensionsV1beta1Api()
        body = client.V1DeleteOptions()
        try:
            name = "ab-%s" % name
            api_response = api_instance.delete_namespaced_ingress(name, namespace, body=body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response)
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling ExtensionsV1beta1Api->delete_namespaced_ingress: %s\n" % e)

    def get_namespace_status(self, name):
        api_instance = client.CoreV1Api()
        try:
            obj = api_instance.read_namespace(name)
            return obj.status.phase
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling ExtensionsV1beta1Api->read_namespace: %s\n" % e)

            return False

    def get_pod_info(self, namespace="", name=""):
        api_instance = client.CoreV1Api()
        label_selector = 'app.kubernetes.io/name=%s' % (
            name,)  # str | A selector to restrict the list of returned objects by their labels. Defaults to everything. (optional)
        timeout_seconds = 56  # int | Timeout for the list/watch call. This limits the duration of the call, regardless of any activity or inactivity. (optional)

        try:
            obj = api_instance.list_namespaced_pod(namespace,
                                                   label_selector=label_selector,
                                                   timeout_seconds=timeout_seconds)
            if obj:
                for item in obj.items:
                    if item.status.reason != "Evicted":
                        return item.metadata.name
            else:
                return None

        except ApiException as e:
            print("Exception when calling CoreV1Api->list_namespaced_pod: %s\n" % e)
            return None

    def get_pod_log(self, namespace="", name="", ):
        api_instance = client.CoreV1Api()
        pretty = True
        try:
            obj = api_instance.read_namespaced_pod_log(name, namespace, pretty=pretty, tail_lines=1000)
            return obj
        except ApiException as e:

            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling ExtensionsV1beta1Api->read_namespaced_pod_log: %s\n" % e)

    def get_deployment_status(self, namespace="", name=""):
        api_instance = client.AppsV1Api()

        try:
            obj = api_instance.read_namespaced_deployment(name, namespace)
            return obj.status.available_replicas
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling ExtensionsV1beta1Api->read_namespaced_deployment: %s\n" % e)
    def get_deployment_ready_status(self, namespace="", name=""):
        api_instance = client.AppsV1Api()

        try:
            obj = api_instance.read_namespaced_deployment(name, namespace)
            return obj.status.ready_replicas
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling ExtensionsV1beta1Api->read_namespaced_deployment: %s\n" % e)


    def get_endpoint(self, namespace="", name=""):
        api_instance = client.CoreV1Api()
        addrs = []
        try:
            api_response = api_instance.read_namespaced_endpoints(name, namespace)
            if api_response.subsets:
                for endp in api_response.subsets:
                    if not endp.not_ready_addresses:
                        for addr in endp.addresses:
                            addrs.append(addr.target_ref.name)

                return addrs
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling ExtensionsV1beta1Api->create_persistent_volume: %s\n" % e)

    def get_pod_status(self, namespace="", name=""):
        api_instance = client.CoreV1Api()

        try:
            api_response = api_instance.read_namespaced_pod_status(name, namespace)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=api_response.status.phase)

            return api_response.status.phase
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="failed to get_pod_status namespace: {}, name: {}, reason-->{}".format(
                                                                      namespace, name,e))

    def get_nodeName_by_podName(self, namespace="", name=""):
        api_instance = client.CoreV1Api()

        try:
            api_response = api_instance.read_namespaced_pod_status(name, namespace)
            if api_response.spec:
                return api_response.spec.node_name
            else:
                return
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling ExtensionsV1beta1Api->get_nodeName_by_podName: %s\n" % e)

    def get_pod_reason(self, namespace="", name=""):
        api_instance = client.CoreV1Api()

        try:
            api_response = api_instance.read_namespaced_pod_status(name, namespace)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of read_namespaced_pod_status: {} ".format(
                                                                      api_response.status.reason))

            return api_response.status.reason

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->read_namespaced_pod_status: %s\n" % e)
            return

    def list_pods_name(self, namespace="", job_name=""):
        api_instance = client.CoreV1Api()
        pod_list = []
        try:
            api_response = api_instance.list_namespaced_pod(namespace=namespace,
                                                            label_selector='job-name={}'.format(job_name))
            if api_instance:
                for item in api_response.items:
                    name = item.metadata.name
                    pod_list.append(name)
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="get pod {} in _namespaced {}".format(
                                                                              name, namespace))

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->read_namespaced_pod_status: %s\n" % e)

        return pod_list

    def get_pod_restart_count_and_reason(self, namespace="", name=""):
        api_instance = client.CoreV1Api()

        try:
            api_response = api_instance.read_namespaced_pod_status(name, namespace)
            return api_response.status.container_statuses[0].restart_count, api_response.status.reason
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->read_namespaced_pod_status: %s\n" % e)

    def get_pod_docker(self, namespace="", name=""):
        api_instance = client.CoreV1Api()

        try:
            api_response = api_instance.read_namespaced_pod_status(name, namespace)
            host_ip = api_response.status.host_ip
            docker_id = api_response.status.container_statuses[0].container_id
            return host_ip, docker_id
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->get_pod_docker: %s\n" % e)

    def get_pods_by_label(self, namespace="", name=""):
        api_instance = client.CoreV1Api()
        label_selector = 'app.kubernetes.io/name=%s' % (
            name,)  # str | A selector to restrict the list of returned objects by their labels. Defaults to everything. (optional)
        timeout_seconds = 56  # int | Timeout for the list/watch call. This limits the duration of the call, regardless of any activity or inactivity. (optional)

        pods = []

        try:
            obj = api_instance.list_namespaced_pod(namespace,
                                                   label_selector=label_selector,
                                                   timeout_seconds=timeout_seconds)
            if obj:
                for it in obj.items:
                    pods.append(it.metadata.name)

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->list_namespaced_pod: %s\n" % e)

        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="get pod list in namespace: {} by label_selector {} :{}".format(
                                                                  namespace, label_selector, pods))
        return pods

    def get_service_port(self, namespace="", name=""):
        api_instance = client.CoreV1Api()
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="namespace: {} , service name: {}".format(
                                                                  namespace, name))

        try:
            api_response = api_instance.read_namespaced_service(name, namespace)
            if api_response:

                portList = []
                for svc in api_response.spec.ports:
                    if svc.node_port:
                        portList.append("{}:{}".format(svc.port, svc.node_port))
                        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                              fileName=os.path.basename(__file__),
                                                                              func=sys._getframe(
                                                                              ).f_code.co_name,
                                                                              num=sys._getframe().f_lineno,
                                                                              args="namespace: {} , service name: {}, service node_port: {}".format(
                                                                                  namespace, name, svc.node_port))

                    else:
                        continue
                return portList

        except ApiException as e:

            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->get_service_port: %s\n" % e)

            return




    def get_namespace_time(self, namespaces):
        api_instance = client.CoreV1Api()
        namespace_list = namespaces.split(",")
        data = {}
        for name in namespace_list:
            try:
                obj = api_instance.read_namespace(name)
                xtime = obj.metadata.creation_timestamp
                t = strptime(str(xtime).split("+")[0], '%Y-%m-%d %H:%M:%S')
                tlist = list(t)
                tlist[3] += 8
                if tlist[3] >= 24:
                    tlist[3] -= 24
                    tlist[2] += 1
                # time = strftime('%Y-%m-%d %H:%M:%S', tuple(tlist))
                old_time = mktime(tuple(tlist))
                new_time = time.time()
                ttime = (new_time-old_time)
                if 0<ttime<(24 * 60 * 60):
                    ytime = ttime / (60 * 60)
                    data[name] = str(round(ytime,2))+"h"
                else:
                    ytime = ttime / (24 * 60 * 60)
                    data[name] = str(abs(int(ytime)))+"d"

            except ApiException as e:
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="Exception when calling ExtensionsV1beta1Api->read_namespace: %s\n" % e)

                data[name] = ""
        return data




    def get_pods_name_by_service(self, namespace="", name=""):
        api_instance = client.CoreV1Api()
        try:
            api_response = api_instance.read_namespaced_endpoints(name, namespace)
            pods = []
            if api_response.subsets:
                for endp in api_response.subsets:
                    if not endp.not_ready_addresses:
                        for addr in endp.addresses:
                            pods.append(addr.target_ref.name)

                        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                              fileName=os.path.basename(__file__),
                                                                              func=sys._getframe(
                                                                              ).f_code.co_name,
                                                                              num=sys._getframe().f_lineno,
                                                                              args="namespace: {} , service name: {}, pods list : {}".format(
                                                                                  namespace, name, pods))

                        return pods

                    else:
                        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                              fileName=os.path.basename(__file__),
                                                                              func=sys._getframe(
                                                                              ).f_code.co_name,
                                                                              num=sys._getframe().f_lineno,
                                                                              args="error!  namespace: {} , service name: {}  has no availed! ".format(
                                                                                  namespace, name))


        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->get_pods_name_by_service: %s\n" % e)

        return

    def exec_pod(self, namespace="", name="", command="sh"):
        api_instance = client.CoreV1Api()
        try:
            api_response = api_instance.connect_get_namespaced_pod_exec(name, namespace, command=command, tty=True)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of read_namespaced_pod_status: {} ".format(
                                                                      api_response))

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->exec_pod: %s\n" % e)

    def create_persist_volume(self, deploy_name):
        api_instance = client.CoreV1Api()
        body = client.V1PersistentVolume()
        body.metadata = client.V1ObjectMeta(name=deploy_name, namespace=deploy_name)
        nfs = client.V1NFSVolumeSource(path="/data-nfs/" + deploy_name, server="172.31.238.10")
        body.spec = client.V1PersistentVolumeSpec(nfs=nfs, capacity={"storage": "2Gi"}, access_modes=["ReadWriteOnce"])
        try:
            api_response = api_instance.create_persistent_volume(body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of read_namespaced_pod_status: {} ".format(
                                                                      api_response))

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->create_persist_volume: %s\n" % e)

    def create_persist_volume_claim(self, deploy_name):
        # create an instance of the API class
        api_instance = client.CoreV1Api()
        namespace = deploy_name  # str | object name and auth scope, such as for teams and projects
        body = client.V1PersistentVolumeClaim()  # V1PersistentVolumeClaim |
        body.metadata = client.V1ObjectMeta(name=deploy_name, namespace=deploy_name)
        body.spec = client.V1PersistentVolumeClaimSpec(access_modes=["ReadWriteOnce"],
                                                       resources=client.V1ResourceRequirements(
                                                           requests={"storage": "2Gi"}))
        try:
            api_response = api_instance.create_namespaced_persistent_volume_claim(namespace, body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of read_namespaced_pod_status: {} ".format(
                                                                      api_response))

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->create_persist_volume_claim: %s\n" % e)

    def create_mysql_init_job(selfs, namespace="", image=""):
        b1 = client.BatchV1Api()
        body = {
            "metadata": {
                "name": "init-db"
            },
            "spec": {
                "template": {
                    "spec": {
                        "initContainers": [
                            {
                                "command": [
                                    "sh",
                                    "-c",
                                    "until nc -z mysql 3306 ; do echo waiting for mysql; sleep 2; done;"
                                ],
                                "image": image,
                                "imagePullPolicy": "Always",
                                "name": "init",
                                "resources": {
                                },
                                "terminationMessagePath": "/dev/termination-log",
                                "terminationMessagePolicy": "File"
                            }
                        ],
                        "restartPolicy": "OnFailure",
                        "schedulerName": "default-scheduler",
                        "securityContext": {
                        },
                        "terminationGracePeriodSeconds": 30,
                        "containers": [
                            {
                                "env": [
                                    {
                                        "name": "TAG",
                                        "value": image.split(":")[1]
                                    },
                                    {
                                        "name": "MYSQL_ROOT_PASSWORD",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "key": "mysql-root-password",
                                                "name": "mysql",
                                                "optional": True
                                            }
                                        }
                                    }
                                ],
                                "name": "source-sql",
                                "image": image,
                                "command": [
                                    "/bin/sh",
                                    "-c",
                                    "mysql -h mysql -uroot -p${MYSQL_ROOT_PASSWORD}  -D mysql -e \"source /sql/${TAG}.sql\""
                                ]
                            }
                        ]
                    }
                },
                "backoffLimit": 4
            }
        }

        try:
            rs = b1.create_namespaced_job(namespace=namespace, body=body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of creating job {} in namespace {} is:  {} ".format(
                                                                      image, namespace, rs))


        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling BatchV1Api->create_namespaced_job: %s\n" % e)
        return


    def create_rdp_init_job(selfs, namespace=""):
        b1 = client.BatchV1Api()
        body = {
            "metadata": {
                "name": "rdp-init-db"
            },
            "spec": {
                "template": {
                    "spec": {
                        "initContainers": [
                            {
                                "command": [
                                    "sh",
                                    "-c",
                                    "until nc -z mysql 3306 ; do echo waiting for mysql; sleep 2; done;"
                                ],
                                "image": "harbor2.flashhold.com/library/mysql-client:rdp",
                                "imagePullPolicy": "Always",
                                "name": "init-rdp",
                                "resources": {
                                },
                                "terminationMessagePath": "/dev/termination-log",
                                "terminationMessagePolicy": "File"
                            }
                        ],
                        "restartPolicy": "OnFailure",
                        "schedulerName": "default-scheduler",
                        "securityContext": {
                        },
                        "terminationGracePeriodSeconds": 30,
                        "containers": [
                            {
                                "env": [
                                    {
                                        "name": "MYSQL_ROOT_PASSWORD",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "key": "mysql-root-password",
                                                "name": "mysql",
                                                "optional": True
                                            }
                                        }
                                    }
                                ],
                                "name": "source-rdp-sql",
                                "image": "harbor2.flashhold.com/library/mysql-client:rdp",
                                "command": [
                                    "/bin/sh",
                                    "-c",
                                    "mysql -h mysql -uroot -p${MYSQL_ROOT_PASSWORD}  -D mysql -e \"source /sql/rdp.sql\""
                                ]
                            }
                        ]
                    }
                },
                "backoffLimit": 4
            }
        }

        try:
            rs = b1.create_namespaced_job(namespace=namespace, body=body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of creating rdp job in namespace {} is:  {} ".format(
                                                                      namespace, rs))


        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling BatchV1Api->create_namespaced rdp_job: %s\n" % e)
        return




    def get_job_status(self, namespace="", name=""):
        b1 = client.BatchV1Api()
        try:
            rs = b1.read_namespaced_job_status(namespace=namespace, name=name)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="job in namespace {} status is {}".format(
                                                                      namespace, rs.status.succeeded))
            if rs.status.succeeded == 1:
                return True

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling BatchV1Api -> read_namespaced_job_status: %s\n" % e)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="type(e): {}".format(type(e)))

            if e.status == 404:
                return True

            return False

    def patch_deployment(self, namespace="", name="", value=None):
        v1 = client.AppsV1Api()
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="args of  patch_namespaced_deployment : namespace={}, name={}, value={}".format(
                                                                  namespace, name, value))

        body = value

        try:
            api_response = v1.patch_namespaced_deployment(namespace=namespace, name=name, body=body)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of  AppsV1Api patch_namespaced_deployment : {}".format(
                                                                      api_response))
            return {"success": True, "message": api_response}

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->patch_namespaces_service: %s\n" % e)

            return {"success": False, "message": e}

    def desc_pod(self, namespace="", name=""):
        if namespace == "":
            return False
        if name == "":
            return False

        c1 = client.CoreV1Api()
        try:
            api_response = c1.read_namespaced_pod(namespace=namespace, name=name)
            desc = []
            if api_response:
                for c in api_response.status.container_statuses:
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="result of  CoreV1Api read_namespaced_pod : {}".format(
                                                                              c.last_state.terminated.reason))

                    desc.append({"container_name": c.name,
                                 "container_status": {"exit_code": c.last_state.terminated.exit_code,
                                                      "reason": c.last_state.terminated.reason}})

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->read_namespaced_pod: %s\n" % e)

        return desc

    def read_deployment(self, namespace="", name=""):
        if namespace == "":
            return False
        if name == "":
            return False

        c1 = client.AppsV1beta1Api()
        try:
            api_response = c1.read_namespaced_deployment(namespace=namespace, name=name)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="pod {} in namespace{} , status.container_statuses: {}".format(
                                                                      name, namespace,
                                                                      api_response))
            # return api_response.status.container_statuses
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling AppsV1beta1Api->read_namespaced_pod: %s\n" % e)

    def patch_configmap(self, namespace="", name="", value={}):
        if namespace == "":
            return False
        if name == "":
            return False
        if not value["data"]:
            return False

        data = self.make_string(value["data"])
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="data of patch_namespaced {} config_map {} is : {}".format(
                                                                  namespace, name,
                                                                  data))
        c1 = client.CoreV1Api()
        try:
            api_response = c1.patch_namespaced_config_map(namespace=namespace, name=name, body={"data": data})
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of patch_namespaced {} config_map {} is : {}".format(
                                                                      namespace, name,
                                                                      api_response))
            return api_response.data
        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->patch_namespaced_config_map: %s\n" % e)
            return None

    def desc_pods_by_label(self, namespace="", value=""):
        api_instance = client.CoreV1Api()
        if len(value.split("=")) != 2:
            return False

        label_selector = value
        timeout_seconds = 56  # int | Timeout for the list/watch call. This limits the duration of the call, regardless of any activity or inactivity. (optional)

        pods = []
        try:
            obj = api_instance.list_namespaced_pod(namespace,
                                                   label_selector=label_selector,
                                                   timeout_seconds=timeout_seconds)
            if obj:
                for pod in obj.items:
                    name = pod.metadata.name
                    desc = self.desc_pod(namespace=namespace, name=name)
                    pods.append({"pod_name": name, "desc": desc})
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="status of desc_pods_by_label pod {} in namespace {}  is : {}".format(
                                                                              namespace, name,
                                                                              desc))

        except ApiException as e:
            print("Exception when calling CoreV1Api->list_namespaced_pod: %s\n" % e)

        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="result of desc_pods_by_label value {} in namespace {}  is : {}".format(
                                                                  namespace, value,
                                                                  pods))
        return pods


    def list_pods_name_nojob(self, namespace=""):
        api_instance = client.CoreV1Api()
        pod_list = []
        try:
            api_response = api_instance.list_namespaced_pod(namespace=namespace)
            if api_instance:
                for item in api_response.items:
                    name = item.metadata.name
                    pod_list.append(name)
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="get pod {} in _namespaced {}".format(
                                                                              name, namespace))

        except ApiException as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when calling CoreV1Api->read_namespaced_pod_status: %s\n" % e)

        return pod_list

#
#
# if __name__ == "__main__":
#     l = K8sApi()
#     print(l.patch_service(namespace="deploy-1573205659", name="evo-wcs-web"))
