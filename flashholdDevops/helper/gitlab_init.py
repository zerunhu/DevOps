import os,sys
from Api.gitlabApi import Api
from Api.ldapApi import Uldap
import gitlab
sys.path.append("/opt/flashhold-devops/flashholdDevops")



if __name__ == "__main__":
    import django
    django.setup()
    from app.models import *
    git = Api()
    users = git.get_users()
    ldap = Uldap()
    for user in users:
        if not User.objects.filter(username=user["username"]):
            uobj = User.objects.create(username=user["username"],email="%s@flashhold.com"%user["username"])
            uobj.set_password("123456")
            rsn,msg = ldap.search_user(uobj.username)
            if not rsn:
                ldap.create_ldapuser(uobj.username,"123456")
        else:
            uobj = User.objects.filter(username=user["username"])[0]
            uobj.last_name = user["username"]
            uobj.save()

    for item in ["a51050",'a51043','a51028','a51051','a31024-002','a31030-002','a51040']:
        d = git.search_group(item)
        if not Project.objects.filter(name=item):

            pobj = Project.objects.create(name=item,slugName="evo-projects/"+item,desc=d.description)
        else:
            pobj = Project.objects.filter(name=item)[0]
            pobj.desc = d.description
            pobj.save()

        projects = git.get_group_project(item)
        admins = []
        users = []
        for project in projects:
            if project.name.find("-plugin") != -1:
                continue
            app_name = pobj.slugName + "/" + project.name
            if not App.objects.filter(name=project.name,project=pobj):
                nobj = App.objects.create(
                    name=project.name,
                    slugName=app_name,
                    project=pobj,
                    projectId=project.id
                )
        # nobj = App.objects.get(name=app_name,project=pobj)
        # project = git.get_project_instance(nobj.projectId)
        # members = project.members.all(all=True)
        # for member in members:
        #     user = User.objects.filter(username=member['username'])
        #     if user:
        #         user = user[0]
        #         if member['access_level']==gitlab.OWNER_ACCESS:
        #             admins.append(user)
        #         elif member['access_level']==gitlab.DEVELOPER_ACCESS:
        #             users.append(user)
        # admins = list(set(admins))
        # users = list(set(users))
        # for admin in admins:
        #     nobj.admin.add(admin)
        # for user in users:
        #     nobj.members.add(user)
        # nobj.save()