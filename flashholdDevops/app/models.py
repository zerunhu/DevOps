# coding=utf-8
from __future__ import unicode_literals
from django.shortcuts import render, reverse
from django.db import models
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.conf import settings
from Api.ldapApi import Uldap
import random
from django.db.models import Q


# Create your models here.

class FGroup(Group):
    nameSlug = models.CharField('别名', max_length=500)

    def save(self, *args, **kwargs):
        l = Uldap()
        l.create_ldapgroup(self.name)
        l.create_ldapgroup2(self.name)
        l.conn.unbind_s()
        super(FGroup, self).save(*args, **kwargs)

    def clean(self):
        super(FGroup, self).clean()
        for ch in self.name:
            if u'\u4e00' <= ch <= u'\u9fff':
                raise ValidationError("name字段不允许中文")


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    maxDeployNum = models.IntegerField('环境限制数', default=5, null=True)
    currentDeployNum = models.IntegerField('当前环境数量', null=True)


class GroupProfile(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='group_profile')
    maxDeployNum = models.IntegerField('环境限制数', default=10, null=True)
    currentDeployNum = models.IntegerField('当前环境数量', default=0, null=True)


class Project(models.Model):
    name = models.CharField('项目名称', max_length=255, unique=True)
    slugName = models.CharField('别名', max_length=255, unique=True)
    admin = models.ManyToManyField(User, related_name="project_admin", verbose_name='项目负责人', null=True)
    members = models.ManyToManyField(User, verbose_name='成员', null=True)
    baseAppVersion = models.CharField('基于基线应用版本', max_length=255, null=True)
    createDate = models.DateTimeField('创建时间', auto_now_add=True)
    progress = models.IntegerField('进度', default=0)
    devMode = models.CharField('开发模式', max_length=10, choices=(('aone', ('AoneFlow模式')), ('truck', ('Truck模式'))),
                               default="aone")
    desc = models.TextField('项目描述', null=True)

    def __unicode__(self):
        return self.name

    def status(self):
        if self.progress == 100:
            return 0

    def get_project_id(self):
        return self.id

    class Meta:
        permissions = (
            ("view_project_and_group", "view project and relative group"),
            ("create_release_branch", "create release branch"),
            ("create_app", "create app"),
            ("create_app_template", "create template"),
            ("delete_app_template", "delete template"),
            ("delete_app", "delete app"),
        )
class ProjectUser(models.Model):
    project = models.ForeignKey(Project,null=True)
    user=models.ForeignKey(User, null=True)
    is_manager=models.IntegerField('是否管理员',null=True)
    role = models.CharField("角色",max_length=255)

class App(models.Model):
    name = models.CharField(max_length=255)
    slugName = models.CharField('别名', max_length=255)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='项目')
    admin = models.ManyToManyField(User, related_name="app_admin", verbose_name='应用负责人')
    members = models.ManyToManyField(User, verbose_name='成员')
    config = models.TextField(verbose_name="应用配置")
    createDate = models.DateTimeField('创建时间', auto_now_add=True)
    langauge = models.CharField('语言', max_length=255, choices=(('java', ('Java')), ('nodejs', ('Nodejs'))),
                                default="java")
    desc = models.TextField('应用描述')
    triggerToken = models.CharField('CI trigger', max_length=255, null=True)
    jstreeData = models.TextField(null=True)
    projectId = models.CharField(max_length=255, null=True)

    class Meta:
        unique_together = (("name", "project"),)

    def __unicode__(self):
        return self.name


class Branch(models.Model):
    name = models.CharField('分支名', max_length=255)
    desc = models.CharField('功能描述', max_length=512)
    type = models.CharField('分支类型', max_length=255, default="feature")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='项目')
    createDate = models.DateTimeField('创建时间', auto_now_add=True)
    # version for release branch
    version = models.CharField('版本号', max_length=255, null=True)
    baseBranch = models.CharField('基于', max_length=255, null=True)
    projectFlag = models.IntegerField("是否项目feature", default=False)
    singleApp = models.CharField('选择应用', max_length=255, null=True)

    class Meta:
        permissions = (
            ("delete_feature_branch", "delete feature branch"),
        )

    def __unicode__(self):
        return self.name

    # class Meta:
    #     unique_together = (("name","app","project"),)


class  EnvTemplate(models.Model):
    name = models.CharField('环境模板', max_length=255)
    desc = models.CharField('环境描述', max_length=255)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='项目', null=True)
    featureApp = models.ManyToManyField(App, verbose_name='应用', null=True)
    baseApp = models.TextField(null=True)
    featureAppOrder = models.CharField('顺序', max_length=1024, null=True)
    envType = models.IntegerField('模板类型', default=1, null=False)
    branchName = models.CharField('分支名称', max_length=128)
    imageTag = models.CharField('镜像版本', max_length=128)
    appName = models.CharField('应用名称', max_length=128)
    appProject = models.CharField('应用所属的项目', max_length=128)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = (("name", "project"),)


class AppTree(models.Model):
    appName = models.CharField('基线应用名', max_length=255)
    jsonData = models.TextField(null=True)
    # 只有release/pro分支的代码才能提交基线项目pom结构
    proBranch = models.CharField('release/pro版本的分支', max_length=255, null=True)


class ImageVersion(models.Model):
    '''
     CI push app version
    '''
    name = models.CharField('名称', max_length=255)
    projectName = models.CharField('项目名', max_length=255)
    appName = models.CharField('应用名', max_length=255)
    branchName = models.CharField('分支名', max_length=255)
    repoAddress = models.CharField('镜像地址', max_length=255, null=True)
    chartAddress = models.CharField('Chart地址', max_length=255, null=True)
    domain = models.CharField('域名', max_length=255, null=True)
    containerPort = models.CharField('容器端口', max_length=32, null=True)
    servicePort = models.CharField('服务端口', max_length=32, null=True)
    createDate = models.DateTimeField('创建时间', auto_now_add=True)
    config = models.TextField(null=True)
    chartVersion = models.CharField('chart版本', max_length=255, null=True)
    baseAppFlag = models.IntegerField("是否基线应用", default=0, null=True)
    http = models.IntegerField('是否是http服务', default=0, null=True)
    randomPort = models.CharField('调试端口', max_length=255, null=True)

    def __unicode__(self):
        if self.repoAddress is None:
            return "no chart found"
        return self.repoAddress


class DataSetImage(models.Model):
    name = models.CharField('名称', max_length=255, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='项目', null=True)
    software = models.CharField('软件', max_length=255, choices=settings.DATASET, null=True)
    imageName = models.CharField('镜像', max_length=255, null=True)
    port = models.CharField('服务端口', max_length=32, null=True)
    chartTmpDir = models.CharField('chart临时安装目录', max_length=255, null=True)
    username = models.CharField('用户名', max_length=255, null=True)
    password = models.CharField('密码', max_length=255, null=True)
    flag = models.IntegerField('上传成功', default=False)
    randomPort = models.CharField('调试端口', max_length=255, null=True)
    domain = models.CharField('域名', max_length=255, null=True)

    # def save(self, *args, **kwargs):
    #
    #     ran = random.sample('abcdefghijklmnopqrstuvwxyz0123456ABCDEFGHIJKLMNOPQRSTUVWXYZ',int(8))
    #     ran = "".join(ran)
    #     self.imageName = "{harbor_url}/dataset/{project}-{name}:{ran}".format(harbor_url = settings.HARBOR_URL,
    #                                                                                      project = self.project,
    #                                                                                      name = self.name,
    #                                                                                      ran=ran)
    #     super(DataSet,self).save(*args, **kwargs)

    def __unicode__(self):
        return "dataset-image-%s" % (self.name,)

    class Meta:
        unique_together = (("name", "project"),)


class DataSet2(models.Model):
    name = models.CharField('名称', max_length=255, null=True)
    project_name = models.CharField('项目名', max_length=255, null=True)
    f = models.FileField("文件", upload_to='uploads/')
    user = models.CharField('用户', max_length=255, null=True)
    imageName = models.CharField('镜像', max_length=255, null=True)
    chartTmpDir = models.CharField('chart临时安装目录', max_length=255, null=True)
    flag = models.IntegerField('上传成功', default=False)
    image = models.IntegerField('是否为数据集image', default=False)
    createDate = models.DateTimeField('创建时间', auto_now_add=True)

    def __unicode__(self):
        if self.image:
            return "image-%s" % self.name
        else:
            return "%s" % (self.name)

    class Meta:
        unique_together = (("name", "image"),)

from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
@receiver(pre_delete, sender=DataSet2)
def mymodel_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.f.delete(False)


class Deployment(models.Model):
    # name = models.CharField('部署名', max_length=255)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='项目')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name='所属组', null=True)
    # branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name='分支')
    envName = models.CharField('环境名', max_length=255, unique=True, null=True)
    envDesc = models.CharField('环境描述', max_length=255, null=True)
    #envTemplate = models.ForeignKey(EnvTemplate, verbose_name='环境模板', null=True)
    envTemplate_name = models.CharField('环境摸板', max_length=255, null=True)
    envTemplate_id = models.IntegerField('环境模板', max_length=11, null=True)
    imageVersion = models.ManyToManyField(ImageVersion, verbose_name='版本名', null=True)
    # deployMode = models.CharField('部署模式', max_length=255, choices=(('new', ('新建实例')), ('replace', ('替换实例'))),default="new")
    #dataSet = models.ForeignKey(DataSet2, verbose_name='数据集', null=True)
    dataSet_id = models.IntegerField("数据集", max_length=255, null=True)
    deployDir = models.CharField('chart临时安装目录', max_length=255, null=True)
    commonApp = models.CharField('基础服务', max_length=255, null=True)
    zipPath = models.CharField('zip路径', max_length=255, null=True)
    userId = models.IntegerField('userid',max_length=11,null=True,default=0)
    dynamicEnv = models.CharField("环境变量",max_length=255,null=True)

    def __unicode__(self):
        return self.envName


class DeployHistory(models.Model):
    deploy = models.ForeignKey(Deployment, on_delete=models.CASCADE, verbose_name='项目', null=True)
    chartTmpDir = models.CharField('chart临时安装目录', max_length=255, null=True)
    msg = models.CharField('信息', max_length=255, null=True)
    createDate = models.DateTimeField('创建时间', auto_now_add=True)


class Limit(models.Model):
    user = models.ForeignKey(User, verbose_name='用户', null=True)
    group = models.ForeignKey(FGroup, verbose_name='用户组', null=True)
    resource = models.CharField('资源', max_length=255, choices=(('env', ('环境')),), default="env")
    limit = models.CharField("配额", max_length=255, default="3")


class ChartVersion(models.Model):
    projectName = models.CharField('项目', max_length=255, null=True)
    appName = models.CharField('应用', max_length=255, null=True)
    branchName = models.CharField('分支', max_length=255, null=True)
    version = models.CharField('版本', max_length=255, default="0.0.1")


class CommomAppServicePortMapping(models.Model):
    deploy = models.ForeignKey(Deployment, on_delete=models.CASCADE, null=True)
    commomAppName = models.CharField('应用名称', max_length=255, null=True)
    randomPort = models.CharField('随机名称', max_length=255, null=True)


class featureServicePortMapping(models.Model):
    deploy = models.ForeignKey(Deployment, on_delete=models.CASCADE, null=True)
    featureAppName = models.CharField('应用名称', max_length=255, null=True)
    port = models.CharField('端口', max_length=255, null=True)
    randomPort = models.CharField('随机名称', max_length=255, null=True)
    nodeIp = models.CharField('nodeIP', max_length=255, null=True)


class IngressData(models.Model):
    tcpService = models.TextField('tcpService', null=True)
    udpService = models.TextField('udpService', null=True)


class TagNum(models.Model):
    dateMonth = models.CharField('dateMonth', max_length=255, null=True)
    project_id = models.IntegerField('gitlab_project_id', null=True)
    num = models.IntegerField('num', default=1, null=True)
    tag_name = models.CharField('tag_name', max_length=255, null=True)
    pipeline_id = models.IntegerField('pipeline_id', default=1, null=True)
    branch_name  = models.CharField('branch_name', max_length=255, null=True)



class EnvTemplateList(models.Model):
    class Meta:
        db_table = 'app_envTemplateList'
    name = models.CharField('环境模板名', max_length=128, null=True)
    description = models.CharField('环境模板描述', max_length=128, null=True)
    project_id = models.IntegerField('项目id',max_length=11,null=True)
    env_type = models.IntegerField('环境',max_length=11,null=True,default=0)
    product_code = models.CharField('产品线简称', max_length=24, null=True)
    dataset_name = models.CharField('dataset_name',max_length=100,null=True)
    def __unicode__(self):
        return self.name

class Release_report_app(models.Model):
    class Meta:
        db_table = 'cmdb_release_report_app'
    app_item = models.CharField("app_item",max_length=100)
    app_name = models.CharField("an",max_length=100)
    app_project_name = models.CharField("pn",max_length=100)
    app_branch = models.CharField("branch",max_length=100)
    app_tag = models.CharField("tag",max_length=100)
    app_stage = models.CharField("stage",max_length=100)
    release_tag = models.CharField("re",max_length=100)

class EnvTemplateDetail(models.Model):
    class Meta:
        db_table = 'app_envTemplateDetail'
    templateList = models.ForeignKey(EnvTemplateList, max_length=6,null=True)
    appProject = models.CharField('appProject', max_length=128, null=True)
    appName = models.CharField('appName',max_length=128,null=True)
    branchName = models.CharField('分支名',max_length=128,null=True)
    imageTag = models.CharField('镜像tag', max_length=128, null=True)
    auto_update = models.IntegerField('auto_update',max_length=6,null=True,default=0)
    def __unicode__(self):
        return self.appName


#user_role
class Fpermission(models.Model):
    name = models.CharField("name",max_length=255)
    desc = models.CharField("权限描述",max_length=255,null=True)
    def __unicode__(self):
        return self.desc
class Role(models.Model):
    name = models.CharField("name",max_length=255)
    desc = models.CharField("role描述",max_length=255,null=True)
    project_name = models.CharField("项目名",max_length=255,null=True)
    user = models.ManyToManyField(User, verbose_name='用户', null=True)
    fpermission = models.ManyToManyField(Fpermission, verbose_name='权限', null=True)
    def __unicode__(self):
        return self.name
class RoleUser(models.Model):
    user_id = models.IntegerField("userid",max_length=10)
    role_id = models.IntegerField("roleid",max_length=10)
class RoleFpermission(models.Model):
    role_id = models.IntegerField("roleid",max_length=10)
    perm_id = models.IntegerField("permid",max_length=10)
