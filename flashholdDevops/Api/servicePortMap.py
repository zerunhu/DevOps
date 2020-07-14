from app.models import featureServicePortMapping
from app.forms import settings

import os
import sys
import datetime
from Api.k8sApi import K8sApi


def setRCSport(deploy_id, deploy_envName):
    if not deploy_id or deploy_envName:
        return False

    l = K8sApi()
    get_rcs_pm = featureServicePortMapping.objects.filter(deploy_id=deploy_id, port="7070",
                                                          featureAppName="evo-rcs")
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="featureServicePortMapping.objects.filter:".format(
                                                              get_rcs_pm))

    if not get_rcs_pm:
        prs = l.patch_service(namespace=deploy_envName, name="evo-rcs")

        if not prs:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="failed to fatch service evo-rcs!")
            return False
        else:
            l = K8sApi()
            NodePort = ""
            for pv in prs:
                if pv.split(":")[1] == "7070":
                    NodePort = pv.split(":")[1]
                    break

            if not NodePort:
                return False

            pods = l.get_pods_name_by_service(namespace=deploy_envName, name="evo-rcs")
            if pods:
                nodeName = l.get_nodeName_by_podName(namespace=deploy_envName, name=pods[0])
                if nodeName:
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="get rcs  pod for node : {}".format(
                                                                              nodeName))
                    crt = featureServicePortMapping.objects.create(deploy_id=int(deploy_id),
                                                                   port="7070",
                                                                   featureAppName="evo-rcs",
                                                                   randomPort=NodePort,
                                                                   nodeIp=settings.NODEMAP[nodeName])
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(
                                                                              __file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="evo-rcs  featureServicePortMapping.save(): {} ".format(
                                                                              crt))
                    cms = featureServicePortMapping.objects.filter(deploy_id=deploy_id, port="7070",
                                                                   featureAppName="evo-rcs",
                                                                   nodeIp=settings.NODEMAP[nodeName],
                                                                   randomPort=NodePort)
                    if cms:
                        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                              fileName=os.path.basename(
                                                                                  __file__),
                                                                              func=sys._getframe(
                                                                              ).f_code.co_name,
                                                                              num=sys._getframe().f_lineno,
                                                                              args="evo-rcs 7070 featureServicePortMapping.objects.filter(): {} ".format(
                                                                                  cms))
                        return True
                    else:
                        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                              fileName=os.path.basename(
                                                                                  __file__),
                                                                              func=sys._getframe(
                                                                              ).f_code.co_name,
                                                                              num=sys._getframe().f_lineno,
                                                                              args="Error! evo-rcs 7070 featureServicePortMapping.objects.filter() is not exist ")
                        return False




                else:
                    return False
            else:
                return False

    else:
        for pm in get_rcs_pm:
            if not pm["nodeIp"]:
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="data {} {} nodeIp is null! will be delete ".format(
                                                                          pm["deploy_id"], pm["port"]))
                pm.delete()

        setRCSport(deploy_id, deploy_envName)
