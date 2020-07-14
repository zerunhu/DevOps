#coding=utf-8

import requests
import simplejson
import logging
from django.conf import settings
import base64
logging.basicConfig(level = logging.INFO)


class HarborClient(object):
    def __init__( self ):
        self.host = settings.HARBOR_HOST
        self.user = settings.HARBOR_USER
        self.password = settings.HARBOR_PASSWORD
        self.protocol = "http"
        self.post_header_dict = {
            'Authorization': 'Basic ' + base64.b64encode(self.user + ":" + self.password)
        }
        # self.session_id = self.login()

    # def __del__( self ):
    #     self.logout()

    def login( self ):
        url = '%s://%s/c/login' %(self.protocol, self.host)
        login_data = requests.post(url,
            data = {'principal':self.user,
                    'password':self.password})
        if login_data.status_code == 200:
            session_id = login_data.cookies.get('sid')

            logging.debug("Successfully login, session id: {}".format(
                session_id))
            return session_id
        else:
            logging.error("Fail to login, please try again")
            return None


    def logout( self ):
        requests.get('%s://%s/logout' % (self.protocol, self.host),)
            # cookies = {'sid':self.session_id})
        logging.debug("Successfully logout")


    # Get project id
    def get_project_id_from_name( self, project_name ):
        registry_data = requests.get(
            '%s://%s/api/projects?name=%s' %
            (self.protocol, self.host, project_name),headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if registry_data.status_code == 200 and registry_data.json():
            project_id = registry_data.json()[0]['project_id']
            logging.debug(
                "Successfully get project id: {}, project name: {}".format(
                    project_id, project_name))
            return project_id
        else:
            print("Fail to get project id from project name", project_name)
            return None


    # GET /search
    def search( self, query_string ):
        result = None
        path = '%s://%s/api/search?q=%s' % (self.protocol, self.host,
                                            query_string)
        response = requests.get(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = response.json()
            logging.debug("Successfully get search result: {}".format(result))
        else:
            logging.error("Fail to get search result")
        return result


    # GET /projects
    def get_projects( self, project_name = None, is_public = None ):
        # TODO: support parameter
        result = None
        path = '%s://%s/api/projects' % (self.protocol, self.host)
        response = requests.get(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = response.json()
            logging.debug("Successfully get projects result: {}".format(
                result))
        else:
            logging.error("Fail to get projects result")
        return result


    # HEAD /projects
    def check_project_exist( self, project_name ):
        result = False
        path = '%s://%s/api/projects?project_name=%s' % (
            self.protocol, self.host, project_name)
        response = requests.head(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = True
            logging.debug(
                "Successfully check project exist, result: {}".format(result))
        elif response.status_code == 404:
            result = False
            logging.debug(
                "Successfully check project exist, result: {}".format(result))
        else:
            logging.error("Fail to check project exist")
        return result


    # POST /projects
    def create_project( self, project_name, public = "true" ):
        result = False
        path = '%s://%s/api/projects' % (self.protocol, self.host)
        request_body = {"project_name":project_name,
                                          "metadata": {
                                            "public": "true",
                                            "enable_content_trust": "false",
                                            "prevent_vul": "false",
                                            "severity": "negligible",
                                            "auto_scan": "false"
                                          }}
        response = requests.post(path,json = request_body,headers=self.post_header_dict)

        # 201   Project created successfully.
        # 400   Unsatisfied with constraints of the project creation.
        # 401   User need to log in first.
        # 409   Project name already exists.
        # 415   The Media Type of the request is not supported, it has to be “application/json”
        # 500   Unexpected internal errors.
        if response.status_code == 201 or response.status_code == 409:
            result = True
            logging.debug(
                "Successfully create project with project name: {}".format(
                    project_name))
        else:
            logging.error(
                "Fail to create project with project name: {}, response code: {}".format(
                    project_name, response.status_code))
        return result

    def get_repo_chart_version(self,project_name,chart_name):
        result = None
        path = '{protocol}://{host}/api/chartrepo/{repo}/charts/{name}'.format(protocol=self.protocol,
                                                                               host=self.host,
                                                                               repo=project_name,
                                                                               name=chart_name)
        response = requests.get(path,headers=self.post_header_dict)
                                # cookies={'sid': self.session_id})

        if response.status_code == 200:
            result = response.json()

        return result

    # PUT /projects/{project_id}/publicity
    def set_project_publicity( self, project_id, is_public ):
        result = False
        path = '%s://%s/api/projects/%s/publicity?project_id=%s' % (
            self.protocol, self.host, project_id, project_id)
        request_body = simplejson.dumps({'public':is_public})
        response = requests.put(path,headers=self.post_header_dict,
            # cookies = {'sid':self.session_id},
            data = request_body)
        if response.status_code == 200:
            result = True
            logging.debug(
                "Success to set project id: {} with publicity: {}".format(
                    project_id, is_public))
        else:
            logging.error(
                "Fail to set publicity to project id: {} with status code: {}".format(
                    project_id, response.status_code))
        return result


    # GET /statistics
    def get_statistics( self ):
        result = None
        path = '%s://%s/api/statistics' % (self.protocol, self.host)
        response = requests.get(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = response.json()
            logging.debug("Successfully get statistics: {}".format(result))
        else:
            logging.error("Fail to get statistics result")
        return result


    # GET /users
    def get_users( self,username = None):
        result = None
        path = '%s://%s/api/users' % (self.protocol, self.host)
        if username:
            path = path + "?username=" + username

        response = requests.get(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = response.json()
            logging.debug("Successfully get users result: {}".format(result))
        else:
            logging.error("Fail to get users result")
        return result


    # POST /users
    # user = {
    #      'username':username,
    #      'email':email,
    #      'password':password,
    #      'realname':realname,
    #      'comment':"create by admin"
    #   }
    def create_user( self, user):
        result = False
        path = '%s://%s/api/users' % (self.protocol, self.host)
        request_body = simplejson.dumps(user)
        response = requests.post(path,headers=self.post_header_dict,
            # cookies = {'sid':self.session_id},
            data = request_body)
        if response.status_code == 201:
            result = True
            logging.debug("Successfully create user with username: {}".format(
                user["username"]))
        else:
            print(response.content)
            logging.error("Fail to create user with username: {}, response code: {}".format(
                    user["username"], response.status_code))
        return result


    # PUT /users/{user_id}
    def update_user_profile( self, user_id, email, realname, comment ):
        # TODO: support not passing comment
        result = False
        path = '%s://%s/api/users/%s?user_id=%s' % (self.protocol, self.host,
                                                    user_id, user_id)
        request_body = simplejson.dumps({'email':email,
                                         'realname':realname,
                                         'comment':comment})
        response = requests.put(path,headers=self.post_header_dict,
            # cookies = {'sid':self.session_id},
            data = request_body)
        if response.status_code == 200:
            result = True
            logging.debug(
                "Successfully update user profile with user id: {}".format(
                    user_id))
        else:
            logging.error(
                "Fail to update user profile with user id: {}, response code: {}".format(
                    user_id, response.status_code))
        return result


    # DELETE /users/{user_id}
    def delete_user( self, user_id ):
        result = False
        path = '%s://%s/api/users/%s' % (self.protocol, self.host, user_id)
        response = requests.delete(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = True
            logging.debug("Successfully delete user with id: {}".format(
                user_id))
        else:
            logging.error("Fail to delete user with id: {}".format(user_id))
        return result


    # PUT /users/{user_id}/password
    def change_password( self, user_id, old_password, new_password ):
        result = False
        path = '%s://%s/api/users/%s/password?user_id=%s' % (
            self.protocol, self.host, user_id, user_id)
        request_body = simplejson.dumps({'old_password':old_password,
                                         'new_password':new_password})
        response = requests.put(path,headers=self.post_header_dict,
            # cookies = {'sid':self.session_id},
            data = request_body)
        if response.status_code == 200:
            result = True
            logging.debug(
                "Successfully change password for user id: {}".format(user_id))
        else:
            logging.error("Fail to change password for user id: {}".format(
                user_id))
        return result


    # PUT /users/{user_id}/sysadmin
    def promote_as_admin( self, user_id ):
        # TODO: always return 404, need more test
        result = False
        path = '%s://%s/api/users/%s/sysadmin?user_id=%s' % (
            self.protocol, self.host, user_id, user_id)
        response = requests.put(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = True
            logging.debug(
                "Successfully promote user as admin with user id: {}".format(
                    user_id))
        else:
            logging.error(
                "Fail to promote user as admin with user id: {}, response code: {}".format(
                    user_id, response.status_code))
        return result


    # GET /repositories
    def get_repositories( self, project_id, query_string = None ):
        result = None
        path = '%s://%s/api/repositories?project_id=%s' % (
            self.protocol, self.host, project_id)
        if query_string:
            path = path + '&q=' + query_string

        response = requests.get(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = response.json()
            logging.debug(
                "Successfully get repositories with id: {}, result: {}".format(
                    project_id, result))
        else:
            logging.error("Fail to get repositories result with id: {}".format(
                project_id))
        return result


    # DELETE /repositories
    def delete_repository( self, repo_name ):
        result = False
        path = '%s://%s/api/repositories/%s' % (self.protocol,
                                                self.host, repo_name)
        response = requests.delete(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = True
            logging.debug("Successfully delete repository: {}".format(
                repo_name))
        else:
            logging.error("Fail to delete repository: {}".format(repo_name))
        return result

    # DELETE /project
    def delete_project(self, project_name):
        project_id = None
        q = self.search(project_name)
        if "project" in q:
            try:
                project_id = q["project"][0]["project_id"]
            except:
                project_id = None
        result = False
        path = '%s://%s/api/projects/%s' % (self.protocol,
                                                self.host, project_id)
        response = requests.delete(path,headers=self.post_header_dict)
                                   # cookies={'sid': self.session_id})
        if response.status_code == 200:
            result = True
            logging.debug("Successfully delete repository: {}".format(
                project_name))
        else:
            logging.error("Fail to delete repository: {}".format(project_name))
        return result


    # DELETE /repositories/tag
    def delete_tag_from_repository( self, repo_name, tag ):
        result = False
        path = '%s://%s/api/repositories/%s/tags/%s' % (self.protocol,
                                                        self.host, repo_name, tag)
        response = requests.delete(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = True
            logging.debug("Successfully delete tag: {}".format(
                repo_name))
        else:
            logging.error("Fail to delete tag: {}".format(repo_name))
        return result


    # Get /repositories/tags
    def get_repository_tags( self, repo_name ):
        result = None
        path = '%s://%s/api/repositories/%s/tags' % (
            self.protocol, self.host, repo_name)
        response = requests.get(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})

        if response.status_code == 200:
            result = response.json()
            logging.debug(
                "Successfully get tag with repo name: {}, result: {}".format(
                    repo_name, result))
        else:
            logging.error("Fail to get tags with repo name: {}".format(
                repo_name))
        return result


    # GET /repositories/manifests
    def get_repository_manifests( self, repo_name, tag ):
        result = None
        path = '%s://%s/api/repositories/manifests?repo_name=%s&tag=%s' % (
            self.protocol, self.host, repo_name, tag)
        response = requests.get(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = response.json()
            logging.debug(
                "Successfully get manifests with repo name: {}, tag: {}, result: {}".format(
                    repo_name, tag, result))
        else:
            logging.error(
                "Fail to get manifests with repo name: {}, tag: {}".format(
                    repo_name, tag))
        return result


    # GET /repositories/top
    def get_top_accessed_repositories( self, count = None ):
        result = None
        path = '%s://%s/api/repositories/top' % (self.protocol, self.host)
        if count:
            path += "?count=%s" % (count)
        response = requests.get(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = response.json()
            logging.debug(
                "Successfully get top accessed repositories, result: {}".format(
                    result))
        else:
            logging.error("Fail to get top accessed repositories")
        return result


    # GET /logs
    def get_logs( self, lines = None, start_time = None, end_time = None ):
        result = None
        path = '%s://%s/api/logs' % (self.protocol, self.host)
        response = requests.get(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = response.json()
            logging.debug("Successfully get logs")
        else:
            logging.error("Fail to get logs and response code: {}".format(
                response.status_code))
        return result



    # GET  project  users
    def get_project_users(self, project_id):
        result = None
        path = '%s://%s/api/projects/%s/members' % (self.protocol, self.host, project_id)
        response = requests.get(path,headers=self.post_header_dict)
            # cookies = {'sid':self.session_id})
        if response.status_code == 200:
            result = response.json()
            logging.debug("Successfully get project users")
        else:
            logging.error("Fail to get project users and response code: {}".format(
                response.status_code))
        return result


    # add project user
    def add_project_user(self, project_id, username):
        result = False
        path = '%s://%s/api/projects/%s/members' % (self.protocol, self.host, project_id)
        project_member = simplejson.dumps( { "roles": [1],
                                             "username": username })
        response = requests.post(path,headers=self.post_header_dict,
            # cookies = {'sid':self.session_id},
            data = project_member)
        if response.status_code == 200 or response.status_code == 409:
            result = True
            logging.debug("Successfully add project user")
        else:
            logging.error("Fail to add project users and response code: {}".format(response.status_code))
        return result

    # delete project user
    def delete_project_user(self,project_id,user_id):
        result = False
        path = '%s://%s/api/projects/%s/members/%s' % (self.protocol, self.host, project_id,user_id)
        response = requests.delete(path,headers=self.post_header_dict)
        if response.status_code == 200:
            result = True
            logging.debug("Successfully delete project user")
        else:
            logging.error("Fail to delete project users and response code: {}".format(response.status_code))
        return result


    def check_project_admin(self,project_id,current_user):
        users = self.get_project_users(project_id)
        for u in users:
            if u.get("username") == current_user and u.get("role_id") == 1:
                return True
        return False


if __name__ == "__main__":
    l = HarborClient()
    # l.create_project("huaweitest")
    q=l.get_repo_chart_version("huawei","rcs-feature-1554874256")
    print q