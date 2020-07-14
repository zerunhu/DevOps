#coding=utf-8
import sys
sys.path.append("/opt/flashhold-devops/flashholdDevops")
import gitlab
import base64,logging
from app.models import *
import json
from pprint import pprint
import os
import datetime
from django.conf import settings
from gitlab import GitlabCreateError

class Api(object):
    def __init__(self):
        # self.gl = gitlab.Gitlab(url=settings.GITLAB_URL, private_token=settings.GITLAB_PRIVATE_TOKEN)
        self.gl = gitlab.Gitlab(url="http://git.flashhold.com:10080", private_token="cznnk5B7eyjpBXbHPY7G",per_page=1000)
        self.baseapp_tree= []

    def get_groups(self):
        gps = self.gl.groups.list()

        ret = []
        if gps:
            for g in gps:
                item = {
                    "id": g.id,
                    "name": g.name,
                }
                ret.append(item)
            return ret
        else:
            return ret
    def get_group_id(self,full_path=""):
        try:
            group = self.gl.groups.get(full_path)
            if group:
                return group.id
        except:
            return False
    def get_group_tree(self,group,parrent="#"):
        if group:
            if parrent == "#":
                self.baseapp_tree.append({"id": "group_" + str(group.id), "text": group.name, "parent": "#"})
            try:
                subgroups = group.subgroups.list()
                if subgroups:
                    for subgroup in subgroups:
                        self.baseapp_tree.append({"id":"group_"+str(subgroup.id),"text":subgroup.name,"parent":"group_"+str(group.id)})
                        self.get_group_tree(subgroup,parrent=group.id)
            except AttributeError:
                projects = self.get_group_projects(group.id)
                if projects:
                    for project in projects:
                        if project['name'].endswith("-plugin"):
                            continue
                        self.baseapp_tree.append({"id":"project_"+str(project['id']),"text":project['name'],"parent":"group_"+str(group.id)})
        return

    def get_group_members(self, group_name,full_path=""):
        group = self.get_group_detail(group_name,full_path=full_path)
        if group:
            members = []
            for m in group.members.list():
                members.append(m.attributes)
            return members
        else:
            return "group_name may not exist"

    def get_runners(self):
        return self.gl.runners.list()

    def get_runner(self,run_id=22):
        runner = self.gl.runners.get(run_id).token
        return runner

    def create_runner(self,token="1AzXhmEktJsQUWbBz6SD"):
        runner = self.gl.runners.create({'token': token})
        return runner


    def delete_group_member(self, group_name, username):
        group = self.get_group_detail(group_name,full_path="software/"+group_name)
        user = self.get_user_detail(username)

        try:
            group.members.delete(user.id)
            return True
        except Exception as e:
            print(e)
            return False

    def delete_group(self,group_name,full_path=""):
        group = self.get_group_detail(group_name,full_path=full_path)
        if group:
            try:
                self.gl.groups.delete(group.id)
                return True
            except:
                return False
    def get_group_detail(self, group_name,full_path=None):
        group = self.search_group(group_name,full_path=full_path)
        return group

    def get_group(self,group_id):
        group = self.gl.groups.get(group_id)
        return group

    def search_group(self, group_name=None,full_path=""):
        gps = self.gl.groups.list(search=group_name)
        if gps:
            for gp in gps:
                if gp.full_path == full_path:
                    return gp
            if full_path:
                return False
            else:
                return gps[0]
        else:
            return False

    def create_group(self, group_name, path):
        try:
            g = self.gl.groups.create({"name": group_name, "path": path})
            if g:
                return True
            else:
                return False
        except Exception as e:
            logging.error(e)
            return False

    def create_group_by_manual(self, name=None, path=None,parent_id=None,desc=None):
        try:
            g = self.gl.groups.create({"name": name, "path": path,"parent_id":parent_id,'description':desc})
            if g:
                return g
            else:
                return False
        except Exception as e:
            logging.error(e)
            return False



    def add_group_member(self, username, group_name,admin=False,full_path=""):
        try:
            group = self.get_group_detail(group_name,full_path=full_path)
            user = self.get_user_detail(username)
            if group and user:
                if admin:
                    group.members.create({'user_id': user.id,
                                      'access_level': gitlab.OWNER_ACCESS})
                else:
                    group.members.create({'user_id': user.id,
                                          'access_level': gitlab.DEVELOPER_ACCESS})
            return True
        except Exception as e:
            if e.__getattribute__("response_code") == 409:
                print str(e)
                return True
            return False


    def get_template_project(self,language="java"):
        group_id = self.get_group_detail("template",full_path="software/template").id
        projects = self.get_group_projects(group_id)
        if language:
            for project in projects:
                if project['name'] == language:
                    return project
        return projects[0]

    def get_merge_request(self,project_id):
        project = self.gl.projects.get(project_id)
        return project.mergerequests.get(4)

    def create_merge_request(self,project_id=None,source_branch=None,target_branch=None,title=None,author=None,assignee=None):
        # author = self.search_user(author)
        # assignee = self.search_user(assignee)
        project = self.gl.projects.get(project_id)
        mr = project.mergerequests.create({'source_branch': source_branch,
                                           'target_branch': target_branch,
                                           'title': title,
                                           'author':author,
                                           'assignee':assignee})

    def create_protected_branch(self,project_id=None,branch_name="release-*"):
        project = self.gl.projects.get(project_id)
        try:
            project.protectedbranches.create({
                'name': branch_name,
                'merge_access_level': gitlab.MAINTAINER_ACCESS,
                'push_access_level': gitlab.MAINTAINER_ACCESS
            })
        except:
            pass
        return True

    def get_baseapp_project(self,app=""):
        group = self.get_group_detail("evo-baseapp",full_path="software/evo-baseapp")
        projects = self.get_group_projects(group.id)
        data = []
        if app:
            for project in projects:
                if project['name'] == app:
                    return project
        else:
            for project in projects:
                data.append((project['name'],project['name']))
            return data

    def get_group_project(self,group_name):
        group = self.get_group_detail(group_name,full_path="software/evo-projects/%s"%group_name)
        group = self.gl.groups.get(group.id)
        if group:
            projects = group.projects.list()
        return projects

    def get_baseapp_tree(self):
        pass

    def get_or_create_trigger(self,project_id):
        project = self.gl.projects.get(project_id)
        trigger_decription = 'mytrigger'
        for t in project.triggers.list():
            if t.description == trigger_decription:
                return t.token
        obj = project.triggers.create({'description': trigger_decription})
        return obj.token

    def get_group_projects(self, group_id=0,):
        group = self.gl.groups.get(group_id)

        if group:
            objects = group.projects.list()
            projects = []
            for p in objects:
                item = {
                    "id": p.id,
                    "name": p.name,
                    "path": p.path_with_namespace,
                    "description": p.description,
                    "last_activity_at": p.last_activity_at
                }
                projects.append(item)
            return projects

        else:
            return None



    def get_project(self, project_id=None):
        if project_id:
            return self.gl.projects.get(project_id).attributes
        else:
            return "project id or name is required"

    def get_project_instance(self, project_id=None):
        if project_id:
            return self.gl.projects.get(project_id)
        else:
            return "project id or name is required"

    def get_group_project_by_name(self,group_name='',project_name='',full_path=""):
        group = self.search_group(group_name,full_path=full_path)
        projects = self.get_group_projects(group.id)
        for project in projects:
            if project['name'] == project_name:
                return project
        return None

    def create_project_in_group(self, name=None, group_id=None):
        try:
            return self.gl.projects.create({'name': name, 'namespace_id': group_id}).attributes
        except Exception as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when create_project_in_group: {}".format(e) )

            return False

    def create_project_with_fork(self, template_id=None, target_namespace=None, new_name=None):

        try:

            project = self.gl.projects.get(template_id)
            if project:
                ret = project.forks.create({'namespace': target_namespace})
                np = self.gl.projects.get(ret.id)
                np.name = new_name
                np.path = new_name
                np.save()
                np.delete_fork_relation()
                self.__update_ci(np.id, company=target_namespace.split("/")[-1])
                return True,np

                #     return None
            else:
                print("project_id is wrong")
                return False,''
        except Exception as e:
            print("create project failed: {e}".format(e=e))
            return False,''

    # update new fork project gitlab-ci file
    def __update_ci(self, project_id=None, company=None):
        try:
            project = self.gl.projects.get(project_id)

            if project:
                f = project.files.get(file_path=".gitlab-ci.yml", ref='master')
                de_cont = f.decode().decode("utf-8")
                rep_cont = de_cont.replace("{{COMPANY}}", company).replace('"evo-baseapp"',company)
                f.content = base64.b64encode(bytes(rep_cont))
                f.save(branch='master', commit_message='Update .gitlab-ci.yml file', encoding='base64')
                return True

            else:
                print("project id maybe wrong")
                return False

        except Exception as e:
            print("update_ci error: {}".format(e))
            return False

    def create_project_commit(self,project_id="",ref="",commit_message="",commit_dir=""):
        dirs = os.popen("find {} -type f".format(commit_dir)).read().split("\n")[:-1]
        actions = []
        for dir in dirs:
            create = {
                'action': 'create',
                'file_path': "/".join(dir.split('/')[7:]),
                'content': open(dir).read()
            }
            actions.append(create)
        data = {
            'branch': ref,
            'commit_message': commit_message,
            'actions': actions
        }
        try:
            project = self.gl.projects.get(project_id)
            commit = project.commits.create(data)
            if commit:
                return commit
            return False
        except Exception as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when create_project_in_group: {}".format(
                                                                      e))

            return False

    def create_project_tag(self, project_id="",tag_name="",ref=""):
        p = self.gl.projects.get(project_id)
        if p:
            p.tags.create({'tag_name': tag_name, 'ref': ref})

            return True
        return False

    def get_project_tag(self,project_id):
        p = self.gl.projects.get(project_id)
        tags = p.tags.list(all=True)
        data = []
        for tag in tags:
            data.append(tag.name)
        print data
        return data

    def create_project_branch(self, project_id="",origin_branch_name='',target_branch_name=''):
        p = self.gl.projects.get(project_id)
        if p:
            try:
                p.branches.create({'branch': target_branch_name, 'ref': origin_branch_name})
            except GitlabCreateError:
                p.branches.create({'branch': origin_branch_name, 'ref': "master"})
                p.branches.create({'branch': target_branch_name, 'ref': origin_branch_name})
            return True
        return False

    def delete_project_branch(self, project_id="",branch_name=""):
        p = self.gl.projects.get(project_id)
        if p:
            p.branches.delete(branch_name)
            return True
        return False

    def search_project_branch(self, project_id="",branch=""):
        p = self.gl.projects.get(project_id)
        if p:
            b = p.branches.list(search=branch)
            if b:
                return True
            else:
                return False
        return False

    def list_project_branch(self, lujin):
        slug = '/'.join(['software', lujin])
        p = self.gl.projects.get(slug)
        b = p.branches.list()
        if b:
            return b
        else:
            return False

    def list_baseapp_branch(self, lujin):
        p = self.gl.projects.get(lujin)
        b = p.branches.list()
        branches_name=[]
        for i in b:
            branches_name.append(i.name.encode('utf-8'))
        return branches_name

    def get_branches(self,branch_id,lujin):
        slug = '/'.join(['software', lujin])
        p = self.gl.projects.get(slug)
        b = p.branches.get(branch_id)
        return b

    def delete_project(self,group_name,project_name,full_path=""):
        project = self.get_group_project_by_name(group_name,project_name,full_path=full_path)
        if project and type(project) is not list:
            try:
                self.gl.projects.delete(project['id'])
                return True
            except :
                return False
    def delete_projects(self,id):
        self.gl.projects.delete(id)
        return True

    def delete_project_by_id(self,id):
        try:
            self.gl.projects.delete(id)
            return True
        except :
            return False

    def get_users(self):
        users = self.gl.users.list(all=True)
        users_list = []

        for u in users:
            item = {
                "id": u.id,
                "name": u.name,
                "username": u.username
            }
            users_list.append(item)
        return users_list
    def get_project_id(self,fullpath):
        try:
            p = self.gl.projects.get(fullpath).id
            if p:
                return p
            else:
                return False
        except Exception as e:
            print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                                  fileName=os.path.basename(__file__),
                                                                  func=sys._getframe(
                                                                  ).f_code.co_name,
                                                                  num=sys._getframe().f_lineno,
                                                                  args="Exception when get_projects_id: {}".format(e))

            return False

    # user = {
    #         "name" : "李雷(李垒)",
    #         "username" : "leili",
    #         "password" : "leili11111",
    #         "email" : "leili@yoozoo.com",
    #         "provider" : "ldapmain",
    #         "skip_confirmation":True,
    #         "extern_uid" : "cn=李雷(李垒),ou=技术资源平台,ou=上海游族信息技术有限公司,dc=uz,dc=local",
    #         "can_create_project" : True
    # }
    def create_user(self, user):
        try:
            u = self.gl.users.create(user).attributes
            if u:
                return True
            else:
                return False
        except Exception as e:
            logging.error(e)
            return False

    def add_user_to_project(self, project_id=None, user_name=None):
        user = self.get_user_detail(user_name)
        project = self.gl.projects.get(project_id)
        if project:
            return project.members.create({'user_id': user.id,
                                           'access_level': gitlab.DEVELOPER_ACCESS}).attributes
        else:
            return " project_id is wrong"

    def get_project_members(self,project_id=None):
        project = self.gl.projects.get(project_id)
        members = project.members.list()
        data = []
        for member in members:
            data.append({
                "username":member.username,
                "access_level":member.access_level,
            })
        return data

    def search_user(self, username):
        user = self.gl.users.list(search=username)
        if user:
            return user
        return False

    def delete_user(self, user_id):
        try:
            return self.gl.users.delete(user_id)
        except Exception as e:
            logging.error(e)
            return None

    def get_user_detail(self, username):
        user = self.gl.users.list(search=username)
        if user:
            return user[0]
        else:
            return False

    def set_group_variable(self,group_name="",key="",value="",full_path=""):
        group = self.get_group_detail(group_name,full_path=full_path)
        group.variables.create({'key': key, 'value': value})

    def get_namespace(self,search=None):
        data = []
        if search:
            items = self.gl.namespaces.list(search=search)
        else:
            items = self.gl.namespaces.list()
        for item in items:
            data.append({"id":item.id,"name":item.name,"path":item.path})
        return data

    def custom_create_group(self,group_name="",full_path="",desc=None):
        group = self.search_group("evo-projects",full_path=full_path)
        new_group = self.create_group_by_manual(name=group_name, path=group_name, parent_id=group.id,desc=desc)
        return new_group

    def get_project_compose_content(self,lujin):
        resource_slug = '/'.join(['software', lujin,'resource'])
        project = self.gl.projects.get(resource_slug)
        f = project.files.get(file_path='docker-compose.yml', ref='master')
        content = f.decode()
        return content

if __name__ == '__main__':

    username='root'
    git = Api()
    print git.get_project(project_id=84)['name']
    # print git.search_group("A51050")
    # print git.get_group_project_by_name(group_name="infra",project_name="registry")
    # print git.get_group_detail("infra")
    # project = git.get_template_project("java")
    # git.create_project_with_fork(project['id'],"test","example-java")

    # git.create_project_branch(13,"")

    # git.get_project_by_name("demo")

    # project=git.get_group_project_by_name("华为",'demo')
    # git.create_project_branch(project_id=project['id'],target_branch_name="release-pro/v2.0.0",origin_branch_name="master")
    # print git.get_merge_request(39)
    # print git.create_merge_request(project_id=39,author="nibin",title="this is a test",assignee="huqing",source_branch="feature-1554874256",target_branch="release/integration/v1.0.0")
    # git.set_group_variable("huawei",key="test",value="value")
    # pprint(git.get_group_detail(group_name="evo-baseApp"))
    # git.create_project_with_fork(template_id=11,target_namespace="baseApp",new_name="rcs1")
    # git.create_group(group_name="evo-baseapp",path="evo-baseapp")
    # pprint(git.get_group_projects(346))
    ###################################################################################
    # members = git.add_group_member("nibin","software",admin=True,full_path="software")
    # print group
    # group = git.get_groups()
    # group = git.search_group("template",full_path="software/template")
    # project = git.get_project(711)
    # pprint(project)
    # git.get_group_tree(group)
    # # web = git.get_group_subgroups("evo-baseapp/web")
    # data = git.baseapp_tree
    # pprint(data)
    # pprint(git.get_group_projects(211))
    # pprint(git.get_project(158))
    # for evo in evos:
    # new_group=git.create_group_by_manual(name="template4",path="template4",parent_id=2)
    # pprint(new_group)
    #     items = git.get_group_projects(evo['id'])
    #     for item in items:
    #         git.create_project_with_fork(template_id=item['id'], target_namespace="evo-baseapp/"+evo['name'], new_name=item['name'])
    ###################################################################################
    # pprint(git.get_groups())

    # pprint(git.get_namespace(search="infra"))
    # pprint(git.get_groups())
    # pprint(git.get_group_projects(212))
    # for group in ['infra','interface','wcs','rcs','wes','web']:
    #     git.create_group_by_manual(name=group, path=group, parent_id=346)

    # for evo in evos:
    #     # new_group=git.create_group_by_manual(name=evo["name"],path=evo["name"],parent_id=346)
    # items = git.get_group_projects(211)
    # for item in items:
    #     git.create_project_with_fork(template_id=item['id'], target_namespace="evo-baseapp/web", new_name=item['name'])

    # git.create_project_with_fork(template_id=85, target_namespace="evo-baseapp/rcs",
    #                              new_name="evo-driveunit")
    # git.create_project_with_fork(template_id=84, target_namespace="evo-baseapp/rcs",
    #                              new_name="evo-rcs")
