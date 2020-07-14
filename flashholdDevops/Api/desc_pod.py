import os, sys, datetime
from django.http import JsonResponse
from Api.k8sApi import K8sApi


def desc_pod(request):
    namespace = request.POST.get("namespace")
    app_name = request.POST.get("app_name")
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="desc_pod arg:{} {} ".format(namespace,
                                                                                            app_name))
    if not namespace:
        return False
    if not app_name:
        return False

    events = []
    l = K8sApi()
    pod_list = l.get_pods_name_by_service(namespace=namespace, name=app_name)
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="pod_list :{}".format(pod_list))
    if pod_list:
        for pod in pod_list:
            rs = l.desc_pod(namespace=namespace, name=pod)
            events.append(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> {} <<<<<<<<<<<<<<<<<<<<<<<<\n".format(pod))
            events.append(rs)
            events.append("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="desc_pod return content :{}".format(events))
    return events
