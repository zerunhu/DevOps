# coding=utf-8

from Api.dnsApi import DnsApi
from Api.get_url import check_url
from helper import deploy_nginx_chart
import traceback
import socket
from app.models import *
from django.http import JsonResponse, HttpResponse
from helper import helper
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
from Api.k8sApi import K8sApi
from Api.monitorApi import MonitorApi
from Api.gitlabApi import Api
from pyhelm.tiller import Tiller
from pyhelm.chartbuilder import ChartBuilder
import datetime
import re
import sys
import os
from Api.harborApi import HarborClient


def getExcludeGroupUsers(request):
    users = User.objects.exclude(username="admin").exclude(groups__name=request.GET['group_name'])
    users = [{"username": user.username, "surname": user.last_name} for user in users]
    return JsonResponse(users, safe=False)


def getGroupUsers(request):
    users = User.objects.exclude(username="admin").filter(groups__name=request.GET['group_name'])
    users = [{"username": user.username, "surname": user.last_name} for user in users]
    return JsonResponse(users, safe=False)


def groupAddUsers(request):
    group_name = request.POST['group_name']
    users = request.POST.getlist("to[]")
    helper.manageGroupUser(group_name, users)
    return HttpResponseRedirect(reverse("group_list"))


def getAppName(request):
    apps = request.POST['apps']
    apps_id = apps.split(",")
    order_apps = []
    for id in apps_id:
        app = App.objects.get(id=id)
        order_apps.append(app)
    items = [{"name": app.name} for app in order_apps]
    return JsonResponse(items, safe=False)


def getEvoApp(request):
    apps = App.objects.filter(project__name="evo")
    apps = [{"app_id": app.id, "app_name": app.name, "gitlab_project_id": app.projectId} for app in apps]
    return JsonResponse(apps, safe=False)


def getAppVersionByEnvtemplateId(request):
    fapp = {"featureApp": {}}

    return JsonResponse(fapp, safe=False)

def getBaseAppVersionByEnvtemplateId(request):
    env_id = request.POST['env_id']
    if not env_id:
        return False
    fapp = {"commonApp": {}}
    envs = EnvTemplateDetail.objects.filter(templateList_id=int(env_id))
    for env in envs:
        if env.appName == "evo-nginx":
            continue
        if env.imageTag:
            appName=env.appName
            imageTag=env.imageTag
            branch_Name = env.branchName
            baseapp="{}:{}".format(appName,imageTag)
            if appName not in fapp["commonApp"]:
                fapp["commonApp"][appName] = []
            images_test = ImageVersion.objects.filter(name=baseapp)
            if len(images_test) == 1:
                image = ImageVersion.objects.get(name=baseapp)
            else:
                image = ImageVersion.objects.filter(name=baseapp,branchName=branch_Name)[0]
            fapp["commonApp"][appName].append(
                {"image_id": image.id, "image_name": image.name, "image_repo": image.repoAddress,
                 "image_chart": image.chartAddress, "branch_name": image.branchName})
        else:
            appName=env.appName
            appProject=env.appProject
            branch_Name=env.branchName
            if ImageVersion.objects.filter(appName=appName, projectName=appProject,
                                        branchName=branch_Name).order_by("-createDate")[:10]:
                images = ImageVersion.objects.filter(appName=appName, projectName=appProject,
                                                 branchName=branch_Name).order_by(
                "-createDate")[:10]
            else:
                images = []
            if appName not in fapp["commonApp"]:
                fapp["commonApp"][appName] = []
            for image in images:
                fapp["commonApp"][appName].append(
                    {"image_id": image.id, "image_name": image.name, "image_repo": image.repoAddress,
                     "image_chart": image.chartAddress, "branch_name": image.branchName})

    return JsonResponse(fapp, safe=False)

# 这个接口很危险，一开始是全表扫描，要禁止的
def getBaseApp(request):
    data = []
    images = ImageVersion.objects.filter(baseAppFlag=1, projectName=settings.BASEAPP_ROOT)[:10]
    for image in images:
        data.append({"image_id": image.id, "image_name": "%s-%s" % (image.name, image.chartVersion),
                     "image_repo": image.repoAddress})
    return JsonResponse(data, safe=False)


def getBaseAppByGroup(request):
    data = []
    images = ImageVersion.objects.filter(baseAppFlag=1).values("appName")
    for image in images:
        data.append(image["appName"])
    data = list(set(data))
    data.remove('evo-notification-center-web')
    data.remove('evo-config')
    data.remove('a31024-002-station-web')
    new_data = []
    for i in data:
        a = i.split('-')
        if 'client' not in a:
            new_data.append(i)
    return JsonResponse(new_data, safe=False)


def get_baseapp_branches(request):
    data = []
    api = Api()
    images = ImageVersion.objects.filter(baseAppFlag=1).values("appName")
    for image in images:
        data.append(image['appName'])
    data = list(set(data))
    data.remove('evo-notification-center-web')
    data.remove('evo-config')
    data.remove('a31024-002-station-web')
    new_data = []
    for i in data:
        a = i.split('-')
        if 'client' not in a:
            new_data.append(i.encode('utf-8'))
    branch_date = []
    for i in range(len(new_data)):
        a = new_data[0].split('-')
        if 'web' in a:
            lujin = '/'.join(['software/evo/web', new_data[0]])
            branch_date.append(api.list_baseapp_branch(lujin))
        elif 'wcs' in a:
            branch_date.append(api.list_baseapp_branch('software/evo/wcs/evo-wcs'))
        elif 'auth' in a or 'basic' in a or 'console' in a:
            lujin = App.objects.filter(name=a[1])[0].slugName
            branch_date.append(api.list_baseapp_branch('/'.join(['software', lujin])))
        elif 'notification' in a:
            branch_date.append(api.list_baseapp_branch('software/evo/infra/notification-center'))
        # elif 'wes' in a or 'rcs' in a or 'registry' in a or 'station' in a or 'interface' in a:
        else:
            lujin = App.objects.filter(name=new_data[0])[0].slugName
            branch_date.append(api.list_baseapp_branch('/'.join(['software', lujin])))
        new_data.remove(new_data[0])
    # data1=api.list_baseapp_branch('devops')
    # data2=api.list_baseapp_branch('ops-platform')
    # data.append(data1)
    # data.append(data2)
    # for image in images_name:
    #     data.append(api.list_baseapp_branch(image["appName"]))
    adf = []
    return JsonResponse(branch_date, safe=False)


def pushImageVersion(requests):
    name = requests.GET.get("image_name", "")
    projectName = requests.GET.get("project_name", "")
    appName = requests.GET.get("app_name", "")
    branchName = requests.GET.get("branch_name")
    repoAddress = requests.GET.get("repo_address", "")
    chartAddress = requests.GET.get("chart_address", "")
    servicePort = requests.GET.get("service_port", "")
    containerPort = requests.GET.get("container_port", "")
    chartVersion = requests.GET.get("chart_version", "")
    domain = requests.GET.get("domain", "")
#    config = requests.FILES.get("configfile", "")
    http = requests.GET.get("http", False)
    baseAppFlag = requests.GET.get("baseapp_flag", 0)

    if branchName.find("release") != -1:
        baseAppFlag = 1

    ImageVersion.objects.create(name=name,
                                projectName=projectName,
                                appName=appName,
                                branchName=branchName,
                                repoAddress=repoAddress,
                                chartAddress=chartAddress,
                                servicePort=servicePort,
                                containerPort=containerPort,
                                domain=domain,
                                chartVersion=chartVersion,
                                baseAppFlag=baseAppFlag,
#                                config=config.read(),
                                http=http)
    return JsonResponse({"success": 0})


def getImageConfig(requests):
    # image_id = requests.POST.get("image_id")
    # obj = ImageVersion.objects.get(id=image_id)

    #
    return JsonResponse({"config": "", "success": 0})


def getChartVersion(requests):
    projectName = requests.GET.get("project_name", "")
    appName = requests.GET.get("app_name", "")
    branchName = requests.GET.get("branch_name")
    if projectName and appName and branchName:
        if ChartVersion.objects.filter(projectName=projectName, appName=appName).exists():
            chart = ChartVersion.objects.filter(projectName=projectName, appName=appName)[0]
            a, b, c = chart.version.split(".")
            c = int(c) + 1
            chart.version = "%s.%s.%s" % (a, b, c)
            chart.save()
        else:
            chart = ChartVersion.objects.create(projectName=projectName, appName=appName, branchName=branchName)
    return HttpResponse(chart.version)


def getDataset(requests):
    dataset_id = requests.GET.get("dataset_id")
    obj = DataSet2.objects.filter(id=dataset_id).values()
    return JsonResponse({"dataset": obj[0], "harbor_url": settings.HARBOR_URL, "success": 0})


def getDeployLog(requests, *args, **kwargs):
    deploy_id = requests.GET.get("deploy_id")
    obj = Deployment.objects.get(id=deploy_id)
    f = open("%s/deploy_record.log" % (obj.deployDir,), "r")
    data = f.read()
    f.close()
    return HttpResponse(data)


def getDeployInfo(requests, *args, **kwargs):
    deploy_id = requests.POST.get("deploy_id")
    obj = Deployment.objects.get(id=deploy_id)
    images = obj.imageVersion.all()
    data = []
    for item in images:
        data.append(
            {"app_name": item.appName, "image_name": item.repoAddress, "env_name": obj.envName, "image_id": item.id})

    # if obj.commonApp:
    #     items = obj.commonApp.split(",")
    #     for item in items:
    #         data.append({"app_name": item, "image_name": "", "env_name": obj.envName,"image_id": u"commonApp"})

    return JsonResponse(data, safe=False)


def getDeployHistory(requests, *args, **kwargs):
    deployhistory_id = requests.GET.get("deployhistory_id")
    obj = DeployHistory.objects.get(id=deployhistory_id)
    f = open(obj.chartTmpDir, "r")
    data = f.read()
    f.close()
    return HttpResponse(data)


def installDataset(requests):
    dataset_id = requests.GET.get("dataset_id")
    obj = DataSet2.objects.get(id=dataset_id)
    tmp_dir = "/tmp/dataset_%s" % (obj.name)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
    chart_dir = os.path.join(settings.CHART_DIR, "mysql")
    cmd = "cp -r {chart_dir}/* {tmp_dir}".format(chart_dir=chart_dir, tmp_dir=tmp_dir)
    os.system(cmd)
    chart_t = os.path.join(tmp_dir, "Chart.template.yaml")
    chart = os.path.join(tmp_dir, "Chart.yaml")
    with open(chart_t, "r") as ct:
        chart_t_str = ct.read()
    with open(chart, "w") as c:
        c.write(chart_t_str.replace("{{image_name}}", obj.name))

    value_t = os.path.join(tmp_dir, "values.template.yaml")
    value = os.path.join(tmp_dir, "values.yaml")
    with open(value_t, "r") as ct:
        value_t_str = ct.read()
    with open(value, "w") as c:
        image, tag = obj.imageName.split(":")
        c.write(value_t_str.replace("{{image}}", image).replace("{{tag}}", tag))

    cmd = "cd {tmp_dir} && export KUBECONFIG={kube_config} && export HELM_HOME={helm_config} && helm push --username {username} --password {password} . http://{harbor_url}/chartrepo/dataset-image".format(
        tmp_dir=tmp_dir,
        kube_config=settings.KUBERNETES_CONFIG,
        helm_config=settings.HELM_HOME,
        username=settings.HARBOR_USER,
        password=settings.HARBOR_PASSWORD,
        harbor_url=settings.HARBOR_URL
    )
    os.system(cmd)
    obj.chartTmpDir = tmp_dir
    obj.flag = True
    obj.save()
    return JsonResponse({"success": 0, "tmp_dir": tmp_dir})

def oneClickUpgrade(requests):
    deploy_id = requests.POST.get("deploy_id")
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="环境 id {}一键更新模板~".format(
                                                              deploy_id))
    deploy = Deployment.objects.filter(id=deploy_id)
    if not deploy:
        return JsonResponse({"result": 200, "data":"环境不存在"})
    deploy = deploy[0]
    envT = EnvTemplateDetail.objects.filter(templateList_id=deploy.envTemplate_id)
    envTag = {}
    for env in envT:
        if env.appName == "evo-nginx":
            continue
        if env.imageTag:
            appName = env.appName
            imageTag = env.imageTag
            branch_Name = env.branchName
            baseapp = "{}:{}".format(appName, imageTag)
            ### 此处解决pipeline_id之前 应用打包同步导致Tag相同的情况
            images_test = ImageVersion.objects.filter(name=baseapp)
            if len(images_test) == 1:
                image = ImageVersion.objects.get(name=baseapp)
            else:
                image = ImageVersion.objects.filter(name=baseapp, branchName=branch_Name)
                if image:
                    image = image[0]
                else:
                    return JsonResponse({"result": 500, "msg": "环境模板中{}版本不正确或者不存在，请检查更换".format(baseapp)})
        else:
            appName = env.appName
            appProject = env.appProject
            branch_Name = env.branchName
            images = ImageVersion.objects.filter(appName=appName, projectName=appProject,
                                                 branchName=branch_Name).order_by("-createDate")
            if images:
                image=images[0]
            else:
                return JsonResponse({"result": 500, "msg": "环境模板中{}版本不正确或者不存在，请检查更换".format(appName)})
        envTag[env.appName]=image
    deployApp = deploy.imageVersion.all()
    deployAppName = [d.name.split(":")[0] for d in deployApp]
    oldId_dict = {}
    for env in envTag.keys():
        if env not in deployAppName:
            envTag.pop(env)
    for de in deployApp:
        _, tag = de.name.split(":")
        if envTag.has_key(de.appName):
            _, envT_tag = envTag[de.appName].name.split(":")
        else:
            continue
        if envT_tag == tag:
            envTag.pop(de.appName)
            continue
        oldId_dict[de.appName] = de.id
    return_msg = {}
    for app in envTag.keys():
        rsn = helper.updateChartNewNomem(namespace=deploy.envName, appName=app,
                           newImageName=envTag[app].repoAddress, old_imageId=oldId_dict[app])

        if rsn["rs"]:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="环境 id {}应用 {} 变更成功~".format(
                                                                      deploy_id,app))
            return_msg[app]="环境 id {}应用 {} 变更成功~".format(deploy_id,app)
        else:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="环境 id {}应用 {} 变更失败 reason-->{}".format(
                                                                      deploy_id, app, rsn["msg"]))
            return_msg[app] = "环境 id {}应用 {} 变更失败 ，reason-->{}".format(deploy_id, app, rsn["msg"])

    l = K8sApi()
    pod_names = l.get_pods_name_by_service(namespace=deploy.envName, name="nginx")
    if pod_names:
        l.delete_pod(name=pod_names[0], namespace=deploy.envName)
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="环境 id {}应用变更中nginx重启成功".format(
                                                              deploy_id))
    return JsonResponse({"result": 200, "msg": return_msg})


def imageUpgrade(requests):
    old_image_id = requests.POST.get("old_image_id")
    image_id = requests.POST.get("image_id")
    deploy_id = requests.POST.get("deploy_id")
    # image_config = requests.POST.get("image_config")
    memory = requests.POST.get("memory")
    # cpu = requests.POST.get("cpu")
    rt = patch_pod_SqlK8s(deploy_id)
    if not rt:
        return JsonResponse({"success": 1,"msg":"环境缺少应用请刷新页面检查后新增对应应用"})
    # 校验值
    if not old_image_id:
        return JsonResponse({"success": 1})
    elif not image_id:
        return JsonResponse({"success": 1})
    elif not deploy_id:
        return JsonResponse({"success": 1})

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="环境 id {}应用变更，客户端传参 old_image_id: {}, image_id: {}, memory: {} ".format(
                                                              deploy_id, old_image_id, image_id, memory))


    imageVersion = ImageVersion.objects.get(id=image_id)
    deploy = Deployment.objects.get(id=deploy_id)
    if "logstash" in deploy.commonApp:
        rcs_filebeat = True
    else:
        rcs_filebeat = False
    #rsn = helper.updateChartNew(namespace=deploy.envName, appName=imageVersion.appName, memory=memory,
    #                            newImageName=imageVersion.repoAddress)

    if memory:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="环境 id {}应用变更，客户端传参 memory: {}, 调用helper.updateChartNew ".format(
                                                                  deploy_id, memory))
        rsn = helper.updateChartNew(namespace=deploy.envName, appName=imageVersion.appName, memory=memory,
                                    newImageName=imageVersion.repoAddress, old_imageId=old_image_id, rcs_filebeat=rcs_filebeat)
    else:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="环境 id {}应用变更， 调用helper.updateChartNewNomem ".format(
                                                                  deploy_id))
        rsn = helper.updateChartNewNomem(namespace=deploy.envName, appName=imageVersion.appName,
                                    newImageName=imageVersion.repoAddress, old_imageId=old_image_id, rcs_filebeat=rcs_filebeat)

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="环境 id {}应用变更的结果是{}".format(
                                                              deploy_id, rsn))
    if rsn["rs"]:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="环境 id {}应用变更成功~".format(
                                                                  deploy_id))
        #if old_image_id:
        #    old_imageVersion = ImageVersion.objects.get(id=old_image_id)
        #    deploy.imageVersion.remove(old_imageVersion)
        #    deploy.save()
        #    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
        #                                                          fileName=os.path.basename(__file__),
        #                                                          func=sys._getframe(
        #                                                          ).f_code.co_name,
        #                                                          num=sys._getframe().f_lineno,
        #                                                          args="环境 id {}应用变更成功, 删除旧镜像版本{}数据成功~".format(
        #                                                              deploy_id, old_image_id))

        #deploy.imageVersion.add(imageVersion)
        #deploy.save()
        l = K8sApi()
        pod_names = l.get_pods_name_by_service(namespace=deploy.envName, name="nginx")
        if pod_names:
            l.delete_pod(name=pod_names[0], namespace=deploy.envName)
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="环境 id {}应用变更中nginx重启成功，返回success: 0".format(
                                                                  deploy_id, image_id))

        return JsonResponse({"success":0,"msg":"更新成功"})

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="环境 id {}应用变更失败，返回success: 1".format(
                                                              deploy_id))
    return JsonResponse({"success": 1,"msg":rsn["msg"]})

def dataSetDefault(request):
    env_id = request.POST['env_id']
    env = EnvTemplateList.objects.get(id=env_id)
    dataset = env.dataset_name
    if dataset:
        data = "tips:根据您选择的环境模板,我们推荐您使用  {}  数据集".format(dataset)
    else:
        data = ""
    return JsonResponse(data, safe=False)

def change_basic_debug(requests):
    namespace = requests.POST.get("namespace")
    rsn = helper.updateBasicDebug(namespace=namespace)
    if rsn:
        return JsonResponse({"success": 0})
    return JsonResponse({"success": 1})
def myDeploy(request):
    user = request.user.username
    return JsonResponse(user, safe=False)

def datasetUpgrade(requests):
    data = {"success": 0}
    dataset_id = requests.POST.get("dataset_id")
    deploy_id = requests.POST.get("deploy_id")
    dataset = DataSet2.objects.get(id=dataset_id)
    deploy = Deployment.objects.get(id=deploy_id)
    try:
        deploy.dataSet = dataset
        deploy.save()
        helper.deployDataset(deploy.id)
    except:
        data["success"] = 1
    return JsonResponse(data)


def imageDelete(requests):
    image_id = requests.POST.get("image_id")
    deploy_id = requests.POST.get("deploy_id")
    imageVersion = ImageVersion.objects.get(id=image_id)
    deploy = Deployment.objects.get(id=deploy_id)
    t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])
    chart_name = "{}-{}".format(deploy.envName,imageVersion.appName)
    try:
        _ = t.uninstall_release(release=chart_name)
    except Exception, e:
        return JsonResponse({"success": 1,"msg":"安装失败 reason-->{}".format(e)})
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="success delete image {}".format(chart_name))
    #rsn = helper.deployDeleteImageChart(deploy_id, imageVersion.id)
    deploy.imageVersion.remove(imageVersion)
    deploy.save()
    nginx_chart = "{}-{}".format(deploy.envName,"nginx")
    rs0 = t.uninstall_release(nginx_chart)
    if rs0:
        rs1 = deploy_nginx_chart.InstallNginxChartNew(deploy.envName)
        if rs1:
            return JsonResponse({"success": 0})
    return JsonResponse({"success": 1,"msg":"删除失败"})

def detailImageAddList1(requests):
    deploy_id = requests.POST.get("deploy_id")
    deploy = Deployment.objects.get(id=deploy_id)
    apps = EnvTemplateDetail.objects.filter(templateList_id=deploy.envTemplate_id)
    data = []
    nowApps = deploy.imageVersion.all()
    nowAppName = []
    for i in nowApps:
        nowAppName.append(i.appName)
    for app in apps:
        if app.appName == "evo-nginx":
            continue
        if app.appName not in nowAppName:
            if app.imageTag:
                data.append({
                    "app_name": app.appName,
                    "app_project": app.appProject,
                    "branch_name": app.branchName,
                    "image_tag": app.imageTag
                })
            else:
                baseimage = ImageVersion.objects.filter(projectName=app.appProject,appName=app.appName,
                                                        branchName=app.branchName).order_by('-createDate')[0]
                image_tag = baseimage.name.split(":")[-1]
                data.append({
                    "app_name": app.appName,
                    "app_project": app.appProject,
                    "branch_name": app.branchName,
                    "image_tag": image_tag
                })
    return JsonResponse(data, safe=False)

def detailImageAddList(requests):
    deploy_id = requests.GET.get("deploy_id")
    deploy = Deployment.objects.get(id=deploy_id)
    apps = EnvTemplateDetail.objects.filter(templateList_id=deploy.envTemplate_id)
    data = []
    nowApps = deploy.imageVersion.all()
    nowAppName = []
    for i in nowApps:
        nowAppName.append(i.appName)
    for app in apps:
        if app.appName == "evo-nginx":
            continue
        if app.appName not in nowAppName:
            if app.imageTag:
                data.append({
                    "app_name": app.appName,
                    "app_project": app.appProject,
                    "branch_name": app.branchName,
                    "image_tag": app.imageTag
                })
            else:
                baseimage = ImageVersion.objects.filter(projectName=app.appProject,appName=app.appName,
                                                        branchName=app.branchName).order_by('-createDate')[0]
                image_tag = baseimage.name.split(":")[-1]
                data.append({
                    "app_name": app.appName,
                    "app_project": app.appProject,
                    "branch_name": app.branchName,
                    "image_tag": image_tag
                })
    return JsonResponse(data, safe=False)

def detailImageAdd(requests):
    rebody = eval(requests.body.encode())
    images = rebody["data"]

    imageProject = requests.POST.get("app_project")
    branchName = requests.POST.get("branch_name")
    deploy_id = rebody["deploy_id"]
    deploy = Deployment.objects.get(id=deploy_id)
    msg=""
    for i in images:
        appName = i["app_name"]
        tag = i["image_tag"]
        imageName = "{}:{}".format(appName,tag)
        if not ImageVersion.objects.filter(name=imageName):
            msg+="{}安装失败,imagevesion不存在".format(imageName)
            continue
        image = ImageVersion.objects.filter(name=imageName)[0]
        repo = "/".join(image.chartAddress.split("/")[0:-1])
        namespace = deploy.envName
        chart_name = "{}-{}".format(namespace,appName)
        t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])
        if appName in settings.POD_PERSISTENCE_APP:
            chart = ChartBuilder(
                {'name': appName, 'source': {'type': 'directory', 'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT, "evo-baseapp-charts", appName)}})
        else:
            chart = ChartBuilder(
                {'name': appName, 'source': {'type': 'directory', 'location': "{}/helmCharts/{}/{}".format(settings.PROJECT_ROOT, "evo-baseapp", appName)}})
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="start to install   {} chart in namespace  {}, image is {}:{}".format(
                                                                  chart_name, namespace, appName, tag))
        dynamicEnv_dict = Deployment.objects.get(envName=namespace).dynamicEnv
        if dynamicEnv_dict:
            dynamicEnv_dict = eval(dynamicEnv_dict)
            if dynamicEnv_dict.has_key(appName):
                dynamicEnv = eval(dynamicEnv_dict[appName])
            else:
                dynamicEnv = {}
        else:
            dynamicEnv = {}
        try:
            if appName in settings.TCPSERVERMAP.keys():
                install_result = t.install_release(chart.get_helm_chart(), dry_run=False, namespace=namespace,
                                                   name=chart_name,
                                                   values={
                                                       "image": {
                                                           "repository": "{}/{}".format(repo, appName).replace("chartrepo/",
                                                                                                               "").replace(
                                                               "http://", ""),
                                                           "tag": tag
                                                       },
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
                                                       "dynamicEnv": dynamicEnv,
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
                                                           "tag": tag
                                                       },
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
                                                       "dynamicEnv": dynamicEnv,
                                                       "service": {
                                                           "type": "ClusterIP"
                                                       }
                                                   })

            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="result of  installed chart: {}".format(
                                                                      install_result))
            deploy.imageVersion.add(image)
            deploy.save()
            nginx_chart = "{}-{}".format(deploy.envName,"nginx")
            rs0 = t.uninstall_release(nginx_chart)
            if rs0:
                rs1 = deploy_nginx_chart.InstallNginxChartNew(deploy.envName)
                if rs1:
                    msg+="{}安装成功,".format(imageName)
                else:
                    msg+="{}安装失败,reason:{}".format(imageName,"nginx安装失败")
            else:
                msg+="{}安装失败,reason:{}".format(imageName,"nginx卸载失败")

        except Exception, e:
           # _ = t.uninstall_release(release=chart_name)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="failed to install helm chart {} in  namespace {}, reson is {}".format(
                                                                      chart_name, namespace, e))
            msg+="{}安装失败,reason:{}".format(imageName,e)
            continue
    result = 200
    for i in msg:
        if "失败" in msg:
            result=500
    return JsonResponse({"result": result,"msg":msg})


def alterDeployNum(requests):
    group_id = requests.POST.get("group_id")
    deployNum = requests.POST.get("deploy_num")
    group = FGroup.objects.get(id=group_id)
    if hasattr(group, "group_profile"):
        group.group_profile.maxDeployNum = deployNum
        group.group_profile.save()
    else:
        GroupProfile.objects.create(group=group, maxDeployNum=10)
    return JsonResponse({"success": 0})


def compareDeployNum(requests):
    if requests.user.is_superuser:
        return JsonResponse({"success": 0, "msg": ""})
    if hasattr(requests.user, "profile"):
        if requests.user.profile.currentDeployNum >= requests.user.profile.maxDeployNum:
            return JsonResponse(
                {"success": 1, "msg": "deploy env limit", "currentDeployNum": requests.user.profile.currentDeployNum})
    else:
        UserProfile.objects.create(user=requests.user, maxDeployNum=3)
    return JsonResponse({"success": 0, "msg": ""})

#def imageUpgradeGetBranch(requests):
#    image_id = requests.POST.get("image_id")
#    image = ImageVersion.objects.filter(id=image_id)
#    if image:
#        appName = image[0].name.split(":")[0]
#        branchs = ImageVersion.objects.filter(appName = appName)
#        Nbrachs = []
#        for branch in branchs:
#            Nbrachs.append(branch.branchName)
#        Nbrachs = list(set(Nbrachs))
#        data = {"branchs":Nbrachs}
#        return JsonResponse(data, safe=False)
def imageUpgradeGetBranch(requests):
    image_id = requests.POST.get("image_id")
    deploy_id = requests.POST.get("deploy_id")
    image = ImageVersion.objects.filter(id = image_id)
    deploy = Deployment.objects.get(id = deploy_id)
    if image:
        appName = image[0].name.split(":")[0]
        envT = EnvTemplateDetail.objects.filter(templateList_id=deploy.envTemplate_id,appName=appName)
        appProject = envT[0].appProject
        branchs = ImageVersion.objects.filter(appName = appName,projectName = appProject)
        Nbrachs = []
        for branch in branchs:
            Nbrachs.append(branch.branchName)
        Nbrachs = list(set(Nbrachs))
        data = {"branchs":Nbrachs}
        return JsonResponse(data, safe=False)

def imageUpgradeSelect(requests):
    image_id = requests.GET.get("image_id")
    branch = requests.GET.get("branch")
    imageVersion = ImageVersion.objects.get(id=image_id)

    project = imageVersion.projectName
    app = imageVersion.appName
    images = ImageVersion.objects.filter(projectName=project, appName=app, branchName=branch).order_by('-createDate')
    data = []
    for image in images:
        data.append({"chart_version": image.chartVersion, "image_name": image.name, "image_id": image.id,
                     "old_image_id": image_id})
    return JsonResponse(data, safe=False)

def get_namespace_time(requests):
    namespaces = requests.POST.get("namespaces")
    l=K8sApi()
    time=l.get_namespace_time(namespaces)
    if  time:
        return JsonResponse({"result":200,"msg":time})


def datasetUpgradeSelect(requests):
    dataset_id = requests.GET.get("dataset_id")
    dataset = DataSet.objects.get(id=dataset_id)
    project = dataset.project
    datasets = DataSet.objects.filter(project=project)
    data = []
    for dataset in datasets:
        data.append({"dataset_image_name": dataset.imageName, "dataset_name": dataset.name, "dataset_id": dataset.id})
    return JsonResponse(data, safe=False)

def get_last_pod_log(request):
    name = request.POST.get("name")
    namespace = request.POST.get("namespace")
    l = K8sApi()
    pod_name = l.get_pod_info(namespace=namespace, name=name)
    data = l.get_last_pod_log(namespace=namespace, pod_name=pod_name, name=name)
    return HttpResponse(data)

def get_pod_last_status(request):
    name = request.POST.get("name")
    namespace = request.POST.get("namespace")
    l = K8sApi()
    last_satus = l.get_pod_laststatus(namespace=namespace, name=name)
    return JsonResponse({"result":200,"msg":last_satus})


# def branchTrigger(requests,*args,**kwargs):
#     app_id  = requests.POST.get("app_id")
#     if "pk" in kwargs:
#         branch_id = kwargs["pk"]
#         branch = Branch.objects.get(id=branch_id)
#         app = App.objects.get(id=app_id)
#         gitlab_project = helper.get_evo_or_evoProjects_gitlab_project(branch.project.id, app.id)
#         cmd ='curl --request POST "{gitlab_api}api/v4/projects/{project_id}/trigger/pipeline?token={token}&ref={branch}"'\
#             .format(gitlab_api=settings.GITLAB_URL,project_id=gitlab_project['id'],token=app.triggerToken,branch=branch.name)
#         os.system(cmd)
#         pipeline_url ="{gitlab_api}software/{app_name}/pipelines".format(gitlab_api=settings.GITLAB_URL,app_name=app.slugName)
#
#         return JsonResponse({"url":pipeline_url})

def branchTrigger(requests, *args, **kwargs):
    app_id = requests.POST.get("app_id")
    app = App.objects.get(id=app_id)
    project_id = app.project_id
    lujin = app.slugName
    api = Api()
    if "pk" in kwargs:
        branch_id = kwargs["pk"]
        branch = api.get_branches(branch_id, lujin)
        gitlab_project = helper.get_evo_or_evoProjects_gitlab_project(project_id, app.id)
        cmd = 'curl --request POST "{gitlab_api}api/v4/projects/{project_id}/trigger/pipeline?token={token}&ref={branch}"' \
            .format(gitlab_api=settings.GITLAB_URL, project_id=gitlab_project['id'], token=app.triggerToken,
                    branch=branch.name)
        os.system(cmd)
        pipeline_url = "{gitlab_api}software/{app_name}/pipelines".format(gitlab_api=settings.GITLAB_URL,
                                                                          app_name=app.slugName)

        return JsonResponse({"url": pipeline_url})


def uploadAppTree(request):
    proBranch = request.POST.get("pro_branch")
    appName = request.POST.get("app_name")
    jsonData = request.POST.get("json_data")
    if appName and jsonData and proBranch:
        if AppTree.objects.filter(appName=appName, proBranch=proBranch).exists():
            obj = AppTree.objects.filter(appName=appName, proBranch=proBranch)[0]
            obj.jsonData = jsonData
            obj.save()
        else:
            AppTree.objects.create(appName=appName, proBranch=proBranch, jsonData=jsonData)
        return JsonResponse({"success": 0}, safe=False)
    return JsonResponse({"success": 1}, safe=False)


def getBaseAppTree(request):
    git = Api()
    group = git.search_group("evo")
    group = git.get_group(group.id)
    git.get_group_tree(group)
    data = git.baseapp_tree
    return JsonResponse({"data": data, "success": 0}, safe=False)
    # return JsonResponse({"data":'[{"text": "evo-rcs", "state": {"selected": "true"}, "id": "evo-rcs", "parent": "#"}, {"text": "agv-simulation", "state": {"selected": "true"}, "id": "agv-simulation", "parent": "evo-rcs"}, {"text": "agv-simulation-communicator", "state": {"selected": "true"}, "id": "agv-simulation-communicator", "parent": "agv-simulation"}, {"text": "agv-simulation-slam", "state": {"selected": "true"}, "id": "agv-simulation-slam", "parent": "agv-simulation"}, {"text": "rcs-boot", "state": {"selected": "true"}, "id": "rcs-boot", "parent": "evo-rcs"}, {"text": "rcs-boot-cau", "state": {"selected": "true"}, "id": "rcs-boot-cau", "parent": "rcs-boot"}, {"text": "rcs-boot-cmd", "state": {"selected": "true"}, "id": "rcs-boot-cmd", "parent": "rcs-boot"}, {"text": "rcs-boot-job", "state": {"selected": "true"}, "id": "rcs-boot-job", "parent": "rcs-boot"}, {"text": "rcs-command", "state": {"selected": "true"}, "id": "rcs-command", "parent": "evo-rcs"}, {"text": "rcs-command-client", "state": {"selected": "true"}, "id": "rcs-command-client", "parent": "rcs-command"}, {"text": "rcs-command-agv", "state": {"selected": "true"}, "id": "rcs-command-agv", "parent": "rcs-command"}, {"text": "rcs-command-agv-core", "state": {"selected": "true"}, "id": "rcs-command-agv-core", "parent": "rcs-command-agv"}, {"text": "rcs-command-agv-frame", "state": {"selected": "true"}, "id": "rcs-command-agv-frame", "parent": "rcs-command-agv"}, {"text": "rcs-command-communication", "state": {"selected": "true"}, "id": "rcs-command-communication", "parent": "rcs-command-agv"}, {"text": "rcs-command-agv-pd", "state": {"selected": "true"}, "id": "rcs-command-agv-pd", "parent": "rcs-command-agv"}, {"text": "rcs-command-cmds-base", "state": {"selected": "true"}, "id": "rcs-command-cmds-base", "parent": "rcs-command-agv"}, {"text": "rcs-command-communication-protocol", "state": {"selected": "true"}, "id": "rcs-command-communication-protocol", "parent": "rcs-command-agv"}, {"text": "rcs-command-carrier", "state": {"selected": "true"}, "id": "rcs-command-carrier", "parent": "rcs-command"}, {"text": "rcs-command-cmds-carrier", "state": {"selected": "true"}, "id": "rcs-command-cmds-carrier", "parent": "rcs-command-carrier"}, {"text": "rcs-command-core-carrier", "state": {"selected": "true"}, "id": "rcs-command-core-carrier", "parent": "rcs-command-carrier"}, {"text": "rcs-command-pd-carrier", "state": {"selected": "true"}, "id": "rcs-command-pd-carrier", "parent": "rcs-command-carrier"}, {"text": "rcs-command-restful-carrier", "state": {"selected": "true"}, "id": "rcs-command-restful-carrier", "parent": "rcs-command-carrier"}, {"text": "rcs-command-workbin", "state": {"selected": "true"}, "id": "rcs-command-workbin", "parent": "rcs-command"}, {"text": "rcs-command-cmds-workbin", "state": {"selected": "true"}, "id": "rcs-command-cmds-workbin", "parent": "rcs-command-workbin"}, {"text": "rcs-command-core-workbin", "state": {"selected": "true"}, "id": "rcs-command-core-workbin", "parent": "rcs-command-workbin"}, {"text": "rcs-command-pd-workbin", "state": {"selected": "true"}, "id": "rcs-command-pd-workbin", "parent": "rcs-command-workbin"}, {"text": "rcs-command-restful-workbin", "state": {"selected": "true"}, "id": "rcs-command-restful-workbin", "parent": "rcs-command-workbin"}, {"text": "rcs-command-slam", "state": {"selected": "true"}, "id": "rcs-command-slam", "parent": "rcs-command"}, {"text": "rcs-command-core-slam", "state": {"selected": "true"}, "id": "rcs-command-core-slam", "parent": "rcs-command-slam"}, {"text": "rcs-command-pd-slam", "state": {"selected": "true"}, "id": "rcs-command-pd-slam", "parent": "rcs-command-slam"}, {"text": "rcs-command-cmds-slam", "state": {"selected": "true"}, "id": "rcs-command-cmds-slam", "parent": "rcs-command-slam"}, {"text": "rcs-action", "state": {"selected": "true"}, "id": "rcs-action", "parent": "evo-rcs"}, {"text": "rcs-action-carrier", "state": {"selected": "true"}, "id": "rcs-action-carrier", "parent": "rcs-action"}, {"text": "rcs-action-carrier-ohs", "state": {"selected": "true"}, "id": "rcs-action-carrier-ohs", "parent": "rcs-action-carrier"}, {"text": "rcs-action-carrier-ohs-restful", "state": {"selected": "true"}, "id": "rcs-action-carrier-ohs-restful", "parent": "rcs-action-carrier"}, {"text": "rcs-action-carrier-core", "state": {"selected": "true"}, "id": "rcs-action-carrier-core", "parent": "rcs-action-carrier"}, {"text": "rcs-action-carrier-sdk-spring", "state": {"selected": "true"}, "id": "rcs-action-carrier-sdk-spring", "parent": "rcs-action-carrier"}, {"text": "rcs-action-carrier-sdk-restful", "state": {"selected": "true"}, "id": "rcs-action-carrier-sdk-restful", "parent": "rcs-action-carrier"}, {"text": "rcs-action-carrier-acl", "state": {"selected": "true"}, "id": "rcs-action-carrier-acl", "parent": "rcs-action-carrier"}, {"text": "rcs-action-carrier-acl-impl", "state": {"selected": "true"}, "id": "rcs-action-carrier-acl-impl", "parent": "rcs-action-carrier"}, {"text": "rcs-action-deliver", "state": {"selected": "true"}, "id": "rcs-action-deliver", "parent": "rcs-action"}, {"text": "rcs-action-deliver-ohs", "state": {"selected": "true"}, "id": "rcs-action-deliver-ohs", "parent": "rcs-action-deliver"}, {"text": "rcs-action-deliver-core", "state": {"selected": "true"}, "id": "rcs-action-deliver-core", "parent": "rcs-action-deliver"}, {"text": "rcs-action-deliver-ohs-restful", "state": {"selected": "true"}, "id": "rcs-action-deliver-ohs-restful", "parent": "rcs-action-deliver"}, {"text": "rcs-action-agv", "state": {"selected": "true"}, "id": "rcs-action-agv", "parent": "rcs-action"}, {"text": "rcs-action-agv-core", "state": {"selected": "true"}, "id": "rcs-action-agv-core", "parent": "rcs-action-agv"}, {"text": "rcs-action-agv-ohs", "state": {"selected": "true"}, "id": "rcs-action-agv-ohs", "parent": "rcs-action-agv"}, {"text": "rcs-action-agv-acl", "state": {"selected": "true"}, "id": "rcs-action-agv-acl", "parent": "rcs-action-agv"}, {"text": "rcs-action-agv-acl-impl", "state": {"selected": "true"}, "id": "rcs-action-agv-acl-impl", "parent": "rcs-action-agv"}, {"text": "rcs-action-agv-script", "state": {"selected": "true"}, "id": "rcs-action-agv-script", "parent": "rcs-action-agv"}, {"text": "rcs-action-spring", "state": {"selected": "true"}, "id": "rcs-action-spring", "parent": "rcs-action-agv"}, {"text": "rcs-action-workbin", "state": {"selected": "true"}, "id": "rcs-action-workbin", "parent": "rcs-action"}, {"text": "rcs-action-workbin-ohs-restful", "state": {"selected": "true"}, "id": "rcs-action-workbin-ohs-restful", "parent": "rcs-action-workbin"}, {"text": "rcs-action-workbin-ohs", "state": {"selected": "true"}, "id": "rcs-action-workbin-ohs", "parent": "rcs-action-workbin"}, {"text": "rcs-action-workbin-core", "state": {"selected": "true"}, "id": "rcs-action-workbin-core", "parent": "rcs-action-workbin"}, {"text": "rcs-action-workbin-acl", "state": {"selected": "true"}, "id": "rcs-action-workbin-acl", "parent": "rcs-action-workbin"}, {"text": "rcs-action-workbin-acl-impl", "state": {"selected": "true"}, "id": "rcs-action-workbin-acl-impl", "parent": "rcs-action-workbin"}, {"text": "rcs-action-slam", "state": {"selected": "true"}, "id": "rcs-action-slam", "parent": "rcs-action"}, {"text": "rcs-action-slam-core", "state": {"selected": "true"}, "id": "rcs-action-slam-core", "parent": "rcs-action-slam"}, {"text": "rcs-action-slam-acl", "state": {"selected": "true"}, "id": "rcs-action-slam-acl", "parent": "rcs-action-slam"}, {"text": "rcs-action-slam-acl-impl", "state": {"selected": "true"}, "id": "rcs-action-slam-acl-impl", "parent": "rcs-action-slam"}, {"text": "rcs-action-slam-ohs", "state": {"selected": "true"}, "id": "rcs-action-slam-ohs", "parent": "rcs-action-slam"}, {"text": "rcs-job", "state": {"selected": "true"}, "id": "rcs-job", "parent": "evo-rcs"}, {"text": "rcs-job-agv", "state": {"selected": "true"}, "id": "rcs-job-agv", "parent": "rcs-job"}, {"text": "rcs-job-agv-core", "state": {"selected": "true"}, "id": "rcs-job-agv-core", "parent": "rcs-job-agv"}, {"text": "rcs-job-agv-base", "state": {"selected": "true"}, "id": "rcs-job-agv-base", "parent": "rcs-job-agv"}, {"text": "rcs-job-agv-carrier", "state": {"selected": "true"}, "id": "rcs-job-agv-carrier", "parent": "rcs-job"}, {"text": "rcs-job-agv-carrier-core", "state": {"selected": "true"}, "id": "rcs-job-agv-carrier-core", "parent": "rcs-job-agv-carrier"}, {"text": "rcs-job-agv-carrier-sdk", "state": {"selected": "true"}, "id": "rcs-job-agv-carrier-sdk", "parent": "rcs-job-agv-carrier"}, {"text": "rcs-job-carrier-restful", "state": {"selected": "true"}, "id": "rcs-job-carrier-restful", "parent": "rcs-job-agv-carrier"}, {"text": "rcs-job-agv-workbin", "state": {"selected": "true"}, "id": "rcs-job-agv-workbin", "parent": "rcs-job"}, {"text": "rcs-job-agv-workbin-sdk", "state": {"selected": "true"}, "id": "rcs-job-agv-workbin-sdk", "parent": "rcs-job-agv-workbin"}, {"text": "rcs-job-agv-workbin-core", "state": {"selected": "true"}, "id": "rcs-job-agv-workbin-core", "parent": "rcs-job-agv-workbin"}, {"text": "rcs-job-agv-workbin-restful", "state": {"selected": "true"}, "id": "rcs-job-agv-workbin-restful", "parent": "rcs-job-agv-workbin"}, {"text": "rcs-job-agv-slam", "state": {"selected": "true"}, "id": "rcs-job-agv-slam", "parent": "rcs-job"}, {"text": "rcs-job-agv-slam-sdk", "state": {"selected": "true"}, "id": "rcs-job-agv-slam-sdk", "parent": "rcs-job-agv-slam"}, {"text": "rcs-job-agv-slam-core", "state": {"selected": "true"}, "id": "rcs-job-agv-slam-core", "parent": "rcs-job-agv-slam"}, {"text": "rcs-job-agv-slam-restful", "state": {"selected": "true"}, "id": "rcs-job-agv-slam-restful", "parent": "rcs-job-agv-slam"}, {"text": "rcs-data", "state": {"selected": "true"}, "id": "rcs-data", "parent": "evo-rcs"}, {"text": "rcs-data-biz", "state": {"selected": "true"}, "id": "rcs-data-biz", "parent": "rcs-data"}, {"text": "rcs-data-client", "state": {"selected": "true"}, "id": "rcs-data-client", "parent": "rcs-data"}, {"text": "rcs-data-restful", "state": {"selected": "true"}, "id": "rcs-data-restful", "parent": "rcs-data"}, {"text": "rcs-data-store", "state": {"selected": "true"}, "id": "rcs-data-store", "parent": "rcs-data"}, {"text": "rcs-data-ohs", "state": {"selected": "true"}, "id": "rcs-data-ohs", "parent": "rcs-data"}, {"text": "rcs-traffic", "state": {"selected": "true"}, "id": "rcs-traffic", "parent": "evo-rcs"}, {"text": "rcs-traffic-manager", "state": {"selected": "true"}, "id": "rcs-traffic-manager", "parent": "rcs-traffic"}, {"text": "rcs-traffic-manager-client", "state": {"selected": "true"}, "id": "rcs-traffic-manager-client", "parent": "rcs-traffic-manager"}, {"text": "rcs-traffic-manager-biz", "state": {"selected": "true"}, "id": "rcs-traffic-manager-biz", "parent": "rcs-traffic-manager"}, {"text": "rcs-traffic-common", "state": {"selected": "true"}, "id": "rcs-traffic-common", "parent": "rcs-traffic-manager"}, {"text": "rcs-traffic-cache", "state": {"selected": "true"}, "id": "rcs-traffic-cache", "parent": "rcs-traffic"}, {"text": "rcs-traffic-cache-client", "state": {"selected": "true"}, "id": "rcs-traffic-cache-client", "parent": "rcs-traffic-cache"}, {"text": "rcs-traffic-cache-biz", "state": {"selected": "true"}, "id": "rcs-traffic-cache-biz", "parent": "rcs-traffic-cache"}, {"text": "rcs-common", "state": {"selected": "true"}, "id": "rcs-common", "parent": "evo-rcs"}, {"text": "rcs-common-agvmodel", "state": {"selected": "true"}, "id": "rcs-common-agvmodel", "parent": "rcs-common"}, {"text": "rcs-common-mapmodel", "state": {"selected": "true"}, "id": "rcs-common-mapmodel", "parent": "rcs-common"}, {"text": "rcs-common-utils", "state": {"selected": "true"}, "id": "rcs-common-utils", "parent": "rcs-common"}, {"text": "rcs-common-akka-spring", "state": {"selected": "true"}, "id": "rcs-common-akka-spring", "parent": "rcs-common"}, {"text": "rcs-common-eventbus", "state": {"selected": "true"}, "id": "rcs-common-eventbus", "parent": "rcs-common"}, {"text": "rcs-common-eventbus-akka", "state": {"selected": "true"}, "id": "rcs-common-eventbus-akka", "parent": "rcs-common"}, {"text": "rcs-common-akka", "state": {"selected": "true"}, "id": "rcs-common-akka", "parent": "rcs-common"}, {"text": "rcs-common-message-service", "state": {"selected": "true"}, "id": "rcs-common-message-service", "parent": "rcs-common"}, {"text": "rcs-controller", "state": {"selected": "true"}, "id": "rcs-controller", "parent": "evo-rcs"}, {"text": "rcs-controller-carrier", "state": {"selected": "true"}, "id": "rcs-controller-carrier", "parent": "rcs-controller"}, {"text": "rcs-controller-carrier-base", "state": {"selected": "true"}, "id": "rcs-controller-carrier-base", "parent": "rcs-controller-carrier"}, {"text": "rcs-controller-carrier-core", "state": {"selected": "true"}, "id": "rcs-controller-carrier-core", "parent": "rcs-controller-carrier"}, {"text": "rcs-controller-agv", "state": {"selected": "true"}, "id": "rcs-controller-agv", "parent": "rcs-controller"}, {"text": "rcs-controller-core", "state": {"selected": "true"}, "id": "rcs-controller-core", "parent": "rcs-controller-agv"}, {"text": "rcs-controller-api", "state": {"selected": "true"}, "id": "rcs-controller-api", "parent": "rcs-controller-agv"}, {"text": "rcs-controller-workbin", "state": {"selected": "true"}, "id": "rcs-controller-workbin", "parent": "rcs-controller"}, {"text": "rcs-controller-workbin-core", "state": {"selected": "true"}, "id": "rcs-controller-workbin-core", "parent": "rcs-controller-workbin"}, {"text": "rcs-controller-slam", "state": {"selected": "true"}, "id": "rcs-controller-slam", "parent": "rcs-controller"}, {"text": "rcs-controller-slam-core", "state": {"selected": "true"}, "id": "rcs-controller-slam-core", "parent": "rcs-controller-slam"}, {"text": "hermes", "state": {"selected": "true"}, "id": "hermes", "parent": "evo-rcs"}, {"text": "hermes-core", "state": {"selected": "true"}, "id": "hermes-core", "parent": "hermes"}, {"text": "hermes-client", "state": {"selected": "true"}, "id": "hermes-client", "parent": "hermes"}, {"text": "hermes-server", "state": {"selected": "true"}, "id": "hermes-server", "parent": "hermes"}, {"text": "rcs-sdk", "state": {"selected": "true"}, "id": "rcs-sdk", "parent": "evo-rcs"}, {"text": "rcs-sdk-client", "state": {"selected": "true"}, "id": "rcs-sdk-client", "parent": "rcs-sdk"}, {"text": "rcs-sdk-pojo", "state": {"selected": "true"}, "id": "rcs-sdk-pojo", "parent": "rcs-sdk"}, {"text": "rcs-charge-manager", "state": {"selected": "true"}, "id": "rcs-charge-manager", "parent": "evo-rcs"}, {"text": "rcs-exception-manager", "state": {"selected": "true"}, "id": "rcs-exception-manager", "parent": "evo-rcs"}, {"text": "agv-slam-runner", "state": {"selected": "true"}, "id": "agv-slam-runner", "parent": "evo-rcs"}]',"success":0}, safe=False)


def get_pod_log(request):
    name = request.POST.get("name")
    namespace = request.POST.get("namespace")
    l = K8sApi()
    pod_name = l.get_pod_info(namespace=namespace, name=name)
    data = l.get_pod_log(namespace=namespace, name=pod_name)
    return HttpResponse(data)


def get_console_url(request):
    name = request.POST.get("name")
    namespace = request.POST.get("namespace")
    #l = K8sApi()
    #pod_name = l.get_pod_info(namespace=namespace, name=name)
    #url = "%s/%s/%s" % (settings.CONSOLE_URL, pod_name, namespace)
    #data = {"success": 0, "url": url}
    #return JsonResponse(data)
    l = K8sApi()
    webshellPort = []
    try:
        pod_name = l.get_pod_info(namespace=namespace, name=name)
        webshellPort = l.get_service_port(namespace="devops", name="webshell")
    except Exception as e:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="Exception when  get_pod_info by appName {} in namespace {} : {}".format(name,namespace,e))
        return JsonResponse({"success": 1})

    if webshellPort:
        port = webshellPort[0].split(':')[1]
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="get webshell service out port is {}".format(port))
        container_name = name
        if name == "nginx":
            container_name = "nginx-evo"
        if name == "mysql":
            container_name = "{}-mysql-mysql".format(namespace)
        url = 'http://api.devops.flashhold.com:{}/terminal?context=kubernetes-admin%40kubernetes&namespace={}&pod={}&container={}'.format(port, namespace, pod_name, container_name)
        return JsonResponse({"success": 0, "url": url})
    else:
        return JsonResponse({"success": 1})


def get_dataset_list(request):
    deploy_id = request.POST.get("deploy_id")
    deploy = Deployment.objects.get(id=deploy_id)
    datasets = DataSet2.objects.filter(project=deploy.project)
    data = []
    for dataset in datasets:
        data.append({"dataset_id": dataset.id, "dataset_name": dataset.name})
    return JsonResponse(data, safe=False)


def delete_pod(request):
    name = request.POST.get("name")
    namespace = request.POST.get("namespace")
    l = K8sApi()
    pod_name = l.get_pod_name(namespace=namespace, name=name)
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="result for  get pod_name in namespace {} for app {}  by get_pods_name_by_service is {} ".format(
                                                              namespace, name, pod_name))
    if pod_name:
        rsn = l.delete_pod(name=pod_name, namespace=namespace)
        if not rsn["rsn"]:
            return JsonResponse({"success": 0}, safe=False)
        else:
            return JsonResponse({"success": 1}, safe=False)
    else:
        return JsonResponse({"success": 1}, safe=False)


# def get_project_branch(request):
#     project_id = request.POST.get("project_id",None)
#     app_id = request.POST.get("app_id")
#     ###得到了id根据id获取路径slugName
#     app = App.objects.get(id=app_id)
#     if not project_id:
#         project = Project.objects.get(name="evo")
#     else:
#         project = Project.objects.get(id=project_id)
#     branchs = Branch.objects.filter(Q(project=project),Q(singleApp=app.name)|Q(projectFlag=1))
#     if not branchs:
#         project = Project.objects.get(id=project_id)
#         Branch.objects.create(name="master",
#                               type="master",
#                               version="",
#                               project=project,
#                               desc="master",
#                               baseBranch="master",
#                               projectFlag=True)
#         branchs = Branch.objects.filter(Q(project__id=project), Q(singleApp=app.name) | Q(projectFlag=1))
#     data = []
#     for branch in branchs:
#         data.append({"branch_id": branch.id, "branch_name": branch.name})
#     return JsonResponse(data, safe=False)
def get_project_branch(request):
    project_id = request.POST.get("project_id", None)
    app_id = request.POST.get("app_id")
    ###得到了id根据id获取路径slugName
    api = Api()
    app = App.objects.get(id=app_id)
    lujing = app.slugName
    branchs = api.list_project_branch(lujing)
    data = []
    for branch in branchs:
        data.append({"branch_id": branch.get_id(), "branch_name": branch.name})

    return JsonResponse(data, safe=False)


def package_deploy(request):
    ###根据提交的deployment_id, 获取该deployment的project信息，原"包名"即项目名称，原"版本"即该项目当天发布总次数的递增序列号
    deploy_id = request.POST.get("deploy_id")
    print("package_deploy deploy_id: {}".format(deploy_id))
    deploy = Deployment.objects.get(id=deploy_id)
    project_name = Project.objects.get(id=deploy.project.id).name
    package_name = project_name
    print("package_deploy package_name: {}".format(package_name))
    print("package_deploy deploy.project.id: {}".format(deploy.project.id))
    # 从打包服务器上遍历该项目的ZIP包总数
    ###把压缩包上传到22.30的目录
    tar_dir = os.path.join(settings.TAR_DIR, package_name)
    comd = 'ssh root@{tar_host} "ls {tar_dir}| grep {tar_time} | wc -l"'.format(tar_host=settings.TAR_HOST,
                                                                                tar_dir=tar_dir,
                                                                                tar_time=datetime.datetime.now().strftime(
                                                                                    "%y%m%d"))
    print("从打包服务器上遍历该项目当天的zip包总数: {}".format(comd))
    count = os.popen(comd).read()
    print("package_deploy count: {}".format(count))
    if int(count) < 10:
        version = "{}0{}".format(datetime.datetime.now().strftime("%y%m%d"), int(count) + 1)
    else:
        version = "{}{}".format(datetime.datetime.now().strftime("%y%m%d"), int(count) + 1)

    print("package_deploy version: {}".format(version))

    deploy_dir = "/devops/%s" % (deploy.envName)
    if not os.path.exists(deploy_dir):
        os.mkdir(deploy_dir)

    os.system("rm -rf %s/*" % (deploy_dir))

    images = deploy.imageVersion.all()
    pattern = []
    images_name = [image.name for image in images]
    ###根据镜像来更改docker-compose文件 dcf
    lujin = deploy.project.slugName
    f_content = helper.build_docker_compose(images_name, lujin)
    dc = "%s/docker-compose.yml" % deploy_dir
    dcf = open(dc, "w")
    dcf.write(f_content)
    dcf.close()

    ###根据镜像先找出evo-base的那些镜像 得到镜像列表fs ，并把它们拷贝到项目目录
    for image in images:
        # num = image.repoAddress.split(":")[-1].split("-")[-1]
        # num = "*%s" % num
        pattern.append(image.name.strip())
    pattern = "|".join(pattern)
    cmd = 'ls /devops/evo-baseapp|grep -E "{pattern}"'.format(pattern=pattern)
    fs = os.popen(cmd).read().split("\n")
    for f in fs:
        if not f: continue
        cmd = "cp -r /devops/evo-baseapp/%s %s" % (f, deploy_dir)
        os.system(cmd)

    ###找到project.name的镜像也移动到项目目录（不知道project.name）
    cmd = 'ls /devops/{project}|grep -E "{pattern}"'.format(project=deploy.project.name, pattern=pattern)
    fs = os.popen(cmd).read().split("\n")
    for f in fs:
        if not f: continue
        cmd = "cp -r /devops/%s/%s %s" % (deploy.project.name, f, deploy_dir)
        os.system(cmd)

    cmd = "cp -r %s %s" % (dc, deploy_dir)  ##这里貌似有问题 自己复制自己
    os.system(cmd)
    offline_package_file = "%s-%s-offline.zip" % (package_name, version)
    on_package_file = "%s-%s-online.zip" % (package_name, version)
    ##在线打包compose 离线打包镜像
    cmd = 'cd {deploy_dir} && zip -r -q -o {project} *'.format(deploy_dir=deploy_dir, project=offline_package_file)
    os.system(cmd)

    cmd = 'cd {deploy_dir} && zip -r -q -o {project} docker-compose.yml'.format(deploy_dir=deploy_dir,
                                                                                project=on_package_file)
    os.system(cmd)

    deploy.zipPath = "/{deploy_dir}/{project}.zip".format(deploy_dir=deploy_dir, project=offline_package_file)
    deploy.save()

    cmd = 'ssh root@{tar_host} "mkdir -p {tar_dir}"'.format(tar_host=settings.TAR_HOST, tar_dir=tar_dir)
    os.system(cmd)

    cmd = 'scp -r {f} root@{tar_host}:{tar_dir}'.format(f=os.path.join(deploy_dir, offline_package_file),
                                                        tar_host=settings.TAR_HOST, tar_dir=tar_dir)
    os.system(cmd)

    cmd = 'scp -r {f} root@{tar_host}:{tar_dir}'.format(f=os.path.join(deploy_dir, on_package_file),
                                                        tar_host=settings.TAR_HOST, tar_dir=tar_dir)
    os.system(cmd)

    return JsonResponse({'zipfile': deploy.zipPath, "status": 0})


def get_project_monitor_resource(request):
    project_id = request.POST.get("project_id")
    l = MonitorApi()
    memorys = l.get_namespace_memory()
    cpus = l.get_namespace_cpu()

    deploys = Deployment.objects.filter(project__id=project_id).values()
    data = {}
    if check_url(url="prometheus.k8s.flashhold.com"):
        for deploy in deploys:
            envName = deploy["envName"]
            data[envName] = {"memory": "", "cpu": ""}
            if memorys and cpus and envName in memorys.keys() and envName in cpus.keys():
                data[envName]["memory"] = "%.1fMiB" % (long(memorys[deploy["envName"]]) / (1024 * 1024))
                data[envName]["cpu"] = "%.2f" % float(cpus[deploy["envName"]])
            else:
                data[envName]["memory"] = None
                data[envName]["cpu"] = None
    else:
        for deploy in deploys:
            envName = deploy["envName"]
            data[envName] = {"memory": None, "cpu": None}
    return JsonResponse(data, safe=False)

#        envName = deploy["envName"]
#        data[envName] = {"memory": "", "cpu": ""}
#        data[envName]["memory"] = None
#        data[envName]["cpu"] = None
#    return JsonResponse(data, safe=False)


def get_pod_monitor_resource(request):
    app_names = request.POST.get("app_names")
    deploy_name = request.POST.get("deploy_name")
    l = MonitorApi()
    k8s = K8sApi()
    pod_map = {}
    app_names = app_names.split(",")
    for item in app_names:
        try:
            pod_name = k8s.get_pod_info(namespace=deploy_name, name=item)
            pod_map[item] = pod_name
        except:
            continue
    memorys = l.get_pods_memory(namespace=deploy_name)
    cpus = l.get_pods_cpu(namespace=deploy_name)
    data = {}
    if check_url(url="prometheus.k8s.flashhold.com"):
        for item in app_names:
            data[item] = {"memory": "", "cpu": "", "restart_count": "", "reason": ""}
            try:
                data[item]["memory"] = "%.1fMiB" % (long(memorys[pod_map[item]]) / (1024 * 1024))
                data[item]["cpu"] = "%.2f" % float(cpus[pod_map[item]])
                restart_count, reason = k8s.get_pod_restart_count_and_reason(namespace=deploy_name, name=pod_map[item])
                data[item]["restart_count"] = restart_count
                data[item]["reason"] = reason
            except:
                data[item]["memory"] = None
                data[item]["cpu"] = None
                data[item]["restart_count"] = None
                data[item]["reason"] = None
    else:
        for item in app_names:
            data[item] = {"memory": None, "cpu": None, "restart_count": None, "reason": None}
    return JsonResponse(data, safe=False)


def getHelmGitlabTagNameNew(request):
    ci_pipeline_id = request.GET.get("ci_pipeline_id")
    print("getHelmGitlabTagNameNew ci_pipeline_id{}".format(ci_pipeline_id))
    if not ci_pipeline_id:
        return getHelmGitlabTagName(request)
    else:
        tag_name = TagNum.objects.get(pipeline_id=int(ci_pipeline_id)).tag_name
        print("getHelmGitlabTagNameNew obj.tag_name: {}".format(tag_name))
        return HttpResponse(tag_name)


def getHelmGitlabTagName(request):
    gitlab_project_id = request.GET.get("gitlab_project_id")
    dateMonth = datetime.datetime.now().strftime("%y%m%d")
    obj = TagNum.objects.filter(dateMonth=dateMonth, project_id=int(gitlab_project_id)).order_by("-num")[0]
    return HttpResponse(obj.tag_name)


def getGitlabTagNameNew(request):
    ci_pipeline_id = request.GET.get("ci_pipeline_id")
    if not ci_pipeline_id:
        return getGitlabTagName(request)
    else:
        branch_name = request.GET.get("branch_name")
        gitlab_project_id = request.GET.get("gitlab_project_id")
        company_id = request.GET.get("company")
        dateMonth = datetime.datetime.now().strftime("%y%m%d")
        print("getGitlabTagNameNew get args: {},{},{},{}".format(branch_name,gitlab_project_id,company_id,dateMonth))
        obj = None
        if not TagNum.objects.filter(dateMonth=dateMonth, project_id=int(gitlab_project_id), branch_name=branch_name):
            obj = TagNum.objects.create(dateMonth=dateMonth, project_id=int(gitlab_project_id),
                                        pipeline_id=ci_pipeline_id, branch_name=branch_name)
            print("getGitlabTagNameNew create obj1: {},{},{},{}".format(branch_name, gitlab_project_id, ci_pipeline_id,
                                                                       dateMonth))
        else:
            obj_old = TagNum.objects.filter(dateMonth=dateMonth, project_id=int(gitlab_project_id),
                                            branch_name=branch_name).order_by(
                "-num").values("num")
            coun = obj_old.values("num")[0]["num"]
            print("getGitlabTagNameNew coun:  ", coun)
            obj = TagNum.objects.create(dateMonth=dateMonth, project_id=int(gitlab_project_id),
                                        pipeline_id=ci_pipeline_id, branch_name=branch_name)
            print("getGitlabTagNameNew create obj2: {},{},{},{}".format(branch_name, gitlab_project_id, ci_pipeline_id,
                                                                     dateMonth))
            obj.num = coun + 1
            obj.save()
            print(
                "getGitlabTagNameNew obj.save() successed ~ ", obj.project_id, obj.pipeline_id, obj.dateMonth, obj.num,
                obj.tag_name, obj.branch_name)
        num = "%s%02d" % (dateMonth, obj.num)

        git = Api()
        tags = git.get_project_tag(gitlab_project_id)
        app_name = git.get_project(gitlab_project_id)['name']

        tag_name = branch_name + "-" + num
        if company_id is None:
            if branch_name == "master":
                tags = [re.match(r'^\d\.\d\.\d$', tag) for tag in tags if re.match(r'^\d\.\d\.\d$', tag) is not None]
                # tags[0] is latest
                if tags:
                    tag_name = "%s-%s" % (tags[0].group(), num)
                else:
                    # git.create_project_tag(project_id=gitlab_project_id, tag_name=tag_name, ref="master")
                    tag_name = "2.2.0-%s" % (num)
            if branch_name.find("hotfix") != -1:
                hotfix_version = ".".join(branch_name.split("-")[1:])
                tag_name = "%shf-%s" % (hotfix_version, num)
            if branch_name.find("release") != -1:
                tag_name = branch_name + "-" + num
            if branch_name.find("feature") != -1:
                tag_name = branch_name + "-" + num
        else:
            if branch_name == "master":
                tag_name = "project-{}-{}".format(company_id, num)
            else:
                tag_name = "project-{}-{}-{}".format(company_id, branch_name, num)
        obj.tag_name = tag_name
        obj.branch_name = branch_name
        obj.pipeline_id = ci_pipeline_id
        print("getGitlabTagNameNew obj.save():", obj.tag_name, obj.branch_name, obj.pipeline_id)
        obj.save()
        print("getGitlabTagNameNew obj.save() success~")
        return HttpResponse(tag_name)

def host_to_ip(host):
    try:
        family, socktype, proto, canonname, sockaddr = socket.getaddrinfo(
            host, 0, socket.AF_UNSPEC, socket.SOCK_STREAM)[0]

        if family == socket.AF_INET:
            ip, port = sockaddr
        elif family == socket.AF_INET6:
            ip, port, flow_info, scope_id = sockaddr

    except Exception:
        ip = None
    return ip

def DeployCreateApi(request):
    project_id = request.POST.get("project")
    envName = request.POST.get("envName")
    envDesc = request.POST.get("envDesc")
    envTemplate_id = request.POST.get("envTemplate")
    dataSet = request.POST.get("dataSet")
    commonApp = request.POST.get("commonApp")
    user = request.POST.get("user")
    dynamicEnv_dict = request.POST.get("dynamicEnv")
    if dynamicEnv_dict:
        dynamicEnv_dict = eval(dynamicEnv_dict)
    else:
        dynamicEnv_dict = {}
    if not(project_id and envName and envDesc and dataSet and commonApp and user and envTemplate_id):
        return JsonResponse({"result": 500, "msg": "缺少参数"})
    if not User.objects.filter(id=user):
        return JsonResponse({"result": 500, "msg": "用户不存在"})
    user = User.objects.get(id=user)
    ugroup = user.groups.all()[0]
    new_images = []

    if not user.is_superuser:
       if hasattr(user, "profile"):
           print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                 fileName=os.path.basename(__file__),
                                                                 func=sys._getframe(
                                                                 ).f_code.co_name,
                                                                 num=sys._getframe().f_lineno,
                                                                 args="用户id{}, 姓名{}, 当前环境数是{}, 环境限额是{}".format(
                                                                     request.POST.get("user"), user.last_name, user.profile.currentDeployNum, user.profile.maxDeployNum))

           num = int(user.profile.currentDeployNum) + 1
           if num > int(user.profile.maxDeployNum):
               return JsonResponse({"result": 500, "msg": "您的环境数为{},环境数上限为{}，不能再创建新环境".format(user.profile.currentDeployNum,user.profile.maxDeployNum)})
       else:
           UserProfile.objects.create(user=user, currentDeployNum=0, maxDeployNum=1)
           print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                 fileName=os.path.basename(__file__),
                                                                 func=sys._getframe(
                                                                 ).f_code.co_name,
                                                                 num=sys._getframe().f_lineno,
                                                                 args="用户没有profile属性. id{}, 姓名{}, 创建了环境限额为1".format(
                                                                     request.POST.get("user"), user.last_name))
       if hasattr(ugroup, "group_profile"):
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                 fileName=os.path.basename(__file__),
                                                                 func=sys._getframe(
                                                                 ).f_code.co_name,
                                                                 num=sys._getframe().f_lineno,
                                                                 args="组id{}, 组名{}, 当前环境数是{}, 环境限额是{}".format(
                                                                     ugroup.id, ugroup.name, ugroup.group_profile.currentDeployNum, ugroup.group_profile.maxDeployNum))

            num = int(ugroup.group_profile.currentDeployNum) + 1
            if num > int(ugroup.group_profile.maxDeployNum):
                return JsonResponse({"result": 500, "msg": "您的所属组环境数为{},环境数上限为{},不能再创建新环境,请前往http://devops.flashhold.com:8000/group/查看组限额详情".format(ugroup.group_profile.currentDeployNum,ugroup.group_profile.maxDeployNum)})
       else:
           return JsonResponse({"result": 500, "msg": "组错误，组没有profile属性，请联系管理员检查"})

    k = K8sApi()
    status = k.get_namespace_status(envName)
    if status == "Terminating":
        return JsonResponse({"result":500,"msg":"上次创建失败的环境正在清理.请刷新页面重新获取环境名创建环境"})

    if not DataSet2.objects.filter(id=dataSet):
        return JsonResponse({"result": 500, "msg": "参数:数据集不存在"})

    if not EnvTemplateList.objects.filter(id=envTemplate_id):
        return JsonResponse({"result": 500, "msg": "参数:环境模板id不存在"})
    envTemplate_name = EnvTemplateList.objects.get(id=envTemplate_id).name
    envs = EnvTemplateDetail.objects.filter(templateList_id=envTemplate_id)
    for env in envs:
        if env.appName == "evo-nginx":
            continue
        if env.imageTag:
            appName = env.appName
            imageTag = env.imageTag
            branch_Name = env.branchName
            baseapp = "{}:{}".format(appName, imageTag)
            ### 此处解决pipeline_id之前 应用打包同步导致Tag相同的情况
            images_test = ImageVersion.objects.filter(name=baseapp)
            if len(images_test) == 1:
                image = ImageVersion.objects.get(name=baseapp)
            else:
                image = ImageVersion.objects.filter(name=baseapp, branchName=branch_Name)
                if image:
                    image = image[0]
                else:
                    return JsonResponse({"result": 500, "msg": "环境模板中{}版本不正确或者不存在，请检查更换".format(baseapp)})
        else:
            appName = env.appName
            appProject = env.appProject
            branch_Name = env.branchName
            images = ImageVersion.objects.filter(appName=appName, projectName=appProject,
                                                 branchName=branch_Name).order_by("-createDate")
            if images:
                image=images[0]
            else:
                return JsonResponse({"result": 500, "msg": "环境模板中{}版本不正确或者不存在，请检查更换".format(appName)})
        new_images.append(image)


    #检查helmcharts
    ##baseapp
    for image in new_images:
        appName = image.name.split(":")[0]
        if appName in settings.POD_PERSISTENCE_APP:
            if not os.path.isdir("{}/helmCharts/evo-baseapp-charts/{}".format(settings.PROJECT_ROOT,appName)):
                return JsonResponse({"result":500,"msg":"{}的helm charts不存在".format(appName)})
        else:
            if not os.path.isdir("{}/helmCharts/evo-baseapp/{}".format(settings.PROJECT_ROOT, appName)):
                return JsonResponse({"result": 500, "msg": "{}的helm charts不存在".format(appName)})
    ##commonapp
    com_images = commonApp.split(",")
    for image in com_images:
        if not os.path.isdir("{}/helmCharts/library/{}".format(settings.PROJECT_ROOT, image)):
            return JsonResponse({"result": 500, "msg": "{}的helm charts不存在".format(image)})

    try:
        obj = Deployment.objects.create(envName=envName,envDesc=envDesc,commonApp=commonApp,dataSet_id=dataSet,
                            envTemplate_name=envTemplate_name,envTemplate_id=envTemplate_id,
                                   project_id=project_id,userId=user.id,dynamicEnv=dynamicEnv_dict)
    except Exception:
        return JsonResponse({"result":500,"msg":"保存数据失败--envName->{}唯一键冲突，"
                                                "请刷新网页获取新的envName后在试".format(envName)})
    for image in new_images:
        obj.imageVersion.add(image)

    try:
        k.create_namespace(obj.envName,user.username,ugroup.name)

        rsn2 = helper.deployCommonApp(obj.id)
        if not rsn2["rs"]:
            k.delete_namespace(namespace=obj.envName)
            # helper.deleteDployTemplate(obj.id)
            helper.deleteDeployCommonApp(obj.id)
            helper.deleteDeployBaseApp(obj.id)
            obj.delete()
            return JsonResponse({"result":500,"msg":rsn2["msg"]})

        # 每次创建mysql chart，会生成一个新的pvc来存储mysql数据，因此原来的mysql数据就被清空了；所以必须要通过source sql文件的形式导入
        rsn = helper.deployInitData(dataSet=dataSet, namespace=obj.envName)
        if not rsn["rs"]:
            job_pod = k.list_pods_name(namespace=obj.envName, job_name="init-db")
            if job_pod:
                logs = k.get_pod_log(namespace=obj.envName, name=job_pod[0])
                if logs:
                    k.delete_namespace(namespace=obj.envName)
                    helper.deleteDeployCommonApp(obj.id)
                    helper.deleteDeployBaseApp(obj.id)
                    obj.delete()
                    raise logs
                    return JsonResponse({"result": 500, "msg": "创建初始化db client job失败,pod创建成功,reason-->{},log-->{}".format(rsn["msg"],logs)})
                k.delete_namespace(namespace=obj.envName)
                helper.deleteDeployCommonApp(obj.id)
                helper.deleteDeployBaseApp(obj.id)
                obj.delete()
                return JsonResponse({"result": 500, "msg": "创建初始化db client job失败,reason-->{}".format(rsn["msg"])})
            k.delete_namespace(namespace=obj.envName)
            helper.deleteDeployCommonApp(obj.id)
            helper.deleteDeployBaseApp(obj.id)
            obj.delete()
            return JsonResponse({"result": 500, "msg": "创建初始化db client job失败,reason-->{}".format(rsn["msg"])})

        if "rdp" in com_images:
            rsn = helper.deployRdpData(namespace=obj.envName)
            if rsn["rs"]:
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="create_rdp_init_job success")
            else:
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="create_rdp_init_job fail {}".format(rsn["msg"]))

        rsn3 = helper.deployBaseApp(obj.id,dynamicEnv_dict=dynamicEnv_dict)
        if not rsn3["rs"]:
            k.delete_namespace(namespace=obj.envName)
            helper.deleteDeployCommonApp(obj.id)
            helper.deleteDeployBaseApp(obj.id)
            obj.delete()
            return JsonResponse({"result": 500, "msg": "创建基础应用失败,reason-->{}".format(rsn3["msg"])})

        rsn4 = deploy_nginx_chart.InstallNginxChart(envName, envTemplate_id)
        if not rsn4["rs"]:
            k.delete_namespace(namespace=obj.envName)
            helper.deleteDeployCommonApp(obj.id)
            helper.deleteDeployBaseApp(obj.id)
            obj.delete()
            return JsonResponse({"result": 500, "msg": "安装nginx chart失败!,reason-->{}".format(rsn4["msg"])})

        ####dns
        dns = DnsApi()
        if not host_to_ip(obj.envName):
            dns.update(domain="{deploy_name}".format(deploy_name=envName),
                       hostIP=settings.DNS_HOST)
        if not check_url(url="{deploy_name}.flashhold.com".format(deploy_name=envName)):
            dns.update(domain="{deploy_name}".format(deploy_name=envName),
                       hostIP=settings.DNS_HOST)
        # if not check_url(url="{deploy_name}.flashhold.com".format(deploy_name=envName)):
        #     k.delete_namespace(namespace=obj.envName)
        #     helper.deleteDeployCommonApp(obj.id)
        #     helper.deleteDeployBaseApp(obj.id)
        #     obj.delete()
        #     return JsonResponse({"result": 500, "msg": "dns解析失败，没有成功添加规则"})

        #if not hasattr(user, "profile"):
        #    UserProfile.objects.create(user=user, currentDeployNum=0, maxDeployNum=2)
        user.profile.currentDeployNum = 1 if not user.profile.currentDeployNum else int(
            user.profile.currentDeployNum) + 1
        user.profile.save()
        ugroup.group_profile.currentDeployNum = int(ugroup.group_profile.currentDeployNum) + 1
        ugroup.group_profile.save()
        return JsonResponse({"result":200,"msg":"部署成功"})

    except Exception as e:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="Exception when Create Deploy: %s\n" % e)

        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="Exception when Create Deploy: %s\n" % traceback.format_exc())

        helper.deleteDeployCommonApp(obj.id)
        helper.deleteDeployBaseApp(obj.id)
        k.delete_namespace(namespace=obj.envName)
        obj.delete()
        return JsonResponse({"result": 500, "msg": "部署失败,reason-->Exception when Create Deploy:{}".format(traceback.format_exc())})

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
def test_api(request):
    dns = DnsApi()
    # # a=check_url(url="{deploy_name}.flashhold.com".format(deploy_name="deploy-1592883887"))
    a=dns.update(domain="{deploy_name}".format(deploy_name="deploy-1591684129"),
                   hostIP=settings.DNS_HOST)
    # return JsonResponse({"result": 500,"e":a})

    return JsonResponse({"result": 500,"e":a})


def DeployDeteleApi(request):
    deploy_id = request.POST.get("deploy_id")
    if Deployment.objects.filter(id=deploy_id):
        deploy = Deployment.objects.get(id=deploy_id)
        env_id=Deployment.objects.get(id=deploy_id).envTemplate_id
    else:
        return JsonResponse({"result": 500, "msg": "环境不存在"})
    if EnvTemplateList.objects.filter(id=env_id):
        helper.deleteDployTemplate(deploy_id)
    os.system("/bin/rm -rf {}/tmp/{}-nginx".format(settings.PROJECT_ROOT, deploy.envName))
    baseDetele = helper.deleteDeployBaseApp(deploy_id)
    if not baseDetele:
        return JsonResponse({"result": 500, "msg": "baseapp删除失败"})
    comDelete = helper.deleteDeployCommonApp(deploy_id)
    if not comDelete:
        return JsonResponse({"result": 500, "msg": "commonapp删除失败"})
    k = K8sApi()
    k.delete_namespace(deploy.envName)
    helper.delete_release_random_port(deploy.envName)

    user = User.objects.get(id=deploy.userId)
    group = user.groups.all()[0]
    if hasattr(user, "profile"):
        user.profile.currentDeployNum = len(Deployment.objects.filter(userId=user.id)) - 1
        user.profile.save()
    if hasattr(group, "group_profile"):
        group.group_profile.currentDeployNum -= 1
        group.group_profile.save()
    ###dns
    dns = DnsApi()
    dns.delete(domain="{}".format(deploy.envName))
    deploy.delete()
    return JsonResponse({"result":200,"msg":"删除成功"})

def get_pod_monitor_resource_func(app_names,deploy_name):
    l = MonitorApi()
    k8s = K8sApi()
    pod_map = {}
    for item in app_names:
        try:
            pod_name = k8s.get_pod_info(namespace=deploy_name, name=item)
            pod_map[item] = pod_name
        except:
            continue
    memorys = l.get_pods_memory(namespace=deploy_name)
    cpus = l.get_pods_cpu(namespace=deploy_name)

    data = {}
    for item in app_names:
        data[item] = {"memory": "", "cpu": "", "restart_count": "", "reason": ""}
        try:
            data[item]["memory"] = "%.1fMiB" % (long(memorys[pod_map[item]]) / (1024 * 1024))
            data[item]["cpu"] = "%.2f" % float(cpus[pod_map[item]])
            restart_count, reason = k8s.get_pod_restart_count_and_reason(namespace=deploy_name, name=pod_map[item])
            data[item]["restart_count"] = restart_count
            data[item]["reason"] = reason
        except:
            data[item]["memory"] = None
            data[item]["cpu"] = None
            data[item]["restart_count"] = None
            data[item]["reason"] = None
    return data

def DeployDetailApi(request):
    deploy_id = request.POST.get("deploy_id")
    deploy = Deployment.objects.get(id=deploy_id)
    rt = patch_pod_SqlK8s(deploy_id)
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="deploy:{}".format(deploy))
    context={}
    l = K8sApi()
    data = {"dataSet": [], "envTemplate": [] ,"commonApp": [], "baseApp": [], "tcpService": []}

    ###数据集
    dataSetId = Deployment.objects.get(id=deploy.id).dataSet_id
    if dataSetId:
        if DataSet2.objects.filter(id=dataSetId):
            dataSet = DataSet2.objects.get(id=dataSetId)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="dataSet name : {}, dataSet imageName: {}".format(
                                                                      dataSet.name, dataSet.imageName))
            job_status = l.get_job_status(namespace=deploy.envName, name="init-db")
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="status for job init-db in namespace {} is {}".format(
                                                                      deploy.envName, job_status))
            if job_status:
                status = "已完成"
            else:
                status = "初始化中"

            data['dataSet'].append({
                "name": dataSet.name,
                "imageName": dataSet.imageName,
                "status": status})
        else:
            data['dataSet'].append({
                "name": "error",
                "imageName": "数据集不存在，可能被删除-请联系管理员",
                "status": "error"})
    else:
        data['dataSet'].append({
            "name": "error",
            "imageName": "环境数据集参数缺失",
            "status": "error"})

    ##envT
    envT = EnvTemplateList.objects.filter(id = deploy.envTemplate_id)
    if envT:
        env_name = envT[0].name
        env_desc = envT[0].description
        data['envTemplate'].append({
            "env_name":env_name,
            "env_desc":env_desc,
        })
    else:
        data['envTemplate'].append({
            "env_name": "参数缺失",
            "env_desc": "参数缺失",
        })

    ###baseApp
    baseImages = deploy.imageVersion.all().order_by('-createDate')
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="baseImages:{}".format(baseImages))
    base_app_str = []

    #for image in baseImages:
    #    base_app_str.append(image.appName)
    #deploy_name = Deployment.objects.get(id=deploy_id).envName
    #pods_resource = get_pod_monitor_resource_func(base_app_str,deploy_name).
    envT = EnvTemplateDetail.objects.filter(templateList_id = deploy.envTemplate_id)
    envT_tag = {}
    # for e in envT:
    #     if e.appName == "evo-nginx":
    #         continue
    #     envT_tag[e.appName]=e.imageTag
    for env in envT:
        if env.appName == "evo-nginx":
            continue
        if env.imageTag:
            appName = env.appName
            imageTag = env.imageTag
            branch_Name = env.branchName
            baseapp = "{}:{}".format(appName, imageTag)
            ### 此处解决pipeline_id之前 应用打包同步导致Tag相同的情况
            images_test = ImageVersion.objects.filter(name=baseapp)
            if len(images_test) == 1:
                image = ImageVersion.objects.get(name=baseapp)
            else:
                image = ImageVersion.objects.filter(name=baseapp, branchName=branch_Name)
                if image:
                    image = image[0]
                else:
                    return JsonResponse({"result": 500, "msg": "环境模板中{}版本不正确或者不存在，请检查更换".format(baseapp)})
        else:
            appName = env.appName
            appProject = env.appProject
            branch_Name = env.branchName
            images = ImageVersion.objects.filter(appName=appName, projectName=appProject,
                                                 branchName=branch_Name).order_by("-createDate")
            if images:
                image = images[0]
            else:
                return JsonResponse({"result": 500, "msg": "环境模板中{}版本不正确或者不存在，请检查更换".format(appName)})
        envT_tag[env.appName] = image.name.split(":")[-1]

    if baseImages:
        for imageVersion in baseImages:
            chart_name = imageVersion.chartAddress.split("/")[-1]
            _, tag = imageVersion.name.split(":")
            commit_name = tag.split("-")[-1]
            branch_name = "-".join(tag.split("-")[0:-1])
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="chart_name:{}, tag:{}, commit_name:{}, branch_name: {}, namespace: {}, name: {}, service_port: {},  chart_version:{}".format(
                                                                      chart_name, tag, commit_name, branch_name,
                                                                      deploy.envName, imageVersion.appName,
                                                                      imageVersion.containerPort,
                                                                      imageVersion.chartVersion))

            releaseApp = Release_report_app.objects.all()
            releaseName=[]
            for i in releaseApp:
                releaseName.append(i.app_tag)
            if imageVersion.name in releaseName:
                release_name = Release_report_app.objects.get(app_tag=imageVersion.name).release_tag
            else:
                release_name = ""
            data["baseApp"].append({
                "id": imageVersion.id,
                "app_name": imageVersion.appName,
                "branch_name": branch_name,
                "envT_tag": "" if not envT_tag.has_key(imageVersion.appName) or envT_tag[imageVersion.appName]==tag else envT_tag[imageVersion.appName],
                "commit_name": commit_name,
                "release_tag": release_name,
                "deploy_status": "部署成功" if l.get_deployment_status(namespace=deploy.envName,
                                                                   name=imageVersion.appName) else "请稍等...",
                "deploy_ready_status": "已就绪" if l.get_deployment_status(namespace=deploy.envName,
                                                                   name=imageVersion.appName) else "未就绪...",
                "pod_name": l.get_pod_info(namespace=deploy.envName,name=imageVersion.appName),
                "service_port": imageVersion.containerPort,
                "random_port": "80" if imageVersion.http else imageVersion.randomPort
            },
            )

            base_app_str.append(imageVersion.appName)
            if imageVersion.appName  in settings.TCPSERVERMAP.keys():
                appName = imageVersion.appName
                for port in settings.TCPSERVERMAP[appName]:
                   rs = helper.getRCSport(deploy_id=deploy.id, deploy_envName=deploy.envName, appName=appName, port=port)
                   print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="result of getRCSport :{}".format(rs))
                   data['tcpService'].append(rs)

    if deploy.commonApp:
        commonApp = deploy.commonApp.split(",")
        for app in commonApp:
            val = {"name": app,"domain": "{}.flashhold.com".format(deploy.envName),
                   "random_port": l.get_service_port(namespace=deploy.envName, name=app)}

            pods = l.get_pods_name_by_service(namespace=deploy.envName, name=app)
            if pods:
                nodeName = l.get_nodeName_by_podName(namespace=deploy.envName, name=pods[0])
                if nodeName:
                    val["nodeIp"] = settings.NODEMAP[nodeName]

            if app == "redis":
                pods = l.get_pods_name_by_service(namespace=deploy.envName, name="redis")
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="redis pod name:{}".format(pods))
                if pods:
                    if l.get_pod_status(namespace=deploy.envName, name=pods[0]) == "Running":
                        val["deploy_status"] = "部署成功"
                    else:
                        val["deploy_status"] = "请稍等..."
            else:
                val["deploy_status"] = "部署成功" if (l.get_deployment_status(namespace=deploy.envName,
                                                                          name=app)) else "请稍等..."

            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="commonApp : {}".format(val))

            data["commonApp"].append(val)

    context["dataSet"] = data['dataSet']
    context["envTemplate"] = data['envTemplate']
    context["tcpService"] = data['tcpService']
    context["baseApp"] = data['baseApp']
    context["commonApp"] = data['commonApp']
    context["baseApp_str"] = ",".join(base_app_str)
    context["domain"] = "{envName}.flashhold.com".format(envName=deploy.envName)

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="i'm here ~~, context['tcpService']: {}".format(context["tcpService"]))

    return JsonResponse({"result": 200, "data":context})

def get_nodeport(request):
    envName = request.POST.get("envName")
    appName = request.POST.get("appName")
    port = request.POST.get("port")
    try:
        deploy_id = Deployment.objects.get(envName=envName).id
        context = helper.getRCSport(deploy_id=deploy_id, deploy_envName=envName, appName=appName, port=port)
        return JsonResponse({"result": 200, "data": context})
    except Exception as e:
        return JsonResponse({"result": 500, "error": "reason --> {}".format(e)})

def getGitlabTagName(request):
    branch_name = request.GET.get("branch_name")
    gitlab_project_id = request.GET.get("gitlab_project_id")
    company_id = request.GET.get("company")

    dateMonth = datetime.datetime.now().strftime("%y%m%d")
    obj = None
    if not TagNum.objects.filter(dateMonth=dateMonth, project_id=int(gitlab_project_id), branch_name=branch_name):
        obj = TagNum.objects.create(dateMonth=dateMonth, project_id=int(gitlab_project_id), branch_name=branch_name)
    else:
        obj_old = TagNum.objects.filter(dateMonth=dateMonth, project_id=int(gitlab_project_id),
                                        branch_name=branch_name).order_by(
            "-num").values("num")
        obj = TagNum.objects.create(dateMonth=dateMonth, project_id=int(gitlab_project_id), branch_name=branch_name)
        coun = obj_old.values("num")[0]["num"]
        print("getGitlabTagName coun:  ", coun)
        obj.num = coun + 1
        obj.save()
    num = "%s%02d" % (dateMonth, obj.num)

    git = Api()
    tags = git.get_project_tag(gitlab_project_id)
    app_name = git.get_project(gitlab_project_id)['name']

    tag_name = branch_name + "-" + num
    if company_id is None:
        if branch_name == "master":
            tags = [re.match(r'^\d\.\d\.\d$', tag) for tag in tags if re.match(r'^\d\.\d\.\d$', tag) is not None]
            # tags[0] is latest
            if tags:
                tag_name = "%s-%s" % (tags[0].group(), num)
            else:
                # git.create_project_tag(project_id=gitlab_project_id, tag_name=tag_name, ref="master")
                tag_name = "2.2.0-%s" % (num)
        if branch_name.find("hotfix") != -1:
            hotfix_version = ".".join(branch_name.split("-")[1:])
            tag_name = "%s-%s" % (hotfix_version, num)
        if branch_name.find("release") != -1:
            tag_name = branch_name + "-" + num
        if branch_name.find("feature") != -1:
            tag_name = branch_name + "-" + num
    else:
        if branch_name == "master":
            tag_name = "project-{}-{}".format(company_id, num)
        else:
            tag_name = "project-{}-{}-{}".format(company_id, branch_name, num)
    obj.tag_name = tag_name
    obj.branch_name = branch_name
    print("getGitlabTagNameNew obj.save():", obj.tag_name, obj.branch_name, obj.pipeline_id)
    obj.save()
    print("getGitlabTagNameNew obj.save() success~")
    return HttpResponse(tag_name)


def setappTag(request):
    tag_name = request.GET.get("tag_name")
    gitlab_project_id = request.GET.get("gitlab_project_id")
    branch_name = request.GET.get("branch_name")
    print(
        os.path.basename(__file__), sys._getframe().f_code.co_name, sys._getframe().f_lineno, tag_name,
        gitlab_project_id,
        branch_name)
    git = Api()
    git.create_project_tag(project_id=gitlab_project_id, tag_name=tag_name, ref=branch_name)
    return JsonResponse({"success": 0, "msg": 0}, safe=False)


def getappTag(request):
    app_id = request.GET.get("app_id")
    app = App.objects.get(id=app_id)
    git = Api()
    tags = git.get_project_tag(app.projectId)
    tags = [re.match(r'^\d\.\d\.\d$', tag).group() for tag in tags if re.match(r'^\d\.\d\.\d$', tag) is not None]
    return JsonResponse(tags, safe=False)

def patch_pod_SqlK8s(deploy_id):
    l = K8sApi()
    deploy = Deployment.objects.get(id=deploy_id)
    k8s_pods = l.list_pods_name_nojob(namespace=deploy.envName)
    ##k8s
    k8spod_list = []
    for pod in k8s_pods:
        k8spod_list.append("-".join(pod.split("-")[:-2]))
    k8spod_list = list(set(k8spod_list))
    commonapp_list = deploy.commonApp.split(",")
    for pod in commonapp_list:
        if pod in k8spod_list:
            k8spod_list.remove(pod)
    if "init" in k8spod_list:
        k8spod_list.remove("init")
    new_k8spod_list = []
    for pod in k8spod_list:
        if "evo" in pod or 'registry' in pod:
            new_k8spod_list.append(pod)
    #sql
    sql_pods = deploy.imageVersion.all()
    sqlpod_dict = {}
    for pod in sql_pods:
        sqlpod_dict[pod.id]=pod.name.split(":")[0]
    #patch
    if len(new_k8spod_list) == len(sqlpod_dict.values()):
        return True
    if len(new_k8spod_list) > len(sqlpod_dict.values()):
        for pod in new_k8spod_list:
            if pod not in sqlpod_dict.values():
                t = Tiller(settings.TILLER_SERVER["address"], settings.TILLER_SERVER["port"])
                chart_name = "{}-{}".format(deploy.envName,pod)
                try:
                    _ = t.uninstall_release(release=chart_name)
                except:
                    return False
    else:
        sqlkey_list = sqlpod_dict.keys()
        sqlkey_list.sort()
        sqlkey_list.reverse()
        applist = []
        for i in sqlkey_list:
            applist.append(sqlpod_dict[i])
        for pod in applist:
            if pod not in new_k8spod_list:
                if sqlpod_dict.values().count(pod)>1:
                    image_id = list(sqlpod_dict.keys())[list(sqlpod_dict.values()).index(pod)]
                    sqlpod_dict.pop(image_id)
                    new_image_id = list(sqlpod_dict.keys())[list(sqlpod_dict.values()).index(pod)]
                    if new_image_id > image_id:
                        image = ImageVersion.objects.get(id = image_id)
                        deploy.imageVersion.remove(image)
                    else:
                        image = ImageVersion.objects.get(id=new_image_id)
                        deploy.imageVersion.remove(image)
                elif sqlpod_dict.values().count(pod) == 1:
                    image_id = list(sqlpod_dict.keys())[list(sqlpod_dict.values()).index(pod)]
                    image = ImageVersion.objects.get(id=image_id)
                    deploy.imageVersion.remove(image)
                else:
                    continue
            else:
                new_k8spod_list.remove(pod)
    return False


def test(request):
    return HttpResponse(1)

