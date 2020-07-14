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

    rsn = re.match(r'[a-zA-Z0-9]([-a-zA-Z0-9]*[a-zA-Z0-9])', data)
    if not rsn:
        raise forms.ValidationError("环境名只允许字母,数字,和 -。并且开头和结尾必须是字母")
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



def deployDeleteTemplate(deploy_id):
    if Deployment.objects.filter(id=deploy_id):
        obj = Deployment.objects.get(id=deploy_id)
        featureApp = obj.envTemplate.featureApp.all()
        tmp_dir = "/tmp/%s" % (obj.envName)
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)

        sf_name = "{tmp_dir}/deploy-delete-template.sh".format(tmp_dir=tmp_dir)

        sf = open(sf_name, "w+")

        cmd = "#!/bin/bash\n"
        sf.write(cmd)

        cmd = "export KUBECONFIG={kube_config}\n".format(
            kube_config=settings.KUBERNETES_CONFIG)
        sf.write(cmd)

        cmd = "export HELM_HOME={helm_config}\n".format(
            helm_config=settings.HELM_HOME)
        sf.write(cmd)

        if featureApp:
            for app in featureApp:
                if obj.imageVersion.filter(appName=app.name).exists():
                    image = obj.imageVersion.filter(appName=app.name)[0]
                    chart_name = image.chartAddress.split("/")[-1]
                    repo = "/".join(image.chartAddress.split("/")[0:-1])
                    cmd = "helm delete --purge {release_name}\n".format(
                        release_name="%s-%s" % (obj.envName, chart_name))
                    sf.write(cmd)
        sf.close()
        os.system("/bin/bash {deploy_file} >> {tmp_dir}/deploy_record.log 2>&1".format(
            deploy_file=sf_name, tmp_dir=tmp_dir))
        crt = DeployHistory.objects.create(deploy=obj, msg=u"删除环境%s" % obj.envName,
                                           chartTmpDir=os.path.join(tmp_dir, "deploy_record.log"))
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="result of DeployHistory.objects.create: ".format(
                                                                  crt))


def deployTemplate(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    # featureApp = obj.envTemplate.featureApp.all()
    tmp_dir = "/tmp/%s" % (obj.envName)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    sf_name = "{tmp_dir}/deploy-template.sh".format(tmp_dir=tmp_dir)
    sf = open(sf_name, "w+")

    cmd = "#!/bin/bash\n"
    sf.write(cmd)

    cmd = "export KUBECONFIG={kube_config}\n".format(
        kube_config=settings.KUBERNETES_CONFIG)
    sf.write(cmd)

    cmd = "export HELM_HOME={helm_config}\n".format(
        helm_config=settings.HELM_HOME)
    sf.write(cmd)

    images = obj.imageVersion.exclude(baseAppFlag=1)
    for image in images:
        chart_name = image.chartAddress.split("/")[-1]
        repo = "/".join(image.chartAddress.split("/")[0:-1])
        containerPorts = image.containerPort.split(",")
        if not image.http:
            # tcp have bug ,fix in future
            containerPort = containerPorts[0]
            random_port = get_tcp_service_random_port(namespace=obj.envName, service_name=chart_name,
                                                      port=containerPort)
            image.randomPort = random_port
        else:
            image.randomPort = 80
        image.save()

        config = deploy_common_env(
            image.config, image.appName, deploy_name=obj.envName)
        config = config.replace(
            "deploy_name", "{envName}".format(envName=obj.envName).replace("enabled: true", "enabled: false"))

        tmp_file = os.path.join(tmp_dir, "new_value.yaml")
        with open(tmp_file, "w") as f:
            f.write(config)

        cmd = "helm install --repo {repo} {chart_name} --name {release_name} --namespace {namespace} -f {value_file} --set ingress.enabled=false  --set service.type=ClusterIP || " \
              "helm upgrade {release_name} {chart_name} --repo {repo} -f {value_file} --set ingress.enabled=false  --set service.type=ClusterIP || " \
              "helm delete --purge {release_name}\n".format(
            repo=repo,
            chart_name=chart_name,
            release_name="%s-%s" % (obj.envName, chart_name),
            value_file=tmp_file,
            namespace=obj.envName)
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="exec cmd : {} for deployTemplate in namespace:{}, check logs last 10 lines:{} ".format(
                                                                  cmd, obj.envName))

        sf.write(cmd)
    sf.close()
    rsn = os.system("/bin/bash {deploy_file} >> {tmp_dir}/deploy_record.log 2>&1".format(
        deploy_file=sf_name, tmp_dir=tmp_dir))
    DeployHistory.objects.create(deploy=obj, msg=u"新增环境%s" % obj.envName,
                                 chartTmpDir=os.path.join(tmp_dir, "deploy_record.log"))
    if rsn > 0:
        with open('/tmp/{}/deploy_record.log'.format(obj.envName), 'r') as file:
            logs = file.readlines()
            errors = '\n'.join(logs[-10:])
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="failed to   deployTemplate in namespace:{}, check logs last 10 lines:{} ".format(
                                                                  obj.envName, errors))
        return False
    else:
        return True


def deployBaseApp(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    # featureApp = obj.envTemplate.featureApp.all()
    tmp_dir = "/tmp/%s" % (obj.envName,)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    sf_name = "{tmp_dir}/deploy-baseapp.sh".format(tmp_dir=tmp_dir)
    sf = open(sf_name, "w+")

    cmd = "#!/bin/bash\n"
    sf.write(cmd)

    cmd = "export KUBECONFIG={kube_config}\n".format(
        kube_config=settings.KUBERNETES_CONFIG)
    sf.write(cmd)

    cmd = "export HELM_HOME={helm_config}\n".format(
        helm_config=settings.HELM_HOME)
    sf.write(cmd)

    cmd = "echo 'XXXXXXXXXXXXXXXXXXX'${HOME}\n"
    sf.write(cmd)

    images = obj.imageVersion.exclude(baseAppFlag=0)
    for image in images:
        chart_name = image.chartAddress.split("/")[-1]
        repo = "/".join(image.chartAddress.split("/")[0:-1])
        containerPorts = image.containerPort.split(",")
        if not image.http:
            # tcp have bug ,fix in future
            containerPort = containerPorts[0]
            random_port = get_tcp_service_random_port(
                namespace=obj.envName, service_name=chart_name, port=containerPort)
            image.randomPort = random_port
            image.save()
        else:
            image.randomPort = 80
            image.save()

        config = deploy_common_env(
            image.config, image.appName, deploy_name=obj.envName)
        config = config.replace(
            "deploy_name", "{envName}".format(envName=obj.envName))

        tmp_file = os.path.join(tmp_dir, "new_value_%s.yaml" % (chart_name,))
        with open(tmp_file, "w") as f:
            f.write(config)

        cmd = "helm install -f {value_file} --repo {repo} {chart_name} --name {release_name}  --set service.type=ClusterIP --set ingress.enabled=false --namespace {namespace} || " \
              "helm upgrade {release_name} {chart_name} -f {value_file}  --set service.type=ClusterIP  --set ingress.enabled=false --repo {repo} || " \
              "helm delete --purge {release_name}\n".format(
            repo=repo,
            chart_name=chart_name,
            release_name="%s-%s" % (obj.envName, chart_name),
            namespace=obj.envName,
            value_file=tmp_file)

        if chart_name == "evo-rcs":
            cmd = "helm install -f {value_file} --repo {repo} {chart_name} --name {release_name} --set service.type=NodePort  --set ingress.enabled=false --namespace {namespace} || " \
                  "helm upgrade {release_name} {chart_name} -f {value_file} --set service.type=NodePort  --set ingress.enabled=false --repo {repo} || " \
                  "helm delete --purge {release_name}\n".format(
                repo=repo,
                chart_name=chart_name,
                release_name="%s-%s" % (obj.envName, chart_name),
                namespace=obj.envName,
                value_file=tmp_file)

        sf.write(cmd)
    sf.close()
    rsn = os.system("/bin/bash {deploy_file} >> {tmp_dir}/deploy_record.log 2>&1".format(
        deploy_file=sf_name, tmp_dir=tmp_dir))
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="code of deloy deployBaseApp : {}".format(rsn))

    if rsn > 0:
        with open('/tmp/{}/deploy_record.log'.format(obj.envName), 'r') as file:
            logs = file.readlines()
            errors = '\n'.join(logs[-10:])
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="failed to  deploy deployBaseApp in namespace:{}, check logs last 10 lines:{} ".format(
                                                                  obj.envName, errors))
        return False
    else:
        return True


def deployCommonApp(deploy_id):
    imageName = settings.MYSQL_IMAGE_BASE
    obj = Deployment.objects.get(id=deploy_id)
    tmp_dir = "/tmp/%s" % (obj.envName)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    sf_name = "{tmp_dir}/deploy-commonapp.sh".format(tmp_dir=tmp_dir)
    sf = open(sf_name, "w+")

    cmd = "#!/usr/bin/bash\n"
    sf.write(cmd)

    cmd = "export KUBECONFIG={kube_config}\n".format(
        kube_config=settings.KUBERNETES_CONFIG)
    sf.write(cmd)

    cmd = "export HELM_HOME={helm_config}\n".format(
        helm_config=settings.HELM_HOME)
    sf.write(cmd)

    charts = obj.commonApp.split(",")
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="charts of deploy rmq :  {}".format(
                                                              charts))

    repo = settings.LOCAL_HARBOR_LIBRARY_REPO
    if charts:
        for chart in charts:
            chart_name = chart.strip()
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="chart_name of deploy  :  {}".format(
                                                                      chart_name))

            if chart_name == "rmq":
                cmd = "helm install rmq --name {release_name} --repo {repo} --set service.type=NodePort  --set ingress.enabled=false --namespace {namespace} " \
                      "|| helm upgrade {release_name} {chart_name} --set service.type=NodePort  --set ingress.enabled=false --repo {repo} " \
                      "|| helm delete --purge {release_name}\n".format(repo=repo,
                                                                       chart_name=chart_name,
                                                                       release_name="%s-%s" % (
                                                                           obj.envName, chart_name),
                                                                       env_name=obj.envName,
                                                                       namespace=obj.envName)
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="cmd of deploy rmq :  {}".format(
                                                                          cmd))

                sf.write(cmd)
                if not CommomAppServicePortMapping.objects.filter(deploy=obj, commomAppName=chart_name).exists():
                    CommomAppServicePortMapping.objects.create(deploy=obj,
                                                               commomAppName=chart_name,
                                                               randomPort=80)
            else:
                if chart_name == "nginx":
                    cmd = "# nginx"
                    continue

                service_port = settings.COMMON_APP_PORT[chart]
                random_port = get_tcp_service_random_port(
                    namespace=obj.envName, service_name=chart_name, port=service_port)
                if not CommomAppServicePortMapping.objects.filter(deploy=obj, commomAppName=chart_name).exists():
                    CommomAppServicePortMapping.objects.create(deploy=obj,
                                                               commomAppName=chart_name,
                                                               randomPort=random_port)
                if chart_name == "mysql":
                    cmd = "helm install --repo {repo} {chart_name} --name {release_name} --namespace {namespace}  --set service.type=NodePort  --set ingress.enabled=false --set image={imageName} --set imageTag={imageTag} || helm upgrade {release_name} {chart_name} --repo {repo} --set service.type=NodePort  --set ingress.enabled=false --set image={imageName} --set imageTag={imageTag} || helm delete --purge {release_name}\n".format(
                        repo=repo,
                        chart_name=chart_name,
                        release_name="%s-%s" % (obj.envName, chart_name),
                        imageName=imageName.split(':')[0],
                        imageTag=imageName.split(':')[1],
                        namespace=obj.envName)

                else:
                    cmd = "helm install --repo {repo} {chart_name} --name {release_name}  --set ingress.enabled=false --set service.type=NodePort --namespace {namespace} || helm upgrade {release_name} {chart_name} --repo {repo} || helm delete --purge {release_name}\n".format(
                        repo=repo,
                        chart_name=chart_name,
                        release_name="%s-%s" % (obj.envName, chart_name),
                        namespace=obj.envName)

                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="cmd of deployCommonApp :  {}".format(
                                                                          cmd))

                sf.write(cmd)
    sf.close()
    rsn = os.system("/usr/bin/bash {deploy_file} >> {tmp_dir}/deploy_record.log 2>&1".format(
        deploy_file=sf_name, tmp_dir=tmp_dir))
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="code of deploy deployCommonApp :  {}".format(rsn))

    if rsn > 0:
        with open('/tmp/{}/deploy_record.log'.format(obj.envName), 'r') as file:
            logs = file.readlines()
            errors = '\n'.join(logs[-10:])
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="failed to  deploy deployCommonApp in namespace:{}, check logs last 10 lines:{} ".format(
                                                                      obj.envName, errors))
        return False
    else:
        return True


def deployImageChart(deploy_id, image_id, image_config, cpu="", memory=""):
    image = ImageVersion.objects.get(id=image_id)
    deploy = Deployment.objects.get(id=deploy_id)
    tmp_dir = "/tmp/%s" % (deploy.envName)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    sf_name = "{tmp_dir}/deploy-image.sh".format(tmp_dir=tmp_dir)
    sf = open(sf_name, "w+")

    cmd = "#!/usr/bin/bash\n"
    sf.write(cmd)

    cmd = "export KUBECONFIG={kube_config}\n".format(
        kube_config=settings.KUBERNETES_CONFIG)
    sf.write(cmd)

    cmd = "export HELM_HOME={helm_config}\n".format(
        helm_config=settings.HELM_HOME)
    sf.write(cmd)

    config = deploy_common_env(
        image.config, image.appName, deploy_name=deploy.envName)
    config = config.replace(
        "deploy_name", "{envName}".format(envName=deploy.envName))

    tmp_file = os.path.join(tmp_dir, "new_value.yaml")
    with open(tmp_file, "w") as f:
        f.write(config)
    chart_name = image.chartAddress.split("/")[-1]
    repo = "/".join(image.chartAddress.split("/")[0:-1])
    if memory:
        cmd = "helm install --repo {repo} {chart_name} --name {release_name} -f {value_file}　--set resources.limits.memory={memory}Mi --namespace {namespace}  || helm upgrade {release_name} {chart_name} --repo {repo} -f {value_file} --set resources.limits.memory={memory}Mi --version {version}|| helm delete --purge {release_name}\n".format(
            repo=repo,
            chart_name=chart_name,
            release_name="%s-%s" % (deploy.envName, chart_name),
            value_file=tmp_file,
            namespace=deploy.envName,
            version=image.chartVersion,
            memory=memory)

    else:
        cmd = "helm install --repo {repo} {chart_name} --name {release_name} -f {value_file} --namespace {namespace}  || helm upgrade {release_name} {chart_name} --repo {repo} -f {value_file} --version {version}|| helm delete --purge {release_name}\n".format(
            repo=repo,
            chart_name=chart_name,
            release_name="%s-%s" % (deploy.envName, chart_name),
            value_file=tmp_file,
            namespace=deploy.envName,
            version=image.chartVersion
        )
    sf.write(cmd)
    sf.close()

    # replace_ingress_tcp(service_name="%s" %
    #                                  (chart_name,), random_port=image.randomPort)

    rsn = os.system("/usr/bin/bash {deploy_file} >> {tmp_dir}/deploy_record.log 2>&1".format(
        deploy_file=sf_name, tmp_dir=tmp_dir))
    DeployHistory.objects.create(deploy=deploy, msg=u"添加或更新release %s-%s" % (
        deploy.envName, chart_name), chartTmpDir=os.path.join(tmp_dir, "deploy_record.log"))
    return rsn


def deployDeleteImageChart(deploy_id, image_id):
    image = ImageVersion.objects.get(id=image_id)
    deploy = Deployment.objects.get(id=deploy_id)
    tmp_dir = "/tmp/%s" % (deploy.envName)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    sf_name = "{tmp_dir}/deploy-delete-image.sh".format(tmp_dir=tmp_dir)
    sf = open(sf_name, "w+")

    cmd = "#!/bin/bash\n"
    sf.write(cmd)

    cmd = "export KUBECONFIG={kube_config}\n".format(
        kube_config=settings.KUBERNETES_CONFIG)
    sf.write(cmd)

    cmd = "export HELM_HOME={helm_config}\n".format(
        helm_config=settings.HELM_HOME)
    sf.write(cmd)

    chart_name = image.chartAddress.split("/")[-1]
    cmd = "helm delete --purge {release_name}\n".format(
        release_name="%s-%s" % (deploy.envName, chart_name))
    sf.write(cmd)
    sf.close()
    rsn = os.system("/bin/bash {deploy_file} >> {tmp_dir}/deploy_record.log 2>&1".format(
        deploy_file=sf_name, tmp_dir=tmp_dir))
    DeployHistory.objects.create(deploy=deploy, msg=u"删除release %s-%s" % (
        deploy.envName, chart_name), chartTmpDir=os.path.join(tmp_dir, "deploy_record.log"))
    return rsn


def deployDatesetImage(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    tmp_dir = "/tmp/%s" % (obj.envName)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
    sf_name = "{tmp_dir}/deploy-dateset.sh".format(tmp_dir=tmp_dir)
    sf = open(sf_name, "w+")

    cmd = "#!/bin/bash\n"
    sf.write(cmd)

    cmd = "export KUBECONFIG={kube_config}\n".format(
        kube_config=settings.KUBERNETES_CONFIG)
    sf.write(cmd)

    cmd = "export HELM_HOME={helm_config}\n".format(
        helm_config=settings.HELM_HOME)
    sf.write(cmd)

    cmd = "helm install --repo {repo} {chart_name} --name {release_name} --namespace {namespace} || " \
          "helm upgrade {release_name} {chart_name} --repo {repo} || " \
          "helm delete --purge {release_name}\n".format(
        repo="http://{harbor_url}/chartrepo/dataset-image".format(
            harbor_url=settings.HARBOR_URL),
        chart_name=obj.dataSet.name,
        release_name="%s-%s" % (obj.envName, obj.dataSet.name),
        namespace=obj.envName)
    sf.write(cmd)
    sf.close()
    rsn = os.system(
        "/bin/bash {deploy_file} >> {tmp_dir}/deploy_record.log 2>&1".format(deploy_file=sf_name, tmp_dir=tmp_dir))
    if rsn > 0:
        with open('/tmp/{}/deploy_record.log'.format(obj.envName), 'r') as file:
            logs = file.readlines()
            errors = '\n'.join(logs[-10:])
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="failed to  deployDatesetImage in namespace:{}, check logs last 10 lines:{} ".format(
                                                                      obj.envName, errors))
        return False
    else:
        return True


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


def deployDataset(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    tmp_dir = "/tmp/%s" % (obj.envName)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    sf_name = "{tmp_dir}/deploy-dataset.sh".format(tmp_dir=tmp_dir)
    sf = open(sf_name, "w+")

    l = K8sApi()
    status = None
    nodePort = None
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="wait to install data!")

    i = 0
    while (status != "Running"):
        try:
            portList = l.get_service_port(namespace=obj.envName, name="mysql")
            for value in portList:
                port = value.split(":")
                if port[0] == "3306":
                    nodePort = port[1]

            pod_name = l.get_pods_name_by_service(namespace=obj.envName, name="mysql")
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="namespace:{}, mysql server pod name:{}".format(
                                                                      obj.envName, pod_name))

            status = l.get_pod_status(namespace=obj.envName, name=pod_name[0])
        except Exception, e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when get_pod_status: %s\n" % e)

            pass
        time.sleep(6)
        if i == 15:
            rsn = os.system(
                "echo 'mysql instance not running up in 90 seconds' >> {tmp_dir}/deploy_record.log 2>&1".format(
                    deploy_file=sf_name, tmp_dir=tmp_dir))

            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="mysql instance not running up in 90 seconds! in namespace:{}".format(
                                                                      obj.envName))

            return tmp_dir, rsn
        i = i + 1

    time.sleep(30)

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="ok , mysql server is running~~~~ ! in namespace:{}".format(
                                                              obj.envName))

    cmd = "#!/bin/bash\n"
    sf.write(cmd)

    cmd = "mysql -h {host} -P {port} -uroot -p123456 -e 'set global max_allowed_packet = 200*1024*1024;source {f};'".format(
        host="127.0.0.1", port=nodePort, f=obj.dataSet.f.path)
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="insert data by mysql client exec {} in namespace:{}".format(
                                                              cmd, obj.envName))

    sf.write(cmd)

    sf.close()
    rsn = os.system("/bin/bash {deploy_file} >> {tmp_dir}/deploy_record.log 2>&1".format(
        deploy_file=sf_name, tmp_dir=tmp_dir))
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="exec code of insert data to  mysql server {} in namespace:{}".format(
                                                              rsn, obj.envName))

    if rsn > 0:
        with open('/tmp/{}/deploy_record.log'.format(obj.envName), 'r') as file:
            logs = file.readlines()
            errors = '\n'.join(logs[-10:])
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="failed to  insert data to  mysql server {} in namespace:{}, check logs last 10 lines:{} ".format(
                                                                      nodePort, obj.envName, errors))
        return False
    else:
        return True


def deployDeleteDataset(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    l = K8sApi()
    name = l.get_pod_info(obj.envName, "mysql")
    if name:
        for m in name:
            l.delete_pod(namespace=obj.envName, name=name)

    return





def deployDeleteCommonApp(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    tmp_dir = "/tmp/%s" % (obj.envName)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    sf_name = "{tmp_dir}/deploy-deleteCommonApp.sh".format(tmp_dir=tmp_dir)
    sf = open(sf_name, "w+")

    cmd = "#!/bin/bash\n"
    sf.write(cmd)

    cmd = "export KUBECONFIG={kube_config}\n".format(
        kube_config=settings.KUBERNETES_CONFIG)
    sf.write(cmd)

    cmd = "export HELM_HOME={helm_config}\n".format(
        helm_config=settings.HELM_HOME)
    sf.write(cmd)

    commonApps = obj.commonApp.split(",")

    for app in commonApps:
        cmd = "helm delete --purge {release_name}\n".format(release_name="%s-%s" % (obj.envName, app),
                                                            kube_config=settings.KUBERNETES_CONFIG,
                                                            helm_config=settings.HELM_HOME)
        sf.write(cmd)
    sf.close()
    os.system("/bin/bash {deploy_file} >> {tmp_dir}/deploy_record.log 2>&1".format(
        deploy_file=sf_name, tmp_dir=tmp_dir))
    return


def deployDeleteDatasetImage(deploy_id):
    obj = Deployment.objects.get(id=deploy_id)
    tmp_dir = "/tmp/%s" % (obj.envName)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    sf_name = "{tmp_dir}/deploy-deleteDatasetImage.sh".format(tmp_dir=tmp_dir)
    sf = open(sf_name, "w+")

    cmd = "#!/bin/bash\n"
    sf.write(cmd)

    cmd = "export KUBECONFIG={kube_config}\n".format(
        kube_config=settings.KUBERNETES_CONFIG)
    sf.write(cmd)

    cmd = "export HELM_HOME={helm_config}\n".format(
        helm_config=settings.HELM_HOME)
    sf.write(cmd)

    cmd = "helm delete --purge {release_name}\n".format(release_name="%s-%s" % (obj.envName, obj.dataSet.name),
                                                        kube_config=settings.KUBERNETES_CONFIG,
                                                        helm_config=settings.HELM_HOME)
    sf.write(cmd)
    sf.close()
    os.system("/bin/bash {deploy_file} >> {tmp_dir}/deploy_record.log 2>&1".format(
        deploy_file=sf_name, tmp_dir=tmp_dir))
    return


def deleteDeployBaseApp(deploy_id):
    if Deployment.objects.filter(id=deploy_id):
        obj = Deployment.objects.get(id=deploy_id)
        tmp_dir = "/tmp/%s" % (obj.envName)


def deployDeleteBaseApp(deploy_id):
    if Deployment.objects.filter(id=deploy_id):
        obj = Deployment.objects.get(id=deploy_id)
        tmp_dir = "/tmp/%s" % (obj.envName)
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)

        sf_name = "{tmp_dir}/deploy-deleteBaseApp.sh".format(tmp_dir=tmp_dir)
        sf = open(sf_name, "w+")

        cmd = "#!/bin/bash\n"
        sf.write(cmd)

        cmd = "export KUBECONFIG={kube_config}\n".format(
            kube_config=settings.KUBERNETES_CONFIG)
        sf.write(cmd)

        cmd = "export HELM_HOME={helm_config}\n".format(
            helm_config=settings.HELM_HOME)
        sf.write(cmd)

        baseImages = obj.imageVersion.all()
        for image in baseImages:
            chart_name = image.chartAddress.split("/")[-1]
            cmd = "helm delete --purge {release_name}\n".format(release_name="%s-%s" % (obj.envName, chart_name),
                                                                kube_config=settings.KUBERNETES_CONFIG,
                                                                helm_config=settings.HELM_HOME)
            sf.write(cmd)
        sf.close()
        os.system("/bin/bash {deploy_file} >> {tmp_dir}/deploy_record.log 2>&1".format(
            deploy_file=sf_name, tmp_dir=tmp_dir))
        return


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


def get_nginx_conf(deploy_name):
    template = settings.NGINX_TEMPLATE
    conf = os.path.join(settings.NGINX_CONF_DIR, "%s.conf" % deploy_name)
    w = open(conf, "w")
    with open(template, "r") as f:
        t = f.read()
        d = t.replace("{{deploy_name}}", deploy_name)
        w.write(d)
    w.close()
    os.system("sudo systemctl restart nginx")
    return


# 已经废弃
def deploy_tcp_mapping(deploy_id):
    deploy = Deployment.objects.get(id=deploy_id)
    ns = deploy.envName
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="ns: {}".format(
                                                              ns))

    try:
        l = K8sApi()
        if not l.get_service_port(namespace=ns, name="evo-rcs"):
            str = "kubectl patch Service evo-rcs --patch '{dict_patch}' -n {namespace} >> /tmp/{namespace}/deploy_record.log"

            patchCont = str.replace('{dict_patch}', '{"spec": {"type":"NodePort"}}').replace('{namespace}', ns)
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args=" patchCont script: {}".format(
                                                                      patchCont))

            rs = os.system(patchCont)
            if rs > 0:
                with open('/tmp/{}/deploy_record.log'.format(ns), 'r') as file:
                    logs = file.readlines()
                    errors = '\n'.join(logs[-10:])
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="failed to deployCommonApp !".format(
                                                                          errors))
                return False

        # 只对rcs应用作映射

        k = l.get_service_port(namespace=ns, name="evo-rcs")
        if k:
            for ports in k:
                if ports.split(":"):
                    if ports.split(":")[0] == "7070":
                        randomPort = ports.split(":")[1]
                        crt = featureServicePortMapping.objects.create(deploy_id=int(deploy.id), port="7070",
                                                                       featureAppName="evo-rcs",
                                                                       randomPort=randomPort)

                        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                              fileName=os.path.basename(
                                                                                  __file__),
                                                                              func=sys._getframe(
                                                                              ).f_code.co_name,
                                                                              num=sys._getframe().f_lineno,
                                                                              args="evo-rcs  featureServicePortMapping.save(): {} ".format(
                                                                                  crt))
                    break

        return True

    except Exception as e:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="Exception when deploy_tcp_mapping: %s\n" % e)

        return False


def setRCSport(deploy_id, deploy_envName):
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="deploy_id: {}, deploy_envName: {}".format(
                                                              deploy_id, deploy_envName))
    if not deploy_id:
        return False
    if not deploy_envName:
        return False

    l = K8sApi()
    get_rcs_pm = featureServicePortMapping.objects.filter(deploy_id=deploy_id, port="7070",
                                                          featureAppName="evo-rcs")
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="featureServicePortMapping.objects.filter: {}".format(
                                                              get_rcs_pm))

    if not get_rcs_pm:
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
            return False

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
                return False

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
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="data for rcs port map in namespace {} is : deploy_id: {}, nodePort: {}, nodeIp: {} ".format(
                                                                      deploy_envName, pm.deploy_id, pm.randomPort,
                                                                      pm.nodeIp))
            if not pm.nodeIp:
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="data {} {} nodeIp is null! will be delete ".format(
                                                                          pm.deploy_id, pm.randomPort))
                pm.delete()
                setRCSport(deploy_id, deploy_envName)


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


def config_nfs(deploy_name):
    cmd = """ssh -o "StrictHostKeyChecking no" root@172.31.238.10 'mkdir /data-nfs/{deploy_name} && echo "/data-nfs/{deploy_name}  192.168.0.0/16(rw,sync,no_root_squash) 10.0.0.0/8(rw,sync,no_root_squash) 172.31.0.0/16(rw,sync,no_root_squash)" >> /etc/exports && exportfs -rf'""".format(
        deploy_name=deploy_name)
    os.system(cmd)
    return


def delete_nfs(deploy_name):
    cmd = """ssh -o "StrictHostKeyChecking no" root@172.31.238.10 'rm -rf /data-nfs/{deploy_name}'""".format(
        deploy_name=deploy_name)
    os.system(cmd)
    cmd = """sed -i '/{deploy_name}/d' /etc/exports """.format(
        deploy_name=deploy_name)
    os.system(cmd)
    return


if __name__ == "__main__":
    config_nfs("default")
