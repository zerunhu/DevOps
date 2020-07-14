# coding=utf-8
import sys

reload(sys)
sys.setdefaultencoding('utf-8')
from django.contrib.auth.models import User, Group
from app.models import *
from Api.ldapApi import Uldap
from Api.gitlabApi import Api
from Api.k8sApi import K8sApi
from Api.gitlabApi import Api
from django import forms
from django.db.models import Q
import time
import os
import re
import random
import json
import copy
import datetime
from pyhelm.chartbuilder import ChartBuilder
from pyhelm.tiller import Tiller


# In a convenient location
# def custom_attributes(user, service):
#     l = Uldap()
#     user_info = l.search_userInfo(user.username)
#     return user_info

def manageGroupUser(group_name, users):
    """
    :param group_name: str
    :param users: list
    :return:
    """
    users_str = ",".join(users)
    group = Group.objects.get(name=group_name)
    users = User.objects.filter(username__in=users)
    group.user_set.clear()
    for user in users:
        user.groups.add(group)
        user.save()
    l = Uldap()
    l.delete_group_all_member(group_name)
    l.delete_group2_all_member(group_name)
    l.add_group_member(group_name, users_str)
    l.add_group2_member(group_name, users_str)
    l.conn.unbind_s()
    return True


def validateData(data):
    # if data.find("/") != -1 or data.find("_") != -1:
    #     raise forms.ValidationError("环境名只允许字母,数字,和 -。并且开头和结尾必须是字母")

 #   rsn = re.match(r'[a-zA-Z0-9]([-a-zA-Z0-9]*[a-zA-Z0-9])', data)
 #   if not rsn:
 #       raise forms.ValidationError("环境名只允许字母,数字,和 -。并且开头和结尾必须是字母")
    return data


def generateFuncBranch(hotfix=None, desc=None):
    # t = int(time.time())
    if hotfix:
        featureName = "hotfix/" + desc
    else:
        featureName = "feature/" + desc
    return featureName


def createReleaseBranch(project_id=None, branch_name="", version=""):
    project = Project.objects.get(id=project_id)
    branch = Branch.objects.create(
        project=project,
        name=branch_name,
        desc=branch_name,
        type="release",
        version=version,
        baseBranch="master"
    )
    createBranchBy(origin="master", target=branch.name, project_id=project_id)
    return True, ""


def createTagBy(project_id=None, tag_name="", ref=""):
    project = Project.objects.get(id=project_id)
    apps = project.app_set.all()
    l = Api()
    for app in apps:
        gitlab_project = get_evo_or_evoProjects_gitlab_project(
            project_id, app.id)
        l.create_project_tag(
            project_id=gitlab_project['id'], tag_name=tag_name, ref=ref)
    return True, ""


def createSingleAppTag(tag_name=None, ref=None, project_id=None, app_id=None):
    l = Api()
    # below project is gitlab project concept
    gitlab_project = get_evo_or_evoProjects_gitlab_project(project_id, app_id)
    rsn = l.create_project_tag(
        project_id=gitlab_project['id'], tag_name=tag_name, ref=ref)
    return rsn


def createBranchBy(origin=None, target=None, project_id=None):
    project = Project.objects.get(id=project_id)
    l = Api()
    # below project is gitlab project concept
    apps = project.app_set.all()
    for app in apps:
        gitlab_project = get_evo_or_evoProjects_gitlab_project(
            project_id, app.id)
        if not l.search_project_branch(project_id=gitlab_project['id'], branch=target):
            l.create_project_branch(
                project_id=gitlab_project['id'], origin_branch_name=origin, target_branch_name=target)
    return True


def createSingleAppBranch(origin=None, target=None, project_id=None, app_id=None):
    l = Api()
    gitlab_project = get_evo_or_evoProjects_gitlab_project(project_id, app_id)
    # below project is gitlab project concept
    if not l.search_project_branch(project_id=gitlab_project['id'], branch=target):
        l.create_project_branch(
            project_id=gitlab_project['id'], origin_branch_name=origin, target_branch_name=target)
    return True


def deleteBranchby(project_id=None, branch_name=""):
    project = Project.objects.get(id=project_id)
    l = Api()
    # below project is gitlab project concept
    apps = project.app_set.all()
    for app in apps:
        gitlab_project = get_evo_or_evoProjects_gitlab_project(
            project_id, app.id)
        if l.search_project_branch(project_id=gitlab_project['id'], branch=branch_name):
            l.delete_project_branch(
                project_id=gitlab_project['id'], branch_name=branch_name)
    return True


def deleteSingleAppBranch(project_id=None, branch_name="", app_name=""):
    l = Api()
    app = App.objects.get(project__id=project_id, name=app_name)
    # below project is gitlab project concept
    gitlab_project = get_evo_or_evoProjects_gitlab_project(project_id, app.id)
    if l.search_project_branch(project_id=gitlab_project['id'], branch=branch_name):
        l.delete_project_branch(
            project_id=gitlab_project['id'], branch_name=branch_name)
    return True


def get_evo_or_evoProjects_gitlab_project(project_id, app_id):
    app = App.objects.get(id=app_id)
    project = Project.objects.get(id=project_id)
    group_name, app_name = app.slugName.split("/")[-2:]
    l = Api()
    if project.name == "evo":
        gitlab_project = l.get_group_project_by_name(group_name=group_name, project_name=app_name,
                                                     full_path="software/evo/" + group_name)
    else:
        gitlab_project = l.get_group_project_by_name(group_name=group_name, project_name=app_name,
                                                     full_path="software/evo-projects/" + group_name)
    return gitlab_project


def generateRandomString(num):
    ran = random.sample(
        'abcdefghijklmnopqrstuvwxyz0123456ABCDEFGHIJKLMNOPQRSTUVWXYZ', int(num))
    return "".join(ran)


def deleteDployTemplate(deploy_id):
    if Deployment.objects.filter(id=deploy_id):
        obj = Deployment.objects.get(id=deploy_id)
        tmp_dir = "/tmp/%s" % (obj.envName)
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

    images = obj.imageVersion.exclude(baseAppFlag=1)
    for image in images:
        appName = image.chartAddress.split("/")[-1]
        chart_name = "%s-%s" % (obj.envName, image.chartAddress.split("/")[-1])
        repo = "/".join(image.chartAddress.split("/")[0:-1])

        t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])
        chart = ChartBuilder(
            {'name': appName, 'source': {'type': 'directory', 'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT, repo.split("/")[-1], appName)}})
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



def installBaseApp(appName, chart_name, repo, namespace, tag, dynamicEnv="", rcs_filebeat=False, rdp_Flag=False):
    t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])
    if appName in settings.POD_PERSISTENCE_APP:
        if rcs_filebeat and appName == "evo-rcs":
            chart = ChartBuilder(
                {'name': appName, 'source': {'type': 'directory',
                                             'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT,
                                                                                      "evo-baseapp-charts", "evo-rcs-filebeat")}})
        elif rdp_Flag and appName == "evo-wcs-g2p":
            chart = ChartBuilder(
                {'name': appName, 'source': {'type': 'directory',
                                             'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT,
                                                                                      "evo-baseapp-charts",
                                                                                      "evo-wcs-g2p-filebeat")}})
        elif rdp_Flag and appName == "evo-rcs":
            chart = ChartBuilder(
                {'name': appName, 'source': {'type': 'directory',
                                             'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT,
                                                                                      "evo-baseapp-charts",
                                                                                      "evo-wcs-g2p-filebeat")}})
        else:
            chart = ChartBuilder(
                {'name': appName, 'source': {'type': 'directory',
                                             'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT,
                                                                                      "evo-baseapp-charts", appName)}})
    else:
        chart = ChartBuilder(
            {'name': appName, 'source': {'type': 'directory',
                                         'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT,
                                                                                  "evo-baseapp", appName)}})
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="start to install   {} chart in namespace  {}, image is {}:{}".format(
                                                              chart_name, namespace, appName, tag))
    try:
        if appName in settings.TCPSERVERMAP.keys():
            install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=namespace,
                                               name=chart_name,
                                               values={
                                                   "image": {
                                                       "repository": "{}/{}".format(repo, appName).replace("chartrepo/",
                                                                                                           "").replace(
                                                           "http://", ""),
                                                       "tag": tag,
                                                       "pullPolicy": "IfNotPresent"
                                                   },
                                                   "env": {
                                                       "SPRING_PROFILES_ACTIVE": "k8s",
                                                       "db_url": "mysql:3306",
                                                       "db_username": "root",
                                                       "db_password": "123456",
                                                       "registry": "registry:8761",
                                                       "host_ip": "",
                                                       "host_port": "8023",
                                                       "redis_host": "redis",
                                                       "release_name": appName,
                                                       "rmqnamesrv": "rmq:9876"
                                                   },
                                                   "dynamicEnv": dynamicEnv,
                                                   "ingress": {
                                                       "enabled": False,
                                                       "hosts": []
                                                   },
                                                   "service": {
                                                       "type": "NodePort"
                                                   }
                                               })
        else:
            install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=namespace,
                                               name=chart_name,
                                               values={
                                                   "image": {
                                                       "repository": "{}/{}".format(repo, appName).replace("chartrepo/",
                                                                                                           "").replace(
                                                           "http://", ""),
                                                       "tag": tag,
                                                       "pullPolicy": "IfNotPresent"
                                                   },
                                                   "env": {
                                                       "SPRING_PROFILES_ACTIVE": "k8s",
                                                       "db_url": "mysql:3306",
                                                       "db_username": "root",
                                                       "db_password": "123456",
                                                       "registry": "registry:8761",
                                                       "host_ip": "",
                                                       "host_port": "8023",
                                                       "redis_host": "redis",
                                                       "release_name": appName,
                                                       "rmqnamesrv": "rmq:9876"
                                                   },
                                                   "dynamicEnv": dynamicEnv,
                                                   "ingress": {
                                                       "enabled": False,
                                                       "hosts": []
                                                   },
                                                   "service": {
                                                       "type": "ClusterIP"
                                                   }
                                               })

        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="success to install helm chart {} in  namespace {}"
                                                              .format(chart_name, namespace))

        return {"rs": 1,
                "msg": "success to install helm chart {} in  namespace {}".format(chart_name, namespace)}

    except Exception, e:
#        _ = t.uninstall_release(release=chart_name)
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="failed to install helm chart {} in  namespace {}, reson is {}".format(
                                                                  chart_name, namespace, e))
        return {"rs": 0,
                "msg": "failed to install helm chart {} in  namespace {} reason-->{}".format(chart_name, namespace,e)}


def deployBaseApp(deploy_id,dynamicEnv_dict=""):
    obj = Deployment.objects.get(id=deploy_id)
    if "logstash" in obj.commonApp:
        rcs_filebeat = True
    else:
        rcs_filebeat = False
    if "rdp" in obj.commonApp:
        rdp_Flag = True
    else:
        rdp_Flag = False
    images = obj.imageVersion.all()
    for image in images:
        appName = image.chartAddress.split("/")[-1]
        if appName == "evo-rcs-log" and not rcs_filebeat:
            continue
        chart_name = "%s-%s" % (obj.envName, appName)
        repo = "/".join(image.chartAddress.split("/")[0:-1])
        tag = image.name.split(":")[1]
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="ready to install helm chart {} in  namespace {}, image version is {}:{}".format(
                                                                  chart_name, obj.envName, appName, tag))
        if appName in dynamicEnv_dict.keys():
            dynamicEnv = eval(dynamicEnv_dict[appName])
            rs = installBaseApp(dynamicEnv=dynamicEnv, appName=appName, chart_name=chart_name, repo=repo,
                                namespace=obj.envName, tag=tag, rcs_filebeat=rcs_filebeat, rdp_Flag=rdp_Flag)
        else:
            rs = installBaseApp(appName=appName, chart_name=chart_name, repo=repo, rdp_Flag=rdp_Flag,
                                namespace=obj.envName, tag=tag, rcs_filebeat=rcs_filebeat)
        if rs["rs"]:
            continue
        else:
            return {"rs":0,"msg":rs["msg"]}
    return {"rs":1,"msg":"创建基础应用成功"}


def deployCommonApp(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    charts = obj.commonApp.split(",")
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
            if chart_name == "nginx":
                continue

            chart = ChartBuilder(
                {'name': chart_name, 'source': {'type': 'directory', 'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT, "library", chart_name)}})
            try:
                if chart_name == "redis":
                    install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=obj.envName,
                                                       name="{}-{}".format(obj.envName, chart_name),
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
                elif chart_name == "mysql":
                    imageName = settings.MYSQL_IMAGE_BASE
                    install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=obj.envName,
                                                       name="{}-{}".format(obj.envName, chart_name),
                                                       values={
                                                           "imageName": imageName.split(':')[0],
                                                           "imageTag": imageName.split(':')[1],
                                                           "service": {
                                                               "type": "NodePort"
                                                           },
                                                           "ingress": {
                                                               "enabled": False
                                                           }
                                                       })
                elif chart_name == "logstash" or "rdp":
                    install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=obj.envName,
                                                       name="{}-{}".format(obj.envName, chart_name))
                else:
                    install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=obj.envName,
                                                       name="{}-{}".format(obj.envName, chart_name),
                                                       values={
                                                           "service": {
                                                               "type": "NodePort"
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
            except Exception, e:
#                try:
#                    _ = t.uninstall_release(release=chart_name)
#                except Exception, e:
#                    pass

                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="failed to install helm chart {} in  namespace {}, reson is {}".format(
                                                                          chart_name, obj.envName, e))
                
                return {"rs":0,"msg":"failed to install helm chart {} in  namespace {}, reson is {}".format(
                                                                          chart_name, obj.envName, e)}

        return {"rs":1,"msg":"创建common应用成功"}

def deployInitData(dataSet="", namespace=""):
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="deployInitData arg:{} {} ".format(dataSet, namespace))
    if dataSet == "":
        return {"rs":0,"mgs":"缺少dataSet参数"}
    if namespace == "":
        return {"rs":0,"msg":"缺少namespace参数"}

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
        try:
            rs = l.create_mysql_init_job(namespace=namespace, image=obj.imageName)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="create_mysql_init_job result:{}".format(rs))
            return {"rs": 1, "msg": "创建初始化db client job成功"}
        except Exception, e:
            pass
        return {"rs":0,"msg":e}
    return {"rs":0,"msg":"数据集harbor仓库地址不存在"}

def deployRdpData(namespace=""):

    l = K8sApi()
    try:
        rs = l.create_rdp_init_job(namespace=namespace)
        return {"rs": 1, "msg": "创建初始化db rdp job成功"}
    except Exception, e:
        pass
    return {"rs":0,"msg":e}


def deleteDeployCommonApp(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    commonApps = obj.commonApp.split(",")

    for app in commonApps:
        t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])

        try:
            _ = t.uninstall_release(release="{}-{}".format(obj.envName, app))
        except Exception, e:
            continue

    return True


def deleteDeployBaseApp(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    baseImages = obj.imageVersion.all()
    for image in baseImages:
        appName = image.chartAddress.split("/")[-1]
        t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])

        try:
            _ = t.uninstall_release(release="%s-%s" % (obj.envName, appName))
        except Exception, e:
            continue

    return True


'''

    def update_release(self, chart, namespace, dry_run=False,
                       name=None, values=None, wait=False,
                       disable_hooks=False, recreate=False,
                       reset_values=False, reuse_values=False,
                       force=False, description="", install=False):
'''


# 变更分为三部分：
# 1.镜像版本变更
# 2.资源限制变更
# 3.环境变量变更

def updateChartNew(namespace, appName, memory, newImageName, old_imageId, rcs_filebeat=False):
    if not namespace:
        return False
    elif not appName:
        return False
    elif not newImageName:
        return False
    dynamicEnv_dict = Deployment.objects.get(envName=namespace).dynamicEnv
    if dynamicEnv_dict:
        dynamicEnv_dict = eval(dynamicEnv_dict)
        if dynamicEnv_dict.has_key(appName):
            dynamicEnv = eval(dynamicEnv_dict[appName])
        else:
            dynamicEnv = {}
    else:
        dynamicEnv = {}
    if appName in settings.POD_PERSISTENCE_APP:
        if appName == "evo-rcs" and rcs_filebeat:
            chart = ChartBuilder(
                {'name': appName, 'source': {'type': 'directory',
                                             'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT,
                                                                                      "evo-baseapp-charts", "evo-rcs-filebeat")}})
        else:
            chart = ChartBuilder(
                {'name': appName, 'source': {'type': 'directory',
                                             'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT,
                                                                                      "evo-baseapp-charts",appName)}})
    else:
        chart = ChartBuilder(
            {'name': appName, 'source': {'type': 'directory',
                                         'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT,
                                                                                  "evo-baseapp", appName)}})
    if "Mi" not in memory:
        memory = "{}Mi".format(memory)

        # 目前只修改镜像版本、内存设置
        value = {
            "env": {
                "SPRING_PROFILES_ACTIVE": "k8s",
                "db_url": "mysql:3306",
                "db_username": "root",
                "db_password": "123456",
                "registry": "registry:8761",
                "host_ip": "",
                "host_port": "8023",
                "redis_host": "redis",
                "release_name": appName,
                "rmqnamesrv": "rmq:9876"
            },
            "ingress": {
                "enabled": False,
                "hosts": []
            },
            "service": {
                "type": "ClusterIP"
            },
            "image": {
                "repository": newImageName.split(":")[0],
                "tag": newImageName.split(":")[1],
                "pullPolicy": "IfNotPresent"
            },
            "dynamicEnv": dynamicEnv,
            "resources": {
                "limits": {
                    "memory": memory
                },
                "requests": {
                    "memory": memory
                }
            }
        }

    applist = ["evo-basic", "evo-rcs", "evo-station", "evo-wes", "evo-wcs-g2p", "evo-wcs-engine"]
    if appName in applist:
        value["service"]["type"] = "NodePort"

    t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="ready to update helm chart {} in namespace {} , value is  {}".format(
                                                              "{}-{}".format(namespace, appName),
                                                              namespace, value))
    try:
#        rs = t.update_release(chart.get_helm_chart(), namespace=namespace,
#                              name="{}-{}".format(namespace, appName), values=value, )
        # print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
        #                                                       fileName=os.path.basename(__file__),
        #                                                       func=sys._getframe(
        #                                                       ).f_code.co_name,
        #                                                       num=sys._getframe().f_lineno,
        #                                                       args="result of upgrade helm chart {} in namespace {} is {}".format(
        #                                                           "{}-{}".format(namespace, appName),
        #                                                           namespace, rs))
        chart_name = "{}-{}".format(namespace, appName)
        rs1 = t.uninstall_release(release=chart_name)
        if rs1:
            old_imageVersion = ImageVersion.objects.get(id=old_imageId)
            deploy = Deployment.objects.get(envName=namespace)
            deploy.imageVersion.remove(old_imageVersion)
            deploy.save()
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of uninstall helm chart {} in namespace {} is {}".format(
                                                                      "{}-{}".format(namespace, appName),
                                                                      namespace, rs1))

            rs2 = t.install_release(chart.get_helm_chart(), dry_run=False,
                                    namespace=namespace, name=chart_name,
                                    values=value)
            if rs2:
                imageVersion = ImageVersion.objects.get(repoAddress=newImageName)
                deploy.imageVersion.add(imageVersion)
                deploy.save()
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of install helm chart {} in namespace {} is {}".format(
                                                                      "{}-{}".format(namespace, appName),
                                                                      namespace, rs2))


    except Exception, e:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="Exception when update helm chart : %s\n" % e)
        return {"rs":0,"msg":"Exception when update helm chart :{}".format(e)}
    return {"rs":1,"msg":"应用变更成功"}


def updateChartNewNomem(namespace, appName, newImageName, old_imageId, rcs_filebeat=False):
    # 校验数据，姿势好几种，哪一种不香
    if not namespace:
        return False
    elif not appName:
        return False
    elif not newImageName:
        return False

    if appName in settings.POD_PERSISTENCE_APP:
        if appName == "evo-rcs" and rcs_filebeat:
            chart = ChartBuilder(
                {'name': appName, 'source': {'type': 'directory',
                                             'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT,
                                                                                      "evo-baseapp-charts", "evo-rcs-filebeat")}})
        else:
            chart = ChartBuilder(
                {'name': appName, 'source': {'type': 'directory',
                                             'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT,
                                                                                      "evo-baseapp-charts",appName)}})
    else:
        chart = ChartBuilder(
            {'name': appName, 'source': {'type': 'directory', 'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT, "evo-baseapp", appName)}})
    chart_values = chart.get_values().raw
    values_list = chart_values.split('\n')
    memorys=[]
    for i in values_list:
        if 'memory' in i:
            memorys.append(i)
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="获取环境 {}里应用{}的chart value, 截取的内存设置值是{}".format(
                                                              namespace, appName, memorys))
    memory=memorys[0].split(': ')[1]
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="获取环境 {}里应用{}的内存设置值是{}".format(
                                                              namespace, appName, memorys))
    dynamicEnv_dict = Deployment.objects.get(envName=namespace).dynamicEnv
    if dynamicEnv_dict:
        dynamicEnv_dict = eval(dynamicEnv_dict)
        if dynamicEnv_dict.has_key(appName):
            dynamicEnv = eval(dynamicEnv_dict[appName])
        else:
            dynamicEnv = {}
    else:
        dynamicEnv = {}
    # 目前只修改镜像版本、内存设置
    value = {
        "env": {
        "SPRING_PROFILES_ACTIVE": "k8s",
            "db_url": "mysql:3306",
            "db_username": "root",
            "db_password": "123456",
            "registry": "registry:8761",
            "host_ip": "",
            "host_port": "8023",
            "redis_host": "redis",
            "release_name": appName,
            "rmqnamesrv": "rmq:9876"
        },
        "ingress": {
            "enabled": False,
            "hosts": []
        },
        "service": {
            "type": "ClusterIP"
        },
        ""
        "image": {
            "repository": newImageName.split(":")[0],
            "tag": newImageName.split(":")[1],
            "pullPolicy": "IfNotPresent"
        },
        "dynamicEnv": dynamicEnv,
        "resources": {
            "limits": {
                "memory": memory
            }
        }
    }
    applist = ["evo-basic","evo-rcs","evo-station","evo-wes","evo-wcs-g2p","evo-wcs-engine"]
    #if appName in settings.TCPSERVERMAP.keys():
    if appName in applist:
        value["service"]["type"] = "NodePort"
    

    t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="ready to update helm chart {} in namespace {} , value is  {}".format(
                                                              "{}-{}".format(namespace, appName),
                                                              namespace, value))
    try:
#        rs = t.update_release(chart.get_helm_chart(), namespace=namespace,
#                              name="{}-{}".format(namespace, appName), values=value, )
        # print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
        #                                                       fileName=os.path.basename(__file__),
        #                                                       func=sys._getframe(
        #                                                       ).f_code.co_name,
        #                                                       num=sys._getframe().f_lineno,
        #                                                       args="result of upgrade helm chart {} in namespace {} is {}".format(
        #                                                           "{}-{}".format(namespace, appName),
        #                                                           namespace, rs))

        chart_name = "{}-{}".format(namespace, appName)
        rs1 = t.uninstall_release(release=chart_name)
        if rs1:
            old_imageVersion = ImageVersion.objects.get(id=old_imageId)
            deploy = Deployment.objects.get(envName=namespace)
            deploy.imageVersion.remove(old_imageVersion)
            deploy.save()
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of uninstall helm chart {} in namespace {} is {}".format(
                                                                      "{}-{}".format(namespace, appName),
                                                                      namespace, rs1))

            rs2 = t.install_release(chart.get_helm_chart(), dry_run=False,
                                    namespace=namespace, name=chart_name,
                                    values=value)
            if rs2:
                imageVersion = ImageVersion.objects.get(repoAddress=newImageName)
                deploy.imageVersion.add(imageVersion)
                deploy.save()
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of install helm chart {} in namespace {} is {}".format(
                                                                      "{}-{}".format(namespace, appName),
                                                                      namespace, rs2))


    except Exception, e:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="应用变更失败! Exception when update helm chart : %s\n" % e)


        return {"rs":0,"msg":"Exception when update helm chart :{}".format(e)}
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="应用变更成功 ~")
    return {"rs":1,"msg":"应用变更成功"}

def updateBasicDebug(namespace):
    deployId = Deployment.objects.get(envName=namespace).id
    images = Deployment.objects.get(envName=namespace).imageVersion.all()
    for image in images:
        if image.name == "evo-basic":
        #if "evo-basic" in image.name and "web" not in image.name:
            imageVersion = image
    imageName = imageVersion.repoAddress
    #appName = imageVersion.appName
    #port = 8023
    data = getRCSport(deploy_id = deployId, deploy_envName = namespace, appName="evo-basic", port=8023)
    if not data:
        return False
    hostIp = data[0]["nodeIp"]
    hostPort = data[0]["randomPort"]
    hostName = [k for k, v in settings.NODEMAP.items() if v == hostIp][0]


    value = {
        "env": {
        "SPRING_PROFILES_ACTIVE": "k8s",
            "db_url": "mysql:3306",
            "db_username": "root",
            "db_password": "123456",
            "registry": "registry:8761",
            "host_ip": hostIp,
            "host_port": hostPort,
            "redis_host": "redis",
            "release_name": "evo-basic",
            "rmqnamesrv": "rmq:9876"
        },
        "ingress": {
            "enabled": False,
            "hosts": []
        },
        "service": {
            "type": "Nodeport"
        },
        "nodeSelector": {"kubernetes.io/hostname":hostName},
        "image": {
            "repository": imageName.split(":")[0].encode(),
            "tag": imageName.split(":")[1].encode(),
            "pullPolicy": "IfNotPresent"
        },
    }


    t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])
    chart = ChartBuilder(
        {'name': appName, 'source': {'type': 'directory', 'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT, settings.BASEAPP_CHARTS_ADDR.split("/")[-1], appName)}})
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="ready to update helm chart {} in namespace {} , value is  {}".format(
                                                              "{}-{}".format(namespace, appName),
                                                              namespace, value))
    try:
        rs = t.update_release(chart.get_helm_chart(), namespace=namespace,
                              name="{}-{}".format(namespace, appName), values=value, )
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="result of update helm chart {} in namespace {} is {}".format(
                                                                  "{}-{}".format(namespace, appName),
                                                                  namespace, rs))
    except Exception, e:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="Exception when update helm chart : %s\n" % e)

        return False

    return True


def updateChart(deploy_id, image_id, memory):
    new_image = ImageVersion.objects.get(id=image_id)
    if not new_image:
        return False

    deploy = Deployment.objects.get(id=deploy_id)
    if not deploy:
        return False

    memory = memory
    if "Mi" not in memory:
        memory = "{}Mi".format(memory)

    DeployHistory.objects.create(deploy=deploy,
                                 msg=u"添加或更新release {} ,  memory: {}, image.name: {}".format(
                                     deploy.envName, memory, new_image.name, chartTmpDir=""))

    # 目前只修改镜像版本、内存设置
    value = {
        "env": {
            "SPRING_PROFILES_ACTIVE": "k8s",
            "db_url": "mysql:3306",
            "db_username": "root",
            "db_password": "123456",
            "registry": "registry:8761",
            "host_ip": "",
            "host_port": "8023",
            "redis_host": "redis",
            "release_name": new_image.appName,
            "rmqnamesrv": "rmq:9876"
        },
        "ingress": {
            "enabled": False,
            "hosts": []
        },
        "service": {
            "type": "ClusterIP"
        },
        "image": {
            "repository": new_image.repoAddress.split(":")[0],
            "tag": new_image.repoAddress.split(":")[1],
            "pullPolicy": "IfNotPresent"
        },
        "resources": {
            "limits": {
                "memory": memory
            }
        }
    }

    if new_image.appName == "evo-rcs":
        value["service"]["type"] == "NodePort"

    t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])
    chart = ChartBuilder(
        {'name': new_image.appName, 'source': {'type': 'directory', 'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT, settings.BASEAPP_CHARTS_ADDR.split("/")[-1], new_image.appName)}})

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="ready to update helm chart {} in namespace {} , value is  {}".format(
                                                              "{}-{}".format(deploy.envName, new_image.appName),
                                                              deploy.envName, value))
    try:
        rs = t.update_release(chart.get_helm_chart(), namespace=deploy.envName,
                              name="{}-{}".format(deploy.envName, new_image.appName), values=value, )
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="result of update helm chart {} in namespace {} is {}".format(
                                                                  "{}-{}".format(deploy.envName, new_image.appName),
                                                                  deploy.envName, rs))
    except Exception, e:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="Exception when update helm chart : %s\n" % e)

        return False

    return True


def get_or_assign_ingress_tcp_port(service=None):
    port = None
    obj = IngressData.objects.all()
    if not obj:
        obj = IngressData.objects.create(tcpService="{}", udpService="{}")
    else:
        obj = obj[0]
    data = obj.tcpService
    data = json.loads(data)
    for key in data:
        if data[key] == service:
            return key
    loop = True
    while loop:
        port = random.choice(range(30000, 39999))
        if port in data:
            continue
        data[int(port)] = service
        break
    data = json.dumps(data)
    obj.tcpService = data
    obj.save()
    return port


def delete_release_random_port(release_name):
    obj = IngressData.objects.all()
    if not obj:
        return
    try:
        obj = obj[0]
        data = obj.tcpService
        data = json.loads(data)
    except:
        return
    data_copy = copy.deepcopy(data)
    for key in data_copy:
        if data[key].find(release_name + "/") != -1:
            data.pop(key)
    data = json.dumps(data)
    obj.tcpService = data
    obj.save()
    return


def delete_dataset_random_port(dataset_name):
    obj = IngressData.objects.all()
    if not obj:
        return
    try:
        obj = obj[0]
        data = obj.tcpService
        data = json.loads(data)
    except:
        return
    data_copy = copy.deepcopy(data)
    for key in data_copy:
        if data[key].find(dataset_name) != -1:
            data.pop(key)
    data = json.dumps(data)
    obj.tcpService = data
    obj.save()
    return


def replace_ingress_tcp(service_name=None, random_port=None):
    obj = IngressData.objects.all()
    if not obj:
        return
    try:
        obj = obj[0]
        data = obj.tcpService
        data = json.loads(data)
        if random_port in data:
            data[random_port] = service_name
        data = json.dumps(data)
        obj.tcpService = data
        obj.save()
        return
    except:
        return


def delete_release_random_port_by_port(port):
    obj = IngressData.objects.all()
    if not obj:
        return
    try:
        obj = obj[0]
        data = obj.tcpService
        data = json.loads(data)
    except:
        return
    data_copy = copy.deepcopy(data)
    for key in data_copy:
        if key == port:
            data.pop(key)
    data = json.dumps(data)
    obj.tcpService = data
    obj.save()
    return


def reload_ingress_tcp_port():
    obj = IngressData.objects.all()
    if not obj:
        return

    try:
        obj = obj[0]
        data = obj.tcpService
        data = json.loads(data)
    except:
        return
    obj = K8sApi()
    obj.replace_config_map(body=data)
    return


def convert_branch_name(branch_name):
    return branch_name.replace("/", "-").replace(".", "-")


def deploy_common_env(config, chart_name, deploy_name=None):
    data = config.replace("{{registry_host}}", "registry:8761"). \
        replace("{{db_url}}", "mysql:3306"). \
        replace("{{db_username}}", "root"). \
        replace("{{db_password}}", "123456"). \
        replace("{{redis_host}}", "redis"). \
        replace("{{host_ip}}", ""). \
        replace("{{host_port}}", ""). \
        replace("{{rmqnamesrv}}", "rmq:9876") \
        .replace("{{release_name}}",
                 "{chart_name}".format(chart_name=chart_name))
    return data


def get_tcp_service_random_port(namespace="", service_name="", port=""):
    service_name = "{namespace}/{service_name}:{port}".format(namespace=namespace,
                                                              service_name="%s" % (
                                                                  service_name,),
                                                              port=port)
    random_port = get_or_assign_ingress_tcp_port(service_name)
    return random_port


def getRCSport(deploy_id, deploy_envName,appName, port):
    tcpService = {}
    #tcpServicelist = []
    serverPort = [port]
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="deploy_id: {}, deploy_envName: {}, serverPort: {}".format(
                                                              deploy_id, deploy_envName, serverPort))
    for port in serverPort:

        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="deploy_id: {}, deploy_envName: {}".format(
                                                                  deploy_id, deploy_envName))
        if not deploy_id:
            return tcpService

        if not deploy_envName:
            return tcpService

        tcpService = {"randomPort": "", "nodeIp": "", "port": port}
        l = K8sApi()
        prs = l.patch_service(namespace=deploy_envName, name=appName)
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="result of  fatch service appName: {}".format(prs))

        if len(prs) < 1:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="failed to fatch service appName!")

        else:
            NodePort = ""
            for pv in prs:
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="service {} in {}, svc port  is {} , nodePort is {}".format(appName, deploy_envName, pv.split(":")[0], pv.split(":")[1]))
                if pv.split(":")[0] == str(port):
                    NodePort = pv.split(":")[1]
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="NodePort of service app {}  in {} is {}".format(appName, 
                                                                              deploy_envName, NodePort))
                    break

            if not NodePort:
                #continue
                return {}

            pods = l.get_pods_name_by_service(namespace=deploy_envName, name=appName)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="get app {} pods_name_by_service app {} in {} is {}".format(appName,appName,deploy_envName, pods))
            if pods:
                nodeName = l.get_nodeName_by_podName(namespace=deploy_envName, name=pods[0])
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="get app {} nodeName  in {} is {}".format(appName,
                                                                          deploy_envName, nodeName))
                if nodeName:
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="get app {}  pod for node : {}".format(appName,
                                                                              nodeName))

                    tcpService = {"randomPort": NodePort, "nodeIp": settings.NODEMAP[nodeName], "port": str(port)}

        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="return tcpService : {}".format(
                                                                  tcpService))
        #tcpServicelist.append(tcpService)

    return tcpService

'''
def getRCSport(deploy_id, deploy_envName):
    tcpService = {"randomPort": "", "nodeIp": "", "port": "7070"}

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="deploy_id: {}, deploy_envName: {}".format(
                                                              deploy_id, deploy_envName))
    if not deploy_id:
        return tcpService

    if not deploy_envName:
        return tcpService

    l = K8sApi()
    prs = l.patch_service(namespace=deploy_envName, name="evo-rcs")
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="result of  fatch service evo-rcs : {}".format(prs))

    if len(prs) < 1:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="failed to fatch service evo-rcs!")

    else:
        NodePort = ""
        for pv in prs:
            if pv.split(":")[0] == "7070":
                NodePort = pv.split(":")[1]
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="NodePort of service evo-rcs in {} is {}".format(
                                                                          deploy_envName, NodePort))
                break

        if not NodePort:
            return tcpService

        pods = l.get_pods_name_by_service(namespace=deploy_envName, name="evo-rcs")
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="get evo-rcs pods_name_by_service evo-rcs in {} is {}".format(
                                                                  deploy_envName, pods))
        if pods:
            nodeName = l.get_nodeName_by_podName(namespace=deploy_envName, name=pods[0])
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="get evo-rcs nodeName  in {} is {}".format(
                                                                      deploy_envName, nodeName))
            if nodeName:
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="get rcs  pod for node : {}".format(
                                                                          nodeName))

                tcpService = {"randomPort": NodePort, "nodeIp": settings.NODEMAP[nodeName], "port": "7070"}

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="return tcpService : {}".format(
                                                              tcpService))
    return tcpService
'''

def build_docker_compose(images, lujin):
    # dc_path = settings.DC_PATH
    # f = open(dc_path, 'r')
    # file_data = f.read()
    # f.close()
    # 更改通过api获取gitlab项目的文件
    api = Api()
    file_data = api.get_project_compose_content(lujin)
    for image in images:
        name, version = image.split(":")
        name = "{%s}" % name
        file_data = file_data.replace(name, image)
    return file_data

