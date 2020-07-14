import os, sys, datetime
from django.http import JsonResponse
from Api.k8sApi import K8sApi


def change_agv_count(request):
    namespace = request.POST.get("namespace")
    count = int(request.POST.get("count"))
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="change_agv_count arg:{} {} ".format(namespace, count))
    # if not namespace:
    #     return False
    #
    # if not count:
    #     return False

    l = K8sApi()

    patch_rs = l.patch_configmap(namespace=namespace, value={"data": {"agv_sum": count}},
                                 name="evo-agv-simulation-carrier")
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="result of   evo-agv-simulation-carrier deployment : {}".format(
                                                              patch_rs))
    if patch_rs:
        pods = l.get_pods_by_label(namespace=namespace, name="evo-agv-simulation-carrier")
        if pods:
            for pod in pods:
                rs = l.delete_pod(namespace=namespace, name=pod)
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="result of  delete evo-agv-simulation-carrier pod  {} in  deployment {} : {}".format(
                                                                          pod, namespace, rs))

                return JsonResponse({"success": 0}, safe=False)

    return JsonResponse({"success": 1}, safe=False)
