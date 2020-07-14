# coding=utf-8
from django.template import loader
from django.http import HttpResponse
from django.views.generic import ListView, CreateView, DeleteView, UpdateView, DetailView
from app.forms import *
from app.models import *
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login as auth_login
from django.urls import reverse_lazy
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group, Permission
from Api.ldapApi import Uldap
from Api.gitlabApi import Api
from Api.harborApi import HarborClient
from Api.k8sApi import K8sApi
from Api.dnsApi import DnsApi
from Api.get_url import check_url
import datetime
from Api.buildMysqlClient import build_mysqlClient
from models import FGroup
from helper import helper
from helper import deploy_nginx_chart
from guardian.shortcuts import assign_perm, remove_perm
import time
import traceback
import os
import sys
import socket
import random
import string
import shutil
from Api.updateDataSetImage import IncreUpdateDataSet

def index(request):
    context = {}
    template = loader.get_template('app/project_list.html')
    return HttpResponse(template.render(context, request))


def login_auth(request):
    context = None
    if request.method == 'POST':
        name = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=name, password=password)
        if user is not None:
            auth_login(request, user)
            url = reverse("project_list")
            return HttpResponseRedirect(url)
        else:
            context = {'error': u"ldap用户或密码错误"}
    return render(request, 'app/login.html', context)


def cas_test(request):
    ha = request

    return HttpResponseRedirect("url")


def log_out(request):
    logout(request)
    return HttpResponseRedirect(reverse("login"))


def reset_password(request):
    errors = ""
    if "username" in request.POST and "old_password" in request.POST and "new_password" in request.POST and "confirm_new_password":
        username = request.POST['username']
        old_password = request.POST['old_password']
        new_password = request.POST['new_password']
        confirm_new_password = request.POST['confirm_new_password']
        user = User.objects.get(username=username)
        if confirm_new_password != new_password:
            errors = "两次密码不一致"
        elif user.check_password(old_password):
            l = Uldap()
            rsn, msg = l.reset_password(username, new_password, old_password)
            if rsn:
                user.set_password(new_password)
                user.save()
                logout(request)
                return HttpResponseRedirect(reverse("login"))
            errors = msg
        else:
            errors = "旧密码错误"
    return render(request, 'app/reset_password_form.html', context={"error": errors})


# def search(request):
#     obj = request.GET.get("object")
#     keyword = request.GET.get("keyword")
#     try:
#         objs = eval(obj).object.all()


def gentella_html(request):
    context = {}
    # The template to be loaded as per gentelella.
    # All resource paths for gentelella end in .html.

    # Pick out the html file name from the url. And load that template.
    load_template = request.path.split('/')[-1]
    template = loader.get_template('app/' + load_template)
    return HttpResponse(template.render(context, request))


def host_to_ip(host):
    '''
    Returns the IP address of a given hostname

    CLI Example:

    .. code-block:: bash

        salt '*' network.host_to_ip example.com
    '''
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


class PermissionList(LoginRequiredMixin,ListView):
    template_name = "auth/permission_list.html"
    def get_queryset(self):
        users = User.objects.all()
        data=[]
        for user in users:
            if user.user_permissions.all():
                per=[]
                for p in user.user_permissions.all():
                    per.append(p.name.encode())
                data.append({"user":user,"permission":per})
        return data

class PermissionCreate(LoginRequiredMixin, CreateView):
    # form_class = PermissionCreateForm
    def get(self,request):
        users = User.objects.all()
        permissions = Permission.objects.all()
        return render(request,"auth/permission_create_form.html",{"users":users,"permissions":permissions})
    def post(self, request, *args, **kwargs):
        user = request.POST.get("user")
        permission = request.POST.get("permission")
        userobj = User.objects.get(username=user)
        a=permission.split("|")[-1].encode().strip()
        permissionobj = Permission.objects.get(name=a)
        userobj.user_permissions.add(permissionobj)
        # return render(request,"auth/permission_list.html")
        # return render(request,"app/index.html")
        url = reverse("user_permission_list")
        return HttpResponseRedirect(url)



class ProjectList(LoginRequiredMixin, ListView):
    model = Project
    template_name = "project/project_list.html"

    def get_queryset(self):
        keyword = self.request.GET.get("keyword", "")
        rsn = []
        user = self.request.user
        if keyword:
            projects = Project.objects.filter(
                Q(name__contains=keyword) | Q(slugName__contains=keyword))
        else:
            projects = Project.objects.all()
        filter_projects = []
        # if not user.is_superuser:
        #     for project in projects:
        #         if project.members.filter(username=user.username).exists():
        #             filter_projects.append(project)
        #         if project.admin.filter(username=user.username).exists():
        #             filter_projects.append(project)
        #     projects = set(filter_projects)
        #     projects = list(projects)

        for project in projects:
            tmp_members = []
            tmp_admin = []
            members = project.members.all()
            admins = project.admin.all()
            for member in members:
                tmp_members.append(member.last_name)
            for admin in admins:
                tmp_admin.append(admin.last_name)
            # rsn.append({"id":project.id,
            #             "name":project.name,
            #             "slugName":project.slugName,
            #             "progress":project.progress,
            #             "admin":",".join(tmp_admin),
            #             "members":",".join(tmp_members),
            #             "devMode":project.devMode})
            rsn.append({"id": project.id,
                        "name": project.name,
                        "slugName": project.slugName,
                        "desc": project.desc,
                        "progress": project.progress,
                        "admin": ",".join(tmp_admin),
                        "members": ",".join(tmp_members),
                        'baseAppVersion': project.baseAppVersion})
        return rsn
    def get_context_data(self,**kwargs):
        user = self.request.user
        userProject = ProjectUser.objects.filter(user_id=user.id)
        userPro=[]
        for i in userProject:
            userPro.append(i.project.name)
        context = super(ProjectList, self).get_context_data(**kwargs)
        context['userProject']=userPro
        context['all_project']=['evo-baseapp']
        return context


class ProjectCreate(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "project/project_form.html"

    def get_form(self):
        form = super(ProjectCreate, self).get_form()
        form.fields['desc'].required = False
        return form

    def post(self, request, *args, **kwargs):
        error = None
        data = request.POST.copy()
        if "jstree_data" in data:
            data.pop("jstree_data")
        form = self.form_class(data)

        if form.is_valid():
            l = Api()
            group_path = "software/evo-projects/" + \
                         form.cleaned_data.get("name")
            rsn = l.search_group(form.cleaned_data.get(
                "name"), full_path=group_path)
            # gilab ops
            if not rsn:
                rsn = l.custom_create_group(group_name=form.cleaned_data.get(
                    "name"), full_path="software/evo-projects", desc=form.cleaned_data.get("slugName"))
                for key in settings.GITLAB_VARIABLE:
                    l.set_group_variable(group_name=form.cleaned_data.get(
                        "name"), key=key, value=settings.GITLAB_VARIABLE[key], full_path=group_path)
                if rsn:
                    project = form.save()
                    project.desc = project.slugName
                    project.save()
                    manager_obj = Role.objects.create(name = "项目开发经理" , desc = "项目开发经理", project_name = project.name)
                    dev_obj = Role.objects.create(name = "项目研发" , desc = "项目研发", project_name = project.name)
                    pro_obj = Role.objects.create(name = "项目产品" , desc = "项目产品", project_name = project.name)
                    permission_branch = Fpermission.objects.get(name = "branch_all")
                    permission_envT = Fpermission.objects.get(name = "envtemplate_all")
                    permission_deploy = Fpermission.objects.get(name = "deploy_all")
                    permission_projectuser = Fpermission.objects.get(name = "projectuser_all")
                    permission_release_select_app = Fpermission.objects.get(name = "release_select_app")
                    permission_release_add = Fpermission.objects.get(name = "release_add")
                    permission_release_edit = Fpermission.objects.get(name = "release_edit")
                    permission_release_select = Fpermission.objects.get(name = "release_select")
                    permission_release_app_add = Fpermission.objects.get(name = "release_app_add")
                    permission_release_app_edit = Fpermission.objects.get(name = "release_app_edit")
                    permission_release_app_select = Fpermission.objects.get(name = "release_app_select")
                    permission_cmdb_select = Fpermission.objects.get(name = "cmdb_select")

                    manager_obj.fpermission.add(permission_branch,permission_envT,permission_deploy,permission_projectuser,
                                                permission_release_app_add,permission_release_app_edit,permission_cmdb_select,
                                                permission_release_select,permission_release_app_select,permission_release_select_app)
                    dev_obj.fpermission.add(permission_envT, permission_deploy,permission_cmdb_select,permission_release_select_app,
                                                permission_release_select,permission_release_app_select)
                    pro_obj.fpermission.add(permission_deploy,permission_release_add,permission_release_edit,permission_cmdb_select,
                                                permission_release_select,permission_release_app_select,permission_release_select_app)
                    manager_obj.save()
                    dev_obj.save()
                    pro_obj.save()

            else:
                error = "项目代码仓库已经存在，请联系管理员"
                return render(request, self.template_name, {'form': form, 'error': error, 'create': True})
            # create harbor
            h = HarborClient()
            h.create_project(project.name)

            url = reverse("project_list")
            response = HttpResponseRedirect(url)
            response.set_cookie("project_id", project.id)
            return response
        return render(request, self.template_name, {'form': form, 'create': True})



class RoleList(LoginRequiredMixin,ListView):
    template_name = "auth/role_list.html"
    model = Role

class RoleCreate(LoginRequiredMixin, CreateView):
    def get(self,request):
        projects = Project.objects.all()
        return render(request,"auth/role_create_form.html",{"projects":projects})
    def post(self, request, *args, **kwargs):
        role = request.POST.get("role")
        desc = request.POST.get("desc")
        project = request.POST.get("project")
        roleobj = Role.objects.create(
            name=role,
            desc=desc,
            project_name=project
        )
        url = reverse("user_role_list")
        return HttpResponseRedirect(url)

class RoleDelete(LoginRequiredMixin, DeleteView):
    model = Role
    success_url = reverse_lazy('user_role_list')
    template_name = "auth/role_confirm_delete.html"

class RoleUserList(LoginRequiredMixin,ListView):
    template_name = "auth/role_user_list.html"
    def get_queryset(self):
        ##明天需要pk来设置到某一个用户
        ##这里需要一个role_user而不是user_role
        role_id = self.kwargs["pk"]
        role = Role.objects.get(id=role_id)
        user = role.user.all()
        return user
    def get_context_data(self, **kwargs):
        context = super(RoleUserList, self).get_context_data(**kwargs)
        role_id = self.kwargs["pk"]
        context["role_id"] = role_id
        context["role_name"] = Role.objects.get(id=role_id).name
        return context

class RoleUserCreate(LoginRequiredMixin,CreateView):
    def get(self,request,pk):
        users = User.objects.all()
        return render(request,"auth/roleUser_create_form.html",{"users":users})
    def post(self, request, *args, **kwargs):
        user = request.POST.get("user")
        user = User.objects.filter(username = user)[0]
        role_id = kwargs["pk"]
        roleobj = Role.objects.get(id = role_id)
        roleobj.user.add(user)
        if roleobj.project_name != "global":
            project_name = roleobj.project_name
            project_id = Project.objects.get(name=project_name).id
            ProjectUser.objects.create(
                project_id = project_id,
                user_id = user.id,
            )
        url = reverse("role_user_list",kwargs={"pk":role_id})
        return HttpResponseRedirect(url)

class RoleUserDelete(LoginRequiredMixin, DeleteView):
    def get(self, request,rid,uid):
        user = User.objects.get(id = uid)
        return render(request, "auth/roleUser_confirm_delete.html", {"user": user.username,"role_id":rid})

    def post(self, request, *args, **kwargs):
        user_id = kwargs["uid"]
        user = User.objects.get(id=user_id)
        role_id = kwargs["rid"]
        role = Role.objects.get(id=role_id)
        role.user.remove(user)
        url = reverse("role_user_list", kwargs={"pk": role_id})
        return HttpResponseRedirect(url)

class RolePermList(LoginRequiredMixin,ListView):
    template_name = "auth/role_perm_list.html"
    def get_queryset(self):
        # perm = Fpermission.objects.all()
        role_id = self.kwargs["pk"]
        role = Role.objects.get(id=role_id)
        perm = role.fpermission.all()
        return perm
    def get_context_data(self, **kwargs):
        context = super(RolePermList, self).get_context_data(**kwargs)
        role_id = self.kwargs["pk"]
        context["role_id"] = role_id
        context["role_name"] = Role.objects.get(id=role_id).name
        return context

class RolePermCreate(LoginRequiredMixin,CreateView):
    def get(self,request,pk):
        perms = Fpermission.objects.all()
        return render(request,"auth/rolePerm_create_form.html",{"perms":perms})
    def post(self, request, *args, **kwargs):
        perm = request.POST.get("perm")
        print "abcdefgabcdefg{}".format(perm)
        perm = Fpermission.objects.filter(desc = perm)[0]
        role_id = kwargs["pk"]
        roleobj = Role.objects.get(id = role_id)
        roleobj.fpermission.add(perm)
        url = reverse("role_perm_list",kwargs={"pk":role_id})
        return HttpResponseRedirect(url)


class RolePermDelete(LoginRequiredMixin, DeleteView):
    def get(self, request,rid,pid):
        perm = Fpermission.objects.get(id = pid)
        return render(request, "auth/rolePerm_confirm_delete.html", {"perm": perm.name,"role_id":rid})

    def post(self, request, *args, **kwargs):
        perm_id = kwargs["pid"]
        perm = Fpermission.objects.get(id=perm_id)
        role_id = kwargs["rid"]
        role = Role.objects.get(id=role_id)
        role.fpermission.remove(perm)
        url = reverse("role_perm_list", kwargs={"pk": role_id})
        return HttpResponseRedirect(url)

class FpermisssionList(LoginRequiredMixin,ListView):
    template_name = "auth/fpermission_list.html"
    model = Fpermission

class FpermisssionCreate(LoginRequiredMixin, CreateView):
    def get(self,request):
        return render(request,"auth/fpermission_create_form.html")
    def post(self, request, *args, **kwargs):
        fperm = request.POST.get("fperm")
        desc = request.POST.get("desc")
        fpermobj = Fpermission.objects.create(
            name=fperm,
            desc=desc,
        )
        url = reverse("fpermission_list")
        return HttpResponseRedirect(url)

class FpermisssionDelete(LoginRequiredMixin, DeleteView):
    model = Fpermission
    success_url = reverse_lazy('fpermission_list')
    template_name = "auth/fpermission_confirm_delete.html"


class ProjectDetail(LoginRequiredMixin, DetailView):
    model = Project
    form_class = ProjectForm
    template_name = "project/project_detail.html"

    def get_context_data(self, **kwargs):
        keyword = self.request.GET.get("keyword", "")
        object_name = self.request.GET.get("object", "")
        error = self.request.GET.get("error", "")
        rsn = []
        context = super(ProjectDetail, self).get_context_data(**kwargs)
        if keyword and object_name == "app":
            apps = App.objects.filter(project__id=self.kwargs['pk']).filter(
                Q(name__contains=keyword) | Q(slugName__contains=keyword))
        else:
            apps = App.objects.filter(project__id=self.kwargs['pk']).all()
        for app in apps:
            tmp_members = []
            tmp_admin = []
            members = app.members.all()
            admins = app.admin.all()
            for member in members:
                tmp_members.append(member.last_name)
            for admin in admins:
                tmp_admin.append(admin.last_name)
            rsn.append({"id": app.id,
                        "name": app.name,
                        "slugName": app.slugName,
                        # "version": app.version.version,
                        "admin": ",".join(tmp_admin),
                        "members": ",".join(tmp_members)})
        # for envTemplate
        context['apps'] = rsn
        if keyword and object_name == "envtemplate":
            envTemplates = EnvTemplate.objects.filter(project__id=self.kwargs['pk']).filter(
                Q(name__contains=keyword) | Q(desc__contains=keyword))
        else:
            envTemplates = EnvTemplate.objects.filter(
                project__id=self.kwargs['pk']).all()
        envT = []
        feature_apps = []

        for env in envTemplates:
            feature_apps = env.featureApp.all()
            feature_apps = [fapp.name for fapp in feature_apps]

            envT.append({"id": env.id,
                         "name": env.name,
                         "desc": env.desc,
                         "featureApp": ",".join(feature_apps),
                         "baseApp": env.baseApp})
            feature_apps = None
        # for branch
        if keyword and object_name == "branch":
            branchs = Branch.objects.filter(project__id=self.kwargs['pk']).filter(
                Q(name__contains=keyword) | Q(desc__contains=keyword))
        else:
            branchs = Branch.objects.filter(
                project__id=self.kwargs['pk']).all()
        branchT = []
        # for branch in branchs:
        #     branchT.append({"name":branch.name,
        #                     "desc":branch.desc,
        #                     "type":branch.type,
        #                     "id":branch.id,
        #                     "singleApp":branch.singleApp})
        project_name=Project.objects.get(id=self.kwargs['pk']).name

        deploys = Deployment.objects.filter(
            project__id=self.kwargs['pk']).values()
        Ndeploys=[]
        for deploy in deploys:
            if deploy['userId']:
                user_name = User.objects.get(id = deploy['userId']).username
            else:
                user_name = User.objects.get(id = 5).username
            deploy['user_name']=user_name
            Ndeploys.append(deploy)

        roles = Role.objects.filter(project_name=project_name)
        # role_manager = Role.objects.filter(project_name=project_name,name="项目开发经理")
        # role_manager = [role.name for role in role_manager]

        for deploy in deploys:
            deploy["memory"] = None
            deploy["cpu"] = None

        project_roles = Role.objects.filter(project_name=project_name)
        user_roles = []
        for i in project_roles:
            if self.request.user in i.user.all():
                user_roles.append(i.name)

        context["role"] = user_roles
        context["QAAS_CMDB"] = settings.QAAS_CMDB
        context["requestUser_id"] = self.request.user.id
        context["deploys"] = Ndeploys
        context["roles"] = roles
        context["envTemplates"] = envT
        context["branchs"] = branchs
        context['project_id'] = self.kwargs['pk']
        context["project_name"] = project_name
        context["gitlab_prefix"] = "evo" if self.get_object(
        ).name == "evo" else "evo-projects"
        context["gitlab_url"] = settings.GITLAB_URL
        context["error"] = error
        return context

    def get(self, request, *args, **kwargs):
        response = super(ProjectDetail, self).get(request, *args, **kwargs)
        response.set_cookie("project_id", self.get_object().id)
        return response


class ProjectDelete(LoginRequiredMixin, DeleteView):
    model = Project
    success_url = reverse_lazy('project_list')
    template_name = "project/project_confirm_delete.html"

    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        # l = Api()
        # l.delete_group(self.get_object().name,full_path="software/"+self.get_object().name)

        ldap = Uldap()
        ldap.delete_group(self.get_object().name)
        ldap.delete_group2(self.get_object().name)

        d = HarborClient()
        d.delete_project(project.name)

        # delete project permission
        remove_perm("create_release_branch",
                    self.request.user, self.get_object())
        remove_perm("create_app", self.request.user, self.get_object())
        remove_perm("delete_app", self.request.user, self.get_object())
        remove_perm("create_app_template",
                    self.request.user, self.get_object())
        remove_perm("delete_app_template",
                    self.request.user, self.get_object())
        return super(ProjectDelete, self).delete(request, *args, **kwargs)


class ProjectUpdate(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "app/project_form.html"

    def get_success_url(self):
        return reverse("project_list")


# class AppList(LoginRequiredMixin, ListView):
#     model = App
#
#     def get_context_data(self,**kwargs):
#         context = super(AppList,self).get_context_data(**kwargs)
#         project = Project.objects.get(pk=self.kwargs['project_id'])
#         context['project'] = project
#         return context

class ProjectuserAdd(LoginRequiredMixin,CreateView):
    model = ProjectUser
    form_class = ProjectUserForm
    template_name = "project/projectUser_form.html"
    def get_form(self):
        form = super(ProjectuserAdd, self).get_form()
        form.initial = {"project": self.kwargs["pk"]}
        form.fields['project'].queryset = Project.objects.filter(id=self.kwargs["pk"])
        form.fields['user'].queryset = User.objects.all()
        return form
    #def get_success_url(self):
    #    return reverse_lazy("project_detail",kwargs={"pk":self.kwargs['pk']})
    def post(self,request,*args,**kwargs):
        data = request.POST.copy()
        form = self.form_class(data)
        if form.is_valid():
            obj=form.save()
            obj.save()
        url = reverse("project_detail",kwargs={"pk":self.kwargs['pk']})
        return HttpResponseRedirect(url)

class ProjectuserDelete(LoginRequiredMixin, DeleteView):
    model = ProjectUser
    template_name = "project/projectUser_confirm_delete.html"

    def get_success_url(self):
        projectuser_id = self.kwargs['pk']
        project_id = ProjectUser.objects.get(id=projectuser_id).project.id
        return reverse("project_detail",kwargs={"pk":project_id})



class AppCreate(LoginRequiredMixin, CreateView):
    model = App
    def get(self,request,project_id):
        project = Project.objects.get(id=project_id)
        return render(request,"app/app_form.html",{"project":project.name})

    def post(self, request, *args, **kwargs):
        app_name = request.POST.get("app_name")
        app_desc = request.POST.get("app_desc")
        app_project = request.POST.get("app_project")
        project_mvn = request.POST.get("project_mvn")
        project_id = Project.objects.get(name=app_project).id
        project = Project.objects.get(id=project_id)
        if app_project == "evo-baseapp":
            return False
        else:
            full_path = "evo-projects/{}".format(app_project)
        l = Api()
        group_id = l.get_group_id("software/{}".format(full_path))
        if not l.get_project_id("software/{}/{}".format(full_path,app_name)):
            rsn = l.create_project_in_group(name=app_name, group_id=group_id)
        else:
            error = "项目代码仓库已经存在，请联系管理员"
            return render(request, "app/app_form.html", {'error': error,"project":project.name})
        if rsn:
            projectId = l.get_project_id("software/{}/{}".format(full_path,app_name))
            obj = App.objects.create(name=app_name, slugName="{}/{}".format(full_path,app_name),
                                     desc=app_desc,project_id=project_id,projectId=projectId)
            if "interface" not in app_name and "printer" not in app_name or not project_mvn:
                url = reverse("project_detail", kwargs={"pk": project_id})
                return HttpResponseRedirect(url)
            else:
                project_mvn = "".join(project_mvn.split("\\\r\n"))
                with open("{}/tmp/{}_{}_expect.sh".format(settings.PROJECT_ROOT,app_project,app_name), 'w') as f:
                    f.write('#!/bin/expect\nspawn {}\nexpect " Y:*"\nsend "y\\r"\ninteract'.format(project_mvn))
                os.system('cd {}/tmp && expect {}_{}_expect.sh && sleep 10'.format(settings.PROJECT_ROOT,
                                                                                   app_project,app_name))
                commit_message = l.create_project_commit(project_id=projectId, ref="master", commit_message=
                             "first commit",commit_dir="{}/tmp/{}".format(settings.PROJECT_ROOT,app_name))
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="mvn gitlab commit message-{}".format
                                                                      (commit_message))
                os.system("cd {}/tmp && /bin/rm -rf {} && /bin/rm -rf {}_{}_expect.sh".format
                          (settings.PROJECT_ROOT,app_name,app_project,app_name))
                if commit_message:
                    url = reverse("project_detail", kwargs={"pk": project_id})
                    return HttpResponseRedirect(url)
                else:
                    error = "项目代码提交失败，请联系管理员"
                    return render(request, "app/app_form.html", {'error': error, "project": project.name})
        else:
            error = "项目代码仓库创建失败，请联系管理员"
            return render(request, "app/app_form.html", {'error': error, "project": project.name})



# class AppDetail(LoginRequiredMixin, DetailView):
#     model = App
#     form_class = AppForm
#
#     def get_context_data(self, **kwargs):
#         context = super(AppDetail, self).get_context_data(**kwargs)
#         branch = Branch.objects.filter(app__id=self.get_object().id)
#         context['branchs'] = branch
#         return context


class AppDelete(LoginRequiredMixin, DeleteView):
    model = App

    def delete(self, request, *args, **kwargs):
        project = self.get_object().project
        # l = Api()
        # l.delete_project(project.name,self.get_object().name,full_path="software/"+project.name)
        return super(AppDelete, self).delete(self, request, *args, **kwargs)

    def get_success_url(self):
        return reverse("project_detail", kwargs={"pk": self.get_object().project.pk})


class AppUpdate(LoginRequiredMixin, UpdateView):
    model = App
    form_class = AppForm

    def get_form(self):
        form = super(AppCreate, self).get_form()
        form.fields['members'].queryset = App.objects.get(
            id=self.kwargs['project_id']).members
        form.fields['admin'].queryset = App.objects.get(
            id=self.kwargs['project_id']).admin
        return form

    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs={"pk": self.get_object().project.pk})


class UserCreate(PermissionRequiredMixin,LoginRequiredMixin, CreateView):
    permission_required = "app.add_user"
    model = User
    form_class = UserForm
    template_name = "auth/user_form.html"

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            l = Uldap()
            u = form.save()
            u.set_password(u.password)
            u.save()
            l.create_ldapuser(form.data['username'], form.data['password'])
            groups = u.groups.all()
            for group in groups:
                l.add_group_member(group.name, u.username)
                l.add_group2_member(group.name, u.username)
            l.conn.unbind()
            UserProfile.objects.create(
                user=u, maxDeployNum=form.data['maxDeployNum'], currentDeployNum=0)
            url = reverse("user_list")
            return HttpResponseRedirect(url)

        return render(request, self.template_name, {'form': form, 'create': True})


class UserList(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "app.list_user"
    model = User
    template_name = "auth/user_list.html"

    def get_queryset(self):
        rsn = []
        users = User.objects.all()
        ##刷新用户环境数量
        deploys = Deployment.objects.all()
        userIds = [int(deploy.userId) for deploy in deploys]
        userid_dict = {}
        for userid in userIds:
            if userid not in userid_dict.keys():
                userid_dict[userid]=1
            else:
                userid_dict[userid]+=1
        for i in userid_dict.keys():
            user = User.objects.get(id=i)
            user.profile.currentDeployNum=userid_dict[i]
            user.profile.save()

        for user in users:
            if hasattr(user, "profile"):
                maxDeployNum = user.profile.maxDeployNum
                currentDeployNum = user.profile.currentDeployNum
                if currentDeployNum:
                    currentDeployNum = user.profile.currentDeployNum
                else:
                    currentDeployNum = 0
            else:
                maxDeployNum = 3
                currentDeployNum = 0
            if user.is_superuser:
                maxDeployNum = "super"
            tmp_group = []
            groups = user.groups.all()
            for group in groups:
                tmp_group.append(group.name)
            rsn.append({"id": user.id, "username": user.username,
                        "last_name": user.last_name,
                        "email": user.email,
                        "groups": ",".join(tmp_group),
                        'maxDeployNum': maxDeployNum,
                        'currentDeployNum': currentDeployNum})
        return rsn


class UserDelete(PermissionRequiredMixin,LoginRequiredMixin, DeleteView):
    permission_required = "app.list_user"
    model = User
    success_url = reverse_lazy('user_list')

    def post(self, request, *args, **kwargs):
        l = Uldap()
        l.delete_user(self.get_object().username)
        l.delete_group_memberuid(self.get_object().username)
        l.delete_group2_memberuid(self.get_object().username)
        l.conn.unbind_s()
        super(UserDelete, self).delete(self, request, *args, **kwargs)
        url = reverse("user_list")
        return HttpResponseRedirect(url)


class UserUpdate(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm

    # template_name = "app/user_form.html"

    def get_success_url(self):
        return reverse("user_list")


class GroupCreate(LoginRequiredMixin, CreateView):
    model = FGroup
    form_class = FGroupForm
    # form_class = GroupProfileFrom
    template_name = "auth/group_form.html"

    def post(self, request, *args, **kwargs):
        field_error = None
        form = self.form_class(request.POST)
        if form.is_valid():
            p = form.save()
            GroupProfile.objects.create(group=p, maxDeployNum=10)
            url = reverse("group_list")
            return HttpResponseRedirect(url)

        if len(form.errors) > 0:
            field_error = form.errors["__all__"]
        return render(request, self.template_name, {'form': form, 'field_error': field_error, 'create': True})


class groupQuotaDetail(LoginRequiredMixin,DetailView):
    model = Group
    template_name = "auth/group_quota_list.html"

    def get_context_data(self,**kwargs):
        group = self.get_object()
        deploys = Deployment.objects.all()
        Gdeploys = []
        for deploy in deploys:
            user = User.objects.get(id=deploy.userId)
            if user.groups.all():
                dgroup = user.groups.all()[0]
            else:
                continue
            if dgroup.name == group.name:
                l = K8sApi()
                time = l.get_namespace_time(deploy.envName)
                Gdeploys.append({
                    "envName": deploy.envName.encode(),
                    "envDesc": deploy.envDesc.encode(),
                    "user": user.last_name.encode(),
                    "time": ",".join(time.values()) if time else "",
                })
        data={"deploy":Gdeploys}
        return data


class GroupList(LoginRequiredMixin, ListView):
    model = FGroup
    template_name = "auth/group_list.html"

    def get_queryset(self):
        deploys = Deployment.objects.all()
        users = [deploy.userId for deploy in deploys]
        groups = Group.objects.all()
        group_dict = {}
        for group in groups:
            group_dict[group.name.encode()]=0
        for user in users:
            uobj = User.objects.get(id=user)
            if uobj.groups.all():
                ugroup = uobj.groups.all()[0].name
            else:
                continue
            if ugroup in group_dict.keys():
                group_dict[ugroup]+=1
        for group in group_dict.keys():
            gobj = Group.objects.get(name = group)
            gobj.group_profile.currentDeployNum = group_dict[group]
            gobj.group_profile.save()
        groups = []
        if self.request.user.is_superuser:
            groups = FGroup.objects.all()
        else:
            groups = FGroup.objects.filter(user=self.request.user)
        return groups


class GroupDelete(LoginRequiredMixin, DeleteView):
    model = Group
    success_url = reverse_lazy('group_list')
    template_name = "auth/group_confirm_delete.html"

    def post(self, request, *args, **kwargs):
        l = Uldap()
        l.delete_group(self.get_object().name)
        l.delete_group2(self.get_object().name)
        l.conn.unbind_s()
        super(GroupDelete, self).delete(self, request, *args, **kwargs)
        url = reverse("group_list")
        return HttpResponseRedirect(url)


class GroupDetail(LoginRequiredMixin, DetailView):
    model = FGroup
    form_class = FGroupForm
    # form_class = GroupProfileFrom
    template_name = "auth/group_detail.html"


class GroupUpdate(LoginRequiredMixin, UpdateView):
    model = FGroup
    form_class = FGroupForm
    # form_class = GroupProfileFrom
    template_name = "auth/group_form.html"

    def get_success_url(self):
        return reverse("group_list")


class BranchCreate(LoginRequiredMixin, CreateView):
    model = Branch
    form_class = BranchForm
    template_name = "branch/branch_form.html"

    def get_form(self):
        form = super(BranchCreate, self).get_form()
        form.initial = {
            "project": self.kwargs["project_id"], "type": self.kwargs["type"]}
        form.fields['project'].queryset = Project.objects.filter(
            id=self.kwargs["project_id"])
        form.fields['singleApp'].queryset = App.objects.filter(
            project__id=self.kwargs["project_id"])
        form.fields['projectFlag'].required = False

        project = Project.objects.get(id=self.kwargs["project_id"])
        if not Branch.objects.filter(project__id=self.kwargs["project_id"], name="master").exists():
            Branch.objects.create(name="master",
                                  type="master",
                                  version="",
                                  project=project,
                                  desc="master",
                                  baseBranch="master",
                                  projectFlag=True)

        form.fields['baseBranch'].queryset = Branch.objects.filter(
            Q(project__id=self.kwargs["project_id"]), (Q(name__startswith="master") | Q(name__contains="tag")))
        # if self.kwargs["type"] == "release":
        #     form.initial = {
        #                     "project": self.kwargs["project_id"],
        #                     "type": self.kwargs["type"],
        #                     "baseBranch":"master",
        #                 }
        return form

    def get_context_data(self, **kwargs):
        context = super(BranchCreate, self).get_context_data(**kwargs)
        context["type"] = self.kwargs["type"]
        return context

    def post(self, request, *args, **kwargs):
        error = ""
        # project = Project.objects.get(id=self.kwargs["project_id"])
        data = request.POST.copy()
        if data['desc'].find(" ") != -1:
            url = reverse("project_detail", kwargs={
                "pk": self.kwargs["project_id"]})
            url = url + "?error=branch name have error"
            return HttpResponseRedirect(url)
        project = Project.objects.get(id=self.kwargs["project_id"])

        # if self.kwargs["type"] == "release":
        #     # for suffix in ["pro","integration"]:
        #     branch_name = "release/%s"%(data['desc'])
        #     if not Branch.objects.filter(project__id=self.kwargs["project_id"],  name=branch_name).exists():
        #         helper.createReleaseBranch(project_id=self.kwargs["project_id"], branch_name=branch_name,version=data['version'])
        if self.kwargs["type"] == "tag":
            baseBranch = Branch.objects.get(id=data["baseBranch"])
            data['name'] = data["desc"]
            if 'projectFlag' in data and data['projectFlag'] == 'on':
                helper.createTagBy(
                    project_id=self.kwargs["project_id"], tag_name=data["name"], ref=baseBranch.name)
                Branch.objects.create(name=data["name"],
                                      type=self.kwargs["type"],
                                      version="",
                                      project=project,
                                      desc=data["desc"],
                                      baseBranch=baseBranch.name,
                                      projectFlag=True)
            else:
                baseBranch = Branch.objects.get(id=data["baseBranch"])
                app_id = data["singleApp"]
                app = App.objects.get(id=app_id)
                helper.createSingleAppTag(
                    tag_name=data["name"], ref=baseBranch.name, project_id=self.kwargs["project_id"], app_id=app_id)
                Branch.objects.create(
                    name=data["name"],
                    type=self.kwargs["type"],
                    desc=data["desc"],
                    version="",
                    project=project,
                    singleApp=app.name,
                    baseBranch=baseBranch.name)

        elif self.kwargs["type"] == "hotfix":
            featureName = helper.generateFuncBranch(
                hotfix="hotfix", desc=data["desc"])
            data["name"] = featureName
            data["type"] = self.kwargs["type"]
            data["project_id"] = self.kwargs["project_id"]
            app_id = data["singleApp"]
            app = App.objects.get(id=app_id)
            ###########################################
            # below "master" has error
            ###########################################
            helper.createSingleAppBranch(
                "master", featureName, self.kwargs["project_id"], app_id)
            b = Branch.objects.create(
                name=data["name"],
                type=data["type"],
                desc=data["desc"],
                version=data["version"],
                project=project,
                singleApp=app.name)
        else:
            baseBranch = Branch.objects.get(id=data["baseBranch"])
            featureName = None
            if self.kwargs["type"] == "feature":
                featureName = helper.generateFuncBranch(desc=data["desc"])
            elif self.kwargs["type"] == "release":
                featureName = "release/" + data["desc"]
            data["name"] = featureName
            data["type"] = self.kwargs["type"]
            data["version"] = baseBranch.version
            data["project_id"] = self.kwargs["project_id"]

            if 'projectFlag' in data and data['projectFlag'] == 'on':
                data['projectFlag'] = 1
            else:
                data['projectFlag'] = 0

            if data['projectFlag']:
                helper.createBranchBy(
                    baseBranch.name, featureName, self.kwargs["project_id"])
                Branch.objects.create(name=data["name"],
                                      type=data["type"],
                                      version=data["version"],
                                      project=project,
                                      desc=data["desc"],
                                      baseBranch=baseBranch.name,
                                      projectFlag=True)
            else:
                app_id = data["singleApp"]
                app = App.objects.get(id=app_id)
                helper.createSingleAppBranch(
                    baseBranch.name, featureName, self.kwargs["project_id"], app_id)
                b = Branch.objects.create(
                    name=data["name"],
                    type=data["type"],
                    desc=data["desc"],
                    version=data["version"],
                    project=project,
                    singleApp=app.name,
                    baseBranch=baseBranch.name)
                assign_perm('delete_feature_branch', self.request.user, b)
                # users = User.objects.filter(is_superuser=True)
                # for user in users:
                #     assign_perm('delete_feature_branch', user, b)

        url = reverse("project_detail", kwargs={
            "pk": self.kwargs["project_id"]})
        return HttpResponseRedirect(url)


class BranchDelete(LoginRequiredMixin, DeleteView):
    model = Branch
    # success_url = reverse_lazy('project_list')
    template_name = "branch/branch_confirm_delete.html"

    def delete(self, request, *args, **kwargs):
        if self.get_object().projectFlag == 1:
            helper.deleteBranchby(
                self.kwargs['project_id'], self.get_object().name)
        else:
            helper.deleteSingleAppBranch(
                self.kwargs['project_id'], self.get_object().name, self.get_object().singleApp)

        return super(BranchDelete, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("project_detail", kwargs={"pk": self.kwargs["project_id"]})


class EnvTemplateCreate(LoginRequiredMixin, CreateView):
    model = EnvTemplate
    form_class = EnvTemplateForm
    # success_url = reverse_lazy('project_list')
    template_name = "envTemplate/envTemplate_form.html"

    def get_form(self):
        form = super(EnvTemplateCreate, self).get_form()
        form.fields["featureApp"].queryset = App.objects.filter(
            project__id=self.kwargs["project_id"])
        return form

    def get_context_data(self, **kwargs):
        context = super(EnvTemplateCreate, self).get_context_data(**kwargs)
        context["project_id"] = self.kwargs['project_id']
        return context

    def post(self, request, *args, **kwargs):
        error = None
        data = request.POST.copy()
        baseApp = request.POST.getlist("baseApp")
        baseApp_branch = request.POST.getlist("baseApp_branch")
        new_baseapp = []
        for i in baseApp:
            base_list = i.split(':')
            key = base_list[1]
            base_list[1] = baseApp_branch[int(key.encode('utf-8'))]
            new_baseapp.append(":".join(base_list))
        baseApp = ",".join(new_baseapp)
        data["baseApp"] = baseApp

        featureApp = request.POST.getlist("featureApp")
        fapps = [App.objects.get(id=fapp_id) for fapp_id in featureApp]

        form = self.form_class(data)
        # form.is_valid　method　invalid　,bugfix later
        if form.is_valid():
            try:
                p = EnvTemplate.objects.create(name=data["name"],
                                               desc=data['desc'],
                                               project=Project.objects.get(
                                                   id=data["project_id"]),
                                               baseApp=data["baseApp"])
                if fapps:
                    for fapp in fapps:
                        p.featureApp.add(fapp)
                    p.save()
                url = reverse("project_detail", kwargs={
                    "pk": request.POST["project_id"]})
                return HttpResponseRedirect(url)
            except Exception, e:
                url = reverse("project_detail", kwargs={
                    "pk": request.POST["project_id"]})
                url = url + "?error=" + str(e)
                return HttpResponseRedirect(url)

        else:
            error = form.errors
            return render(request, self.template_name,
                          {'form': form, 'project_id': request.POST.get("project_id"), 'error': error, 'create': True})


# class EnvTemplateList(LoginRequiredMixin,ListView):
#     model = EnvTemplate
#     template_name = "envTemplate/envTemplate_list.html"
def EnvEdit(request,pid,eid):
    env_name = EnvTemplate.objects.get(id=eid).name
    project_id = pid
    return render(request,'envTemplate/envEdit.html',{'env_name':env_name,'project_id':project_id})

def sys_release_list(request):
    return render(request,'envTemplate/sys_release.html',{'cmdb_ip':settings.CMDB})
def deploy_release_list(request):
    return render(request,'envTemplate/deploy_release.html',{'cmdb_ip':settings.CMDB})
def deploy_release_download(request):
    return render(request,'envTemplate/download_release.html',{'QAAS_CMDB':settings.QAAS_CMDB})
def preserverlist(request):
    return render(request,'envTemplate/preserverlist.html',{'QAAS_CMDB':settings.QAAS_CMDB})
def memoryconfig(request):
    return render(request,'envTemplate/memoryconfig.html',{'QAAS_CMDB':settings.QAAS_CMDB})

class EnvTemplateDelete(LoginRequiredMixin, DeleteView):
    model = EnvTemplate
    # success_url = reverse_lazy('project_list')
    template_name = "envTemplate/envTemplate_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs={"pk": self.get_object().project.pk})


class DeployCreate(LoginRequiredMixin, CreateView):
    model = Deployment
    form_class = DeployForm
    template_name = "deploy/deploy_form.html"

    def get_form(self):
        form = super(DeployCreate, self).get_form()
        # branchs = Branch.objects.filter(project__id=self.kwargs['project_id'])
        project = Project.objects.get(id=self.kwargs['project_id'])
        form.fields['project'].queryset = Project.objects.filter(
            id=self.kwargs['project_id'])
        
        xenv = EnvTemplateList.objects.filter(project_id=self.kwargs['project_id']).order_by("-env_type","-id")
        form.fields['envTemplate'].queryset = xenv
        #form.fields['envTemplate'].queryset = EnvTemplate.objects.filter(
        #    project__id=self.kwargs['project_id'])
        form.fields['group'].queryset = self.request.user.groups.all()
        # form.fields['branch'].queryset = Branch.objects.filter(project__id=self.kwargs['project_id'])
        # form.fields['baseAppVersion'].queryset = branchs

        # 选择数据集的数据来源
        form.fields['dataSet'].queryset = DataSet2.objects.filter(
            (Q(image=1) & Q(flag=1)) | Q(image=0))
        # form.fields['imageVersion'].queryset = ImageVersion.objects.filter(projectName=project.name)
        if self.request.user.is_superuser:
            form.initial = {"project": project,
                            "envName": "deploy-%s" % (int(time.time()))}
            form.fields['group'].queryset = Group.objects.all()
        else:
            form.initial = {"project": project, "envName": "deploy-%s" %
                                                           (int(time.time())),
                            "group": self.request.user.groups.all()[0]}
                #            "group": 'infra'}

        # if branchs:
        #     form.initial["baseAppVersion"] = branchs[0]
        # form.initial["branch"] = branchs[0]
        # if EnvTemplate.objects.filter(project__id=self.kwargs['project_id']).exists():
        #        form.initial["envTemplate"] = EnvTemplate.objects.filter(project__id=self.kwargs['project_id'])[0]
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="form: {}".format(form))

        return form

    def post(self, request, *args, **kwargs):
        project_id = request.POST.get("project")
        envName = request.POST.get("envName")
        envTemplate_id = request.POST.get("envTemplate")
        dataSet = request.POST.get("dataSet")
        commonApp = request.POST.getlist("commonApp")
	# 对必要字段值进行校验
	for needKey in ["project", "envName", "envTemplate", "dataSet"]:
	    if not request.POST.get(needKey):
                return render(request, "deploy/deploy_list.html",
                                  {'error': u"创建环境请求参数有误! 必要字段%s 数据为空!" % (needKey)})
        group = request.POST.get("group")
        new_images = []
        baseImages = []
        for item in request.POST.keys():
            if item.find("appapp-") != -1:
                baseImages.append(request.POST[item])

        if not request.user.is_superuser:
            group = Group.objects.get(id=group)
            if hasattr(group, "group_profile"):
                num = int(group.group_profile.currentDeployNum) + 1
                if num > int(group.group_profile.maxDeployNum):
                    return render(request, "deploy/deploy_list.html",
                                  {'error': u"您的环境数为%s,不能再创建新环境" % (group.group_profile.maxDeployNum,)})

            user = request.user
            if hasattr(user, "profile"):
                if user.profile.currentDeployNum:
                    num = int(user.profile.currentDeployNum) + 1
                    if num > int(user.profile.maxDeployNum):
                            return render(request, "deploy/deploy_list.html",
                                  {'error': u"您的环境数为%s,不能再创建新环境" % (user.profile.maxDeployNum,)})
                #num = int(user.profile.currentDeployNum) + 1
                #if num > int(user.profile.maxDeployNum):
                #    return render(request, "deploy/deploy_list.html",
                #                  {'error': u"您的环境数为%s,不能再创建新环境" % (user.profile.maxDeployNum,)})

        k = K8sApi()
        status = k.get_namespace_status(envName)
        if status == "Terminating":
            return render(request, "deploy/deploy_list.html", {'error': u"%s环境正在清理，请稍后创建" % (envName,)})

        data = request.POST.copy()
        if "commonApp" in data:
            data.pop("commonApp")
        error = None

        if baseImages:
            for iid in baseImages:
                tmp_image = ImageVersion.objects.get(id=iid)
                new_images.append(tmp_image)

        form = self.form_class(data)
        if form.is_valid():
            obj = form.save()
            for image in new_images:
                obj.imageVersion.add(image)

            # rsn3 = helper.deployBaseApp(obj.id)
            # rsn4 = deploy_nginx_chart.InstallNginxChart(envName, envTemplate_id)

            if commonApp:
                commonApp = ",".join(commonApp)
                obj.commonApp = commonApp
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="commonApp: {}".format(commonApp))

                obj.save()
            userobj = Deployment.objects.all().order_by('-id')[0]

            obj.envTemplate_name = EnvTemplateList.objects.get(id=envTemplate_id).name
            userobj.envTemplate_id = envTemplate_id
            userobj.userId = request.user.id
            userobj.save()

            try:
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="nginx chart dir is {} ".format(
                                                                          "{}/charts/nginx".format(
                                                                              settings.PROJECT_ROOT)))
                if not os.path.isdir("{}/charts/nginx".format(settings.PROJECT_ROOT)):
                    return render(request, "deploy/deploy_list.html", {'error': "nginx chart is not exits!"})

         #       k.create_namespace(obj.envName)
         #       print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
         #                                                             fileName=os.path.basename(__file__),
         #                                                             func=sys._getframe(
         #                                                             ).f_code.co_name,
         #                                                             num=sys._getframe().f_lineno,
         #                                                             args="obj.dataSet.imageName: {}".format(
         #                                                                 DataSet2.objects.get(id=obj.dataSet_id).imageName))

                rsn2 = helper.deployCommonApp(obj.id)
                if not rsn2:
                    k.delete_namespace(namespace=obj.envName)
                    helper.deleteDployTemplate(obj.id)
                    helper.deleteDeployCommonApp(obj.id)
                    helper.deleteDeployBaseApp(obj.id)
                    obj.delete()

                    return render(request, self.template_name,
                                  {'form': form, 'project_id': request.POST["project"], 'error': "创建common应用失败！",
                                   'create': True})
                    # return render(request, "deploy/deploy_list.html", {'error': ("\n").join(errors)})

                # 每次创建mysql chart，会生成一个新的pvc来存储mysql数据，因此原来的mysql数据就被清空了；所以必须要通过source sql文件的形式导入
                if dataSet:
                    rsn = helper.deployInitData(dataSet=dataSet, namespace=obj.envName)
                    if not rsn:
                        job_pod = k.list_pods_name(namespace=obj.envName, job_name="init-db")
                        if job_pod:
                            logs = k.get_pod_log(namespace=obj.envName, name=job_pod[0])
                            if logs:
                                k.delete_namespace(namespace=obj.envName)
                                helper.deleteDployTemplate(obj.id)
                                helper.deleteDeployCommonApp(obj.id)
                                helper.deleteDeployBaseApp(obj.id)
                                obj.delete()
                                raise logs
                                return render(request, self.template_name,
                                              {'form': form, 'project_id': request.POST["project"],
                                               'error': "创建初始化db client job失败！\n".format(logs), 'create': True})
                                # return render(request, "deploy/deploy_list.html", {'error': logs})

                rsn3 = helper.deployBaseApp(obj.id)
                if not rsn3:
                    k.delete_namespace(namespace=obj.envName)
                    helper.deleteDployTemplate(obj.id)
                    helper.deleteDeployCommonApp(obj.id)
                    helper.deleteDeployBaseApp(obj.id)
                    obj.delete()

                    return render(request, self.template_name,
                                  {'form': form, 'project_id': request.POST["project"],
                                   'error': "创建基础应用失败! ", 'create': True})

                    # return render(request, "deploy/deploy_list.html", {'error': ("\n").join(errors)})

                rsn4 = deploy_nginx_chart.InstallNginxChart(envName, envTemplate_id)
                if not rsn4:
                    k.delete_namespace(namespace=obj.envName)
                    helper.deleteDployTemplate(obj.id)
                    helper.deleteDeployCommonApp(obj.id)
                    helper.deleteDeployBaseApp(obj.id)
                    obj.delete()
                    return render(request, self.template_name,
                                  {'form': form, 'project_id': request.POST["project"],
                                   'error': "安装nginx chart失败! ", 'create': True})

                deploy_dir = "/tmp/%s" % (obj.envName)

                obj.deployDir = deploy_dir
                obj.userId = request.user.id
                obj.envTemplate_id = envTemplate_id
                obj.dataSet_id = dataSet
                obj.envTemplate_name = EnvTemplateList.objects.get(id=envTemplate_id).name
                obj.save()
                if not hasattr(request.user, "profile"):
                    UserProfile.objects.create(
                        user=request.user, currentDeployNum=0)
                request.user.profile.currentDeployNum = 1 if not request.user.profile.currentDeployNum else int(
                    request.user.profile.currentDeployNum) + 1
                request.user.profile.save()

                dns = DnsApi()
                if not host_to_ip(obj.envName):
                    dns.update(domain="{deploy_name}".format(deploy_name=envName),
                               hostIP=settings.DNS_HOST)

                # 尝试访问URL ，无法访问就再改成12
                if not check_url(url="{deploy_name}.flashhold.com".format(deploy_name=envName)):
                    dns.update(domain="{deploy_name}".format(deploy_name=envName),
                               hostIP=settings.DNS_HOST)

                groups = FGroup.objects.filter(user=request.user)
                for group in groups:
                    if hasattr(group, "group_profile"):
                        if group.group_profile.currentDeployNum is None or group.group_profile.currentDeployNum == 0:
                            group.group_profile.currentDeployNum = 1
                        else:
                            group.group_profile.currentDeployNum = group.group_profile.currentDeployNum + 1
                        group.group_profile.save()
                url = reverse("project_detail", kwargs={
                    "pk": self.request.COOKIES["project_id"]})

                return HttpResponseRedirect(url)

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

                helper.deleteDployTemplate(obj.id)
                helper.deleteDeployCommonApp(obj.id)
                helper.deleteDeployBaseApp(obj.id)
                k.delete_namespace(namespace=obj.envName)
                obj.delete()

        #            userobj = Deployment.objects.all().order_by('-id')[0]
        #            userobj.userId=request.user.id
        #            userobj.save()
        else:
            error = form.errors
        return render(request, self.template_name,
                      {'form': form, 'project_id': request.POST["project"], 'error': error, 'create': True})

@login_required()
def deployDetail(request,pk):
    deploy_id = pk
    namespace = Deployment.objects.get(id=pk).envName
    return render(request,'deploy/deploy_detail.html',{'deploy_id':deploy_id,'namespace':namespace,
                                                       "QAAS_CMDB":settings.QAAS_CMDB})


class DeployDetail(LoginRequiredMixin, DetailView):
    model = Deployment
    template_name = "deploy/deploy_detail.html"

    def get_context_data(self, **kwargs):
        deploy = self.get_object()
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="deploy:{}".format(deploy))

        context = super(DeployDetail, self).get_context_data(**kwargs)
        context["deploy"] = deploy

        imageVersions = deploy.imageVersion.all()

        l = K8sApi()

        data = {"dataSet": [], "commonApp": [], "baseApp": [], "tcpService": []}

        try:
            dataSetId = Deployment.objects.get(id=deploy.id).dataSet_id
            dataSet = DataSet2.objects.get(id=dataSetId)
        except:
            dataSet = None
        if dataSetId and dataSet:

            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="dataSetId :{}".format(
                                                                      dataSetId))

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
                "name": "数据集不存在，可能被删除-请联系管理员",
                "imageName": "数据集不存在，可能被删除-请联系管理员,如果您正在创建环境请稍后，环境没有创建完成",
                "status": "error"})


        baseImages = deploy.imageVersion.all().order_by('-createDate')
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="baseImages:{}".format(baseImages))

        base_app_str = []
        if baseImages:
            #base_app_str = []
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
                    "release_tag": release_name,
                    "image_name": imageVersion.name,
                    "branch_name": branch_name,
                    "commit_name": commit_name,
                    "image_repo": imageVersion.repoAddress,
                    "app_name": imageVersion.appName,
                    "image_chart": imageVersion.chartAddress,
                    "config": imageVersion.config,
                    "release_name": "%s-%s" % (deploy.envName, chart_name),
                    "deploy_status": "部署成功" if l.get_deployment_status(namespace=deploy.envName,
                                                                       name=imageVersion.appName) else "请稍等...",
                    "domain": "{envName}.flashhold.com".format(envName=deploy.envName),
                    "service_port": imageVersion.containerPort,
                    "chart_version": imageVersion.chartVersion,
                    "random_port": "80" if imageVersion.http else imageVersion.randomPort
                },
                )

                base_app_str.append(imageVersion.appName)

                if imageVersion.appName  in settings.TCPSERVERMAP.keys():
                    appName = imageVersion.appName
                    for port in settings.TCPSERVERMAP[appName]:
                       rs = helper.getRCSport(deploy_id=deploy.id, deploy_envName=deploy.envName, appName=appName, port=port)
                    #rs = helper.getRCSport(deploy_id=deploy.id, deploy_envName=deploy.envName, appName=imageVersion.appName)
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

                val = {"name": app,
                       "domain": "{}.flashhold.com".format(deploy.envName),
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

        deployHistorys = DeployHistory.objects.filter(
            deploy=deploy).order_by("-createDate")[0:10]

        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="deployHistorys : {}".format(deployHistorys))

        context["dataSet"] = data['dataSet']
        context["tcpService"] = data['tcpService']
        # context["featureApp"] = data['featureApp']
        context["baseApp"] = data['baseApp']
        context["commonApp"] = data['commonApp']
        context["deploy_history"] = deployHistorys
        context["baseApp_str"] = ",".join(base_app_str)
        #print(os.path.basename(__file__), sys._getframe(
        #).f_code.co_name, sys._getframe().f_lineno, "deploy.dataSet: ", DataSet2.objects.get(id=deploy.dataSet_id))
        context["dataset"] = None

        context["domain"] = "{envName}.flashhold.com".format(
            envName=deploy.envName)

        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="i'm here ~~, context['tcpService']: {}".format(context["tcpService"]))

        return context


class DeployDelete(LoginRequiredMixin, DeleteView):
    model = Deployment
    # success_url = reverse_lazy('project_list')
    template_name = "deploy/deploy_confirm_delete.html"

    def get_success_url(self):
        project_id = self.request.COOKIES['project_id']
        return reverse("project_detail", kwargs={"pk": project_id})

    def delete(self, request, *args, **kwargs):
        a=self.get_object().envTemplate_id
        try:
           if EnvTemplateList.objects.get(id=a):
               helper.deleteDployTemplate(self.get_object().id)
        except:
           pass
        #if self.get_object().envTemplate:
        #    helper.deleteDployTemplate(self.get_object().id)
        helper.deleteDeployBaseApp(self.get_object().id)
        helper.deleteDeployCommonApp(self.get_object().id)
        k = K8sApi()
        k.delete_namespace(self.get_object().envName)

        if hasattr(self.get_object().group, "group_profile"):
            group = self.get_object().group
            group.group_profile.currentDeployNum = group.group_profile.currentDeployNum - 1
            group.group_profile.save()

        helper.delete_release_random_port(self.get_object().envName)
        #curDeploy = Deployment.objects.filter(userId=request.user.id)
        #if hasattr(request.user, "profile"):
        #    if request.user.profile.currentDeployNum is None or request.user.profile.currentDeployNum <= 0:
        #        request.user.profile.currentDeployNum = 0
        #    else:
        #        request.user.profile.currentDeployNum = len(curDeploy)-1
        #    request.user.profile.save()
        if self.get_object().userId:
            user = User.objects.get(id = self.get_object().userId)
            curDeploy = Deployment.objects.filter(userId = self.get_object().userId)
            if hasattr(user, "profile"):
                if user.profile.currentDeployNum is None or user.profile.currentDeployNum <= 0:
                    request.user.profile.currentDeployNum = 0
                else:
                    request.user.profile.currentDeployNum = len(curDeploy)-1
                request.user.profile.save()
        return super(DeployDelete, self).delete(request, *args, **kwargs)

def deployDetailRedirect(request,pk):
    dname = "deploy-{}".format(pk)
    deploy = Deployment.objects.filter(envName=dname)
    if not deploy:
        url = reverse("project_list")
        return HttpResponseRedirect(url)
    pid = deploy[0].id
    url = reverse("deploy_detail", kwargs={"pk": pid})
    return HttpResponseRedirect(url)


class DeployList(LoginRequiredMixin, ListView):
    model = Deployment
    template_name = "deploy/deploy_list.html"

    def get_context_data(self, **kwargs):
        context = super(DeployList, self).get_context_data(**kwargs)
        context["projects"] = Project.objects.all()

        # deploys = Deployment.objects.all()
        # context["deploys"] = deploys
        return context


class DataSetCreate(LoginRequiredMixin, CreateView):
    model = DataSet2
    form_class = DataSetForm2
    success_url = reverse_lazy('dataset_list')
    template_name = "dataset/dataset_form.html"

    def get_context_data(self, **kwargs):
        context = super(DataSetCreate, self).get_context_data(**kwargs)
        projects = Project.objects.all()
        project_name=[]
        for i in projects:
            project_name.append(i.name)
        context['project_name'] = project_name
        return context

    def post(self, request, *args, **kwargs):
        project_name = request.POST['project_name']
        na = request.POST['name']
        user = request.user.username
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            try:
                p = form.save()
                fn = DataSet2.objects.get(name=na).f
                file_path = "{media_root}/{file_name}".format(
                    media_root=settings.MEDIA_ROOT, file_name=fn)

                tag_name = file_path.split("uploads/")[1].split('.sql')[0]

                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="DataSetCreate update file name:{}, tag_name:{} ".format(
                                                                          file_path, tag_name))

                ins = build_mysqlClient(dockerAddr=settings.DOCKER_SERVER, sqlFilePath=file_path)

                if ins:
                    p.imageName = '{}:{}'.format(settings.MYSQLCLIENT_IMAGE_BASE.split(':')[0], tag_name)
                    p.flag = 1
                    p.image = 1
                    p.save()
                    project_name = Project.objects.get(name=project_name).name
                    DataSet2.objects.filter(name=na).update(project_name=project_name)
                    DataSet2.objects.filter(name=na).update(user=user)
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="success to save data {}:{}  in dataset2. ".format(
                                                                              settings.MYSQL_IMAGE_BASE.split(':')[0],
                                                                              tag_name))


            except Exception as e:
                p.delete()
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="Exception when Create DataSet: %s\n" % e)

                return render(request, self.template_name,
                              {'form': form, 'error': e, 'create': False})

            # ran = random.sample('abcdefghijklmnopqrstuvwxyz0123456ABCDEFGHIJKLMNOPQRSTUVWXYZ', int(8))
            # ran = "".join(ran)
            # p.imageName = "{harbor_url}/dataset/{project}-{name}:{ran}".format(harbor_url=settings.HARBOR_URL,
            #                                                                       project=p.project,
            #                                                                       name=p.name,
            #                                                                       ran=ran)
            # p.save()
        else:
            error = form.errors
            return render(request, self.template_name,
                          {'form': form, 'error': error, 'create': False})

        url = reverse("dataset_list")
        return HttpResponseRedirect(url)


class DataSetList(LoginRequiredMixin, ListView):
    model = DataSet2
    template_name = "dataset/dataset_list.html"

    def get_queryset(self):
        # data = DataSet2.objects.filter(id > 0)
        data = DataSet2.objects.filter(Q(image=0) | Q(image=1))
        return data

    def get_context_data(self, **kwargs):
        context = super(DataSetList, self).get_context_data(**kwargs)
        context['datasets'] = DataSet2.objects.all()
        context['datasetss'] = DataSet2.objects.all()
        context["harbor_url"] = settings.HARBOR_URL
        context["devops_url"] = settings.DEVOPS_URL
        return context

class DataSetUpdate(LoginRequiredMixin, CreateView):
    model = DataSet2
    form_class = DataSetForm3
    template_name = "dataset/dataset2_form.html"
    success_url = reverse_lazy('dataset_list')

    def get_context_data(self,**kwargs):
        context = super(DataSetUpdate,self).get_context_data(**kwargs)
        dataset_name = DataSet2.objects.get(id=self.kwargs['pk']).name
        projects = Project.objects.all()
        project_name=[]
        for i in projects:
            project_name.append(i.name)
        context['dataset_name']=dataset_name
        context['project_name'] = project_name

        return context

    def post(self, request, *args, **kwargs):
        user = request.user.username
        na = DataSet2.objects.get(id=self.kwargs['pk']).name
        form = self.form_class(request.POST, request.FILES)
        project_name = request.POST['project_name']

        if form.is_valid():
            try:
                oldDatasetId = DataSet2.objects.get(name=na).id
                print "==========id{}===========".format(oldDatasetId)
                DataSet2.objects.filter(name=na).delete()
                p = form.save()
                p.name = na
                p.save()
                fn = DataSet2.objects.get(name=na).f
                file_path = "{media_root}/{file_name}".format(
                    media_root=settings.MEDIA_ROOT, file_name=fn)

                tag_name = file_path.split("uploads/")[1].split('.sql')[0]

                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="update file name:{}, tag_name:{} ".format(
                                                                          file_path, tag_name))

                ins = build_mysqlClient(dockerAddr=settings.DOCKER_SERVER, sqlFilePath=file_path)

                if ins:
                    p.imageName = '{}:{}'.format(settings.MYSQLCLIENT_IMAGE_BASE.split(':')[0], tag_name)
                    p.flag = 1
                    p.image = 1
                    p.save()
                    project_name = Project.objects.get(name=project_name).name
                    DataSet2.objects.filter(name=na).update(project_name=project_name)
                    DataSet2.objects.filter(name=na).update(user=user)
                    newDatasetId = DataSet2.objects.get(name=na).id
                    Deployment.objects.filter(dataSet_id=oldDatasetId).update(dataSet_id=newDatasetId)

                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="success to save data {}:{}  in dataset2. ".format(
                                                                              settings.MYSQL_IMAGE_BASE.split(':')[0],
                                                                              tag_name))
            except Exception as e:
#                p.form.delete()
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="Exception when Create DataSet: %s\n" % e)

                return render(request, self.template_name,
                              {'form': form, 'error': e, 'create': False})
        else:
            error = form.errors
            return render(request, self.template_name,
                          {'form': form, 'error': error, 'create': False})

        url = reverse("dataset_list")
        return HttpResponseRedirect(url)


class DataSetIncreUpdate(LoginRequiredMixin, CreateView):
    model = DataSet2
    form_class = DataSetForm2
    success_url = reverse_lazy('dataset_list')
    template_name = "dataset/dataset_increUpdate.html"

    def get_context_data(self, **kwargs):
        context = super(DataSetIncreUpdate, self).get_context_data(**kwargs)
        dataset_name = DataSet2.objects.get(id=self.kwargs['pk']).name
        projects = Project.objects.all()
        project_name = []
        for i in projects:
            project_name.append(i.name)
        context['project_name'] = project_name
        context['dataset_name'] = dataset_name
        return context

    def ranstr(self, num):
        salt = ''.join(random.sample(string.ascii_letters + string.digits, num))

        return salt

    def post(self, request, *args, **kwargs):
        project_name = request.POST['project_name']
        na = request.POST['name']
        user = request.user.username
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="request data, project_name:{}, data name :{} , user name: {}".format(
                                                                  project_name, na, user))
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            try:
                oldDataset = DataSet2.objects.get(name=na)
                DataSet2.objects.filter(name=na).delete()
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="旧DataSet id {} 数据删除, name: {}, f: {}, imageName: {}".format(
                                                                          oldDataset.id, oldDataset.name, oldDataset.f,
                                                                          oldDataset.imageName))
                p = form.save()
                # 名称、镜像tag不变，f变
                # p.f = oldDataset.f
                p.imageName = oldDataset.imageName
                p.name = na
                p.save()
                DataSet2.objects.filter(name=na).update(project_name=project_name)
                DataSet2.objects.filter(name=na).update(user=user)
                # oldFileName = DataSet2.objects.get(name=na).f
                # p = form.save()
                newDataset = DataSet2.objects.get(name=na)
                fn = newDataset.f
                # fn = DataSet2.objects.get(name=na).f
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="form保存后查询的 DataSet id {}, name: {}, f: {}, imageName: {}".format(
                                                                          newDataset.id, newDataset.name, newDataset.f,
                                                                          newDataset.imageName))
                file_path = "{media_root}/{file_name}".format(
                    media_root=settings.MEDIA_ROOT, file_name=fn)
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="media_root是: {}, 客户端上传文件的实际位置{} ".format(
                                                                          settings.MEDIA_ROOT, file_path))

                newFile = "{media_root}/{ranstr}/{file_name}".format(media_root=settings.MEDIA_ROOT,
                                                                     ranstr=self.ranstr(6), file_name=fn)

                newPath = newFile.split("uploads")[0] + "uploads"
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="sql文件新路径是: {} ".format(newFile))

                if not os.path.isdir(newPath):
                    os.makedirs(newPath)
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="成功创建新路径: {} ".format(newPath))

                #  创建一个特殊的目录，将sql文件拷贝过去
                try:
                    shutil.copy(file_path, newFile)
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="用shutil.copytree方法将sql文件 {} 复制到 {}成功".format(
                                                                              file_path, newFile))
                except  Exception as e:
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="用shutil.copytree方法将sql文件 {} 复制到 {}失败: {}".format(
                                                                              file_path, newFile, e))

                    return render(request, self.template_name,
                                  {'form': form, 'error': '复制原sql 文件到新的目录下失败', 'create': False})

                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="复制原sql {} 文件到新的SQL文件{} 成功.".format(
                                                                          file_path, newFile))

                tag_name = DataSet2.objects.get(name=na).imageName.split(':')[1].split('.sql')[0]

                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="DataSetCreate update file name:{}, tag_name:{} ".format(
                                                                          newFile, tag_name))

                ins = IncreUpdateDataSet(oldMysqlClientImageTag=tag_name, newSqlFilePath=newFile)

                if ins:
                    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                          fileName=os.path.basename(__file__),
                                                                          func=sys._getframe(
                                                                          ).f_code.co_name,
                                                                          num=sys._getframe().f_lineno,
                                                                          args="成功将sql脚本 {}合并并推送镜像: {}".format(newFile,
                                                                                                               tag_name))
                # p = form.save()
                # dataSetFile = "{},{}".format(fn,newFile.split("media")[1])
                # p.f = dataSetFile
                # p.save()

            except Exception as e:
                # p.f = oldFileName
                # p.save()
                print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                      fileName=os.path.basename(__file__),
                                                                      func=sys._getframe(
                                                                      ).f_code.co_name,
                                                                      num=sys._getframe().f_lineno,
                                                                      args="Exception when IncreUpdate DataSet: %s\n" % e)

                return render(request, self.template_name,
                              {'form': form, 'error': e, 'create': False})

            # ran = random.sample('abcdefghijklmnopqrstuvwxyz0123456ABCDEFGHIJKLMNOPQRSTUVWXYZ', int(8))
            # ran = "".join(ran)
            # p.imageName = "{harbor_url}/dataset/{project}-{name}:{ran}".format(harbor_url=settings.HARBOR_URL,
            #                                                                       project=p.project,
            #                                                                       name=p.name,
            #                                                                       ran=ran)
            # p.save()
        else:
            error = form.errors
            return render(request, self.template_name,
                          {'form': form, 'error': error, 'create': False})

        url = reverse("dataset_list")
        return HttpResponseRedirect(url)



class DataSetDelete(LoginRequiredMixin, DeleteView):
    model = DataSet2
    template_name = "dataset/dataset_confirm_delete.html"
    success_url = reverse_lazy('dataset_list')

    def delete(self, request, *args, **kwargs):
        # l = Api()
        # l = HarborClient()
        # _,imageName = self.get_object().imageName.split("/", 1)
        # repo,tag = imageName.split(":")
        # l.delete_tag_from_repository(repo,tag)
        return super(DataSetDelete, self).delete(request, *args, **kwargs)

def DataSetDownload(request, *args, **kwargs):
    dataset = DataSet2.objects.filter(id = kwargs.get("pk")).first()
    file = dataset.f
    response = HttpResponse(file)
    response['Content-Type'] = 'application/octet-stream'
    filename = str(file).split("/")[-1]
    response['Content-Disposition'] = 'attachment;filename="{}"'.format(filename)
    return response

class DataSetImageCreate(LoginRequiredMixin, CreateView):
    model = DataSet2
    form_class = DataSetImageForm
    success_url = reverse_lazy('dataset_image_list')
    template_name = "dataset_image/dataset_form.html"

    def get_form(self):
        form = super(DataSetImageCreate, self).get_form()
        form.initial = {
            "imageName": "harbor2.flashhold.com/dataset-image/dataset_image:" + helper.generateRandomString(12)}
        return form

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            p = form.save()
            p.image = 1
            p.save()
            # ran = random.sample('abcdefghijklmnopqrstuvwxyz0123456ABCDEFGHIJKLMNOPQRSTUVWXYZ', int(8))
            # ran = "".join(ran)
            # p.imageName = "{harbor_url}/dataset/{project}-{name}:{ran}".format(harbor_url=settings.HARBOR_URL,
            #                                                                       project=p.project,
            #                                                                       name=p.name,
            #                                                                       ran=ran)
            # p.save()
        else:
            error = form.errors
            return render(request, self.template_name,
                          {'form': form, 'error': error, 'create': True})
        url = reverse("dataset_image_list")
        return HttpResponseRedirect(url)


class DataSetImageList(LoginRequiredMixin, ListView):
    model = DataSet2
    template_name = "dataset_image/dataset_list.html"

    def get_queryset(self):
        data = DataSet2.objects.filter(image=1)
        return data

    def get_context_data(self, **kwargs):
        context = super(DataSetImageList, self).get_context_data(**kwargs)
        context["harbor_url"] = settings.HARBOR_URL
        context["devops_url"] = settings.DEVOPS_URL
        return context



class DataSetImageDelete(LoginRequiredMixin, DeleteView):
    model = DataSet2
    template_name = "dataset_image/dataset_confirm_delete.html"
    success_url = reverse_lazy('dataset_image_list')

    def delete(self, request, *args, **kwargs):
        # l = Api()
        # l = HarborClient()
        # _,imageName = self.get_object().imageName.split("/", 1)
        # repo,tag = imageName.split(":")
        # l.delete_tag_from_repository(repo,tag)
        return super(DataSetImageDelete, self).delete(request, *args, **kwargs)
# class ProDeployCreate(LoginRequiredMixin,CreateView):
#     model = Deployment
#     form_class = ProDeployForm
#     template_name = "deploy/pro_deploy_form.html"
#
#     def post(self, request, *args, **kwargs):
#         deploy_id = request.POST.get("deploy")
#         dc_file = request.POST.get("dc_file")
#         project_name = request.POST.get("project_name")
#         version = request.POST.get("version")
#         deploy = Deployment.objects.get(id=deploy_id)
#         images = deploy.imageVersion.all()
#         pattern = []
#         helper.build_docker_compose()
#         for image in images:
#             num = image.repoAddress.split(":")[-1].split("-")[-1]
#             num = "*%s"%num
#             pattern.append(num)
#         pattern = "|".join(pattern)
#         base_dir = "evo-baseapp %s %s"%(deploy.project.name,dcf)
#         cmd = 'cd /devops && ls {dir}|grep -E "{pattern}"|xargs zip -r -q -o {project}.zip'.format(dir=base_dir,
#                                                                                                    pattern=pattern,
#                                                                                                    project="%s-%s"%(project_name,version))
#         os.system(cmd)
#         deploy.zipPath = "/devops/{project}.zip".format(project="%s-%s"%(project_name,version))
#         deploy.save()
#         url = reverse("pro_deploy_add")
# return render(request, "deploy/pro_deploy_form.html", {'msg':
# u"打包文件在%s"%deploy.zipPath})
