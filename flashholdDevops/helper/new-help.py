# coding=utf-8
import sys

reload(sys)
sys.setdefaultencoding('utf-8')

from app.models import *
from Api.k8sApi import K8sApi
import os
import datetime
from pyhelm.chartbuilder import ChartBuilder
from pyhelm.tiller import Tiller








def deleteDployTemplate(deploy_id):
    if Deployment.objects.filter(id=deploy_id):
        obj = Deployment.objects.get(id=deploy_id)
        featureApp = obj.envTemplate.featureApp.all()
        tmp_dir = "/tmp/%s" % (obj.envName)
        t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])

        if featureApp:
            for app in featureApp:
                if obj.imageVersion.filter(appName=app.name).exists():
                    image = obj.imageVersion.filter(appName=app.name)[0]
                    chart_name = image.chartAddress.split("/")[-1]
                    delete_rs = t.uninstall_release(release="%s-%s" % (obj.envName, chart_name))
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="result of uninstall_release {} : {} ".format(
                                                                              "%s-%s" % (obj.envName, chart_name),
                                                                              delete_rs))
        crt = DeployHistory.objects.create(deploy=obj, msg=u"删除环境%s" % obj.envName,
                                           chartTmpDir=os.path.join(tmp_dir, "deploy_record.log"))
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="result of DeployHistory.objects.create: ".format(
                                                                  crt))

        return True


# 一般不会用到这个
def deployTemplate(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    # featureApp = obj.envTemplate.featureApp.all()
    tmp_dir = "/tmp/%s" % (obj.envName)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    images = obj.imageVersion.exclude(baseAppFlag=1)
    for image in images:
        chart_name = "%s-%s" % (obj.envName, image.chartAddress.split("/")[-1])
        repo = "/".join(image.chartAddress.split("/")[0:-1])

        t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])
        chart = ChartBuilder(
            {'name': chart_name, 'source': {'type': 'directory', 'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT, repo.split("/")[-1], chart_name)}})
        # chart.get_metadata()
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="start to install   {} chart in namespace  {}".format(
                                                                  chart_name, obj.envName))

        try:
            install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=obj.envName,
                                               name=chart_name,
                                               values={"service": {"type": "NodePort"}, "ingress": {"enabled": False}})

            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of  installed chart: {}".format(
                                                                      install_result))
            DeployHistory.objects.create(deploy=obj, msg=str(install_result),
                                         chartTmpDir=chart_name)
        except Exception, e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="failed to install helm chart {} in  namespace {}, reson is {}".format(
                                                                      chart_name, obj.envName, e))
            return False

    return True


def deployBaseApp(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    images = obj.imageVersion.exclude(baseAppFlag=0)
    for image in images:
        appName = image.chartAddress.split("/")[-1]
        chart_name = "%s-%s" % (obj.envName, appName)
        repo = "/".join(image.chartAddress.split("/")[0:-1])

        t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])
        chart = ChartBuilder(
            {'name': chart_name, 'source': {'type': 'directory', 'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT, repo.split("/")[-1], chart_name)}})
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="start to install   {} chart in namespace  {}".format(
                                                                  chart_name, obj.envName))

        try:
            if chart_name == "evo-rcs":
                install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=obj.envName,
                                                   name=chart_name,
                                                   values={
                                                       "env": {
                                                           "SPRING_PROFILES_ACTIVE": "k8s",
                                                           "db_url": "mysql:3306",
                                                           "db_username": "root",
                                                           "db_password": "123456",
                                                           "registry": "registry:8761",
                                                           "host_ip": "",
                                                           "redis_host": "redis",
                                                           "release_name": appName,
                                                           "rmqnamesrv": "rmq:9876"
                                                       },
                                                       "ingress": {
                                                           "enabled": False,
                                                           "hosts": []
                                                       },
                                                       "service": {
                                                           "type": "NodePort"
                                                       }
                                                   })
            else:
                install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=obj.envName,
                                                   name=chart_name,
                                                   values={
                                                       "env": {
                                                           "SPRING_PROFILES_ACTIVE": "k8s",
                                                           "db_url": "mysql:3306",
                                                           "db_username": "root",
                                                           "db_password": "123456",
                                                           "registry": "registry:8761",
                                                           "host_ip": "",
                                                           "redis_host": "redis",
                                                           "release_name": appName,
                                                           "rmqnamesrv": "rmq:9876"
                                                       },
                                                       "ingress": {
                                                           "enabled": False,
                                                           "hosts": []
                                                       },
                                                       "service": {
                                                           "type": "Cluster"
                                                       }
                                                   })

            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of  installed chart: {}".format(
                                                                      install_result))
            DeployHistory.objects.create(deploy=obj, msg=str(install_result),
                                         chartTmpDir=chart_name)
        except Exception, e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="failed to install helm chart {} in  namespace {}, reson is {}".format(
                                                                      chart_name, obj.envName, e))
            return False

    return True


def deployCommonApp(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    charts = obj.commonApp.split(",")
    repo = settings.LOCAL_HARBOR_LIBRARY_REPO
    if charts:
        for ch in charts:
            chart_name = ch.strip()
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="chart_name of deploy  :  {}".format(
                                                                      chart_name))
            t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])
            chart = ChartBuilder(
                {'name': chart_name, 'source': {'type': 'directory', 'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT, repo.split("/")[-1], chart_name)}})
            try:
                if chart_name == "redis":
                    install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=obj.envName,
                                                       name=chart_name,
                                                       values={
                                                           "master": {
                                                               "service": {
                                                                   "type": "NodePort"
                                                               }
                                                           },
                                                           "slave": {
                                                               "service": {
                                                                   "type": "NodePort"
                                                               }
                                                           },
                                                           "ingress": {
                                                               "enabled": False
                                                           }
                                                       })
                elif chart_name == "nginx":
                    install_result = "nginx pass ~ "
                else:
                    install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=obj.envName,
                                                       name=chart_name,
                                                       values={
                                                           "service": {
                                                               "type": "Cluster"
                                                           },
                                                           "ingress": {
                                                               "enabled": False
                                                           }
                                                       })

                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="result of  installed chart: {}".format(
                                                                          install_result))
                DeployHistory.objects.create(deploy=obj, msg=str(install_result),
                                             chartTmpDir=chart_name)
            except Exception, e:
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="failed to install helm chart {} in  namespace {}, reson is {}".format(
                                                                          chart_name, obj.envName, e))
                return False


def deployInitData(dataSet="", namespace=""):
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="deployInitData arg:{} {} ".format(dataSet, namespace))
    if dataSet == "":
        return False
    if namespace == "":
        return False

    obj = DataSet2.objects.get(id=dataSet)
    l = K8sApi()
    if obj.imageName:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="create_mysql_init_job arg:{} {}".format(
                                                                  obj.imageName, namespace))

        rs = l.create_mysql_init_job(namespace=namespace, image=obj.imageName)
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="create_mysql_init_job result:{}".format(rs))

        return True
