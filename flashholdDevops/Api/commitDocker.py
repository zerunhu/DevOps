# coding=utf-8

import docker
import os
import sys
import random
import socket
import time
from django.conf import settings


def get_post():
    port = random.randint(1024, 65530)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    if result == 0:
        get_post()
    else:
        sock.close()
        print(os.path.basename(__file__), sys._getframe(
        ).f_code.co_name, sys._getframe().f_lineno, "get avalived port: {}".format(port))

        return port


class Insert_Data(object):

    def __init__(self, dockerAddr, file_path, tag_name):

        auth_config = {
            "username": "admin",
            "password": "Harbor12345"
        }
        self.auth_config = auth_config

        self.file_path = file_path
        self.file_name = file_path.split("uploads/")[1]
        self.tag_name = tag_name

        if dockerAddr:
            self.client = docker.DockerClient(
                base_url='tcp://{}'.format(dockerAddr), timeout=30)
        elif os.path.exists("/run/containerd/containerd.sock"):
            self.client = docker.DockerClient(
                base_url='unix://run/containerd/containerd.sock')
        elif os.path.exists("/var/run/docker.sock"):
            self.client = docker.DockerClient(
                base_url='unix://var/run/docker.sock')
        else:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, "未找到可用的docker服务!")
            return {"success": False, "error": "error: no docker server to be used! "}

        self.port = get_post()
        print(os.path.basename(__file__), sys._getframe(
        ).f_code.co_name, sys._getframe().f_lineno, " init args: {}".format(self.port))

    def pull_mysql(self):
        try:
            img = self.client.images.pull(settings.MYSQL_IMAGE_BASE.split(':')[0],
                                          tag=settings.MYSQL_IMAGE_BASE.split(':')[1], auth_config=self.auth_config)

            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, " pull image success: ", img)

            return {"success": True}
        except Exception as e:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, " pull image failed: ", str(e))

            #             panic(e)
            return {"success": False, "error": str(e)}

    def pull_mysql_client(self):
        try:
            img = self.client.images.pull("arey/mysql-client:latest")

            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, " pull image success: ", img)

            return {"success": True}

        except Exception as e:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, " pull image failed: ", str(e))

            #             panic(e)
            return {"success": False, "error": str(e)}

    def run_mysql(self):
        try:
            img = self.client.images.get(settings.MYSQL_IMAGE_BASE)
        except docker.errors.ImageNotFound:
            self.pull_mysql()

        try:
            img = self.client.images.get("arey/mysql-client")
        except docker.errors.ImageNotFound:
            self.pull_mysql_client()

        try:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno,
                  " start craete  mysql instance mysql-{}".format(self.port))

            volume = '/opt/mysqldata-{}'.format(self.port)

            mysql_container = self.client.containers.run(
                image=settings.MYSQL_IMAGE_BASE,
                #                 volumes={volume: {'bind': '/var/lib/mysql', 'mode': 'rw'},
                #                          '/opt/shentong-20190920.sql': {'bind': '/var/shentong-20190920.sql', 'mode': 'rw'}},
                name='mysql-{}'.format(self.port),
                ports={'3306/tcp': self.port},
                environment=["MYSQL_ROOT_PASSWORD=123456"],
                detach=True, stdout=True, stderr=True, user='root')

            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno,
                  "waiting 90s for starting mysql-{} container......".format(self.port))

            time.sleep(90)

            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno,
                  "mysql_container_id: {}".format(mysql_container.id))

            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, self.client.containers.get(
                "mysql-{}".format(self.port)).id)

            container_list = [container for container in self.client.containers.list(
                filters={'status': 'running', 'name': 'mysql-{}'.format(self.port)}) if
                              container.name == "mysql-{}".format(self.port)]
            if container_list:
                print(os.path.basename(__file__), sys._getframe(
                ).f_code.co_name, sys._getframe().f_lineno, "container_list: ", container_list)

                container = container_list[0]
                #                 for container in self.client.containers.list(filters={'status': 'running', 'name': 'mysql-{}'.format(self.port)}):
                #                 if container.name == "mysql-{}".format(self.port):
                print(os.path.basename(__file__), sys._getframe(
                ).f_code.co_name, sys._getframe().f_lineno, "in in in in list")

                print(os.path.basename(__file__), sys._getframe(
                ).f_code.co_name, sys._getframe().f_lineno, container.logs(stream=True, tail=30))

                return {"success": True, "mysql_container_id": mysql_container.id}

            else:
                print(os.path.basename(__file__), sys._getframe(
                ).f_code.co_name, sys._getframe().f_lineno, "failed to start mysql-{} instance: ".format(self.port),
                      container.logs(stream=True,tail=30))

                return {"success": False, "error": str(container.logs(stream=True, tail=30))}

        except docker.errors.ImageNotFound:

            pull_result = self.pull_mysql()
            if pull_result['success']:
                self.run_mysql()

            else:
                return pull_result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_mysql_server_log(self):
        # container_list = container for container in self.client.containers.
        container = self.client.containers.get(
            "mysql-{}".format(self.port))
        print(os.path.basename(__file__), sys._getframe(
        ).f_code.co_name, sys._getframe().f_lineno, container.logs(timestamps=True, tail=30))

    def get_mysql_client_log(self):
        # container_list = container for container in self.client.containers.
        container = self.client.containers.get(
            "mysql-client-{}".format(self.port))
        print(os.path.basename(__file__), sys._getframe(
        ).f_code.co_name, sys._getframe().f_lineno, container.logs(timestamps=True, tail=30))

        if container.logs(timestamps=True):
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, "failed to install data for mysql-{}".format(self.port))
            return False
        else:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, "success to install data for mysql-{}".format(self.port))
            return True

    '''
    def wait_mysql_client(self):
        containers = [container for container in self.client.containers.list(
            filters={'name': 'mysql-client-{}'.format(self.port), 'status': 'exited'})]
        if containers:
            self.get_mysql_server_log()

            client_log = self.get_mysql_client_log()
            print(os.path.basename(__file__),  sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, "exec self.get_mysql_client_log(): ", client_log)

            # 日志为空，代表执行成功
            if client_log:
                return False

            else:
                print(os.path.basename(__file__),  sys._getframe(
                ).f_code.co_name, sys._getframe().f_lineno, "there is no logs out of mysql-client-{} , install data success ".format(self.port))
                return False

        else:
            print(os.path.basename(__file__),  sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, "sleep 60s, continue to mysql_client-{} exit... ".format(self.port))
            time.sleep(60)
            # 这里会不会存在一个问他，当其他函数调用本函数时，这里有个隐藏的 return None，会直接作为调用本函数的返回值，返回给调用它的函数! 所以调用本函数的返回值永远为 None！
            self.wait_mysql_client()
        '''

    def run_mysql_client(self):

        # 调用run_mysql，启动mysql-init容器
        run_result = self.run_mysql()

        if run_result['success']:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno,
                  " successed running mysql-{} instance ~".format(self.port))
            try:
                netLink = 'mysql-{}'.format(self.port)

                client_container = self.client.containers.run(
                    image="arey/mysql-client",
                    links={netLink: 'mysql-server'},
                    volumes={
                        self.file_path: {'bind': '/sql/{}'.format(self.file_name), 'mode': 'rw'}},
                    name='mysql-client-{}'.format(self.port),
                    command="-h mysql-{} -uroot -p123456 -D mysql -e 'set global max_allowed_packet = 100*1024*1024;source /sql/{file_name};'".format(
                        self.port, file_name=self.file_name),
                    detach=True, stdout=True, stderr=True, remove=False)

                print(os.path.basename(__file__), sys._getframe(
                ).f_code.co_name, sys._getframe().f_lineno, "success run mysql-client-{}  ".format(self.port))

                '''
                用循环的方式，去查看mysql-client容器是否退出，若退出则同时查看mysql-server日志，未退出继续循环
                '''
                while 1 == 1:
                    if [container for container in self.client.containers.list(
                            filters={'name': 'mysql-client-{}'.format(self.port), 'status': 'exited'})]:

                        client_log = self.get_mysql_client_log()
                        print(os.path.basename(__file__), sys._getframe().f_code.co_name, sys._getframe(
                        ).f_lineno, "exec self.get_mysql_client_log(): ", client_log)

                        if client_log:
                            print(os.path.basename(__file__), sys._getframe().f_code.co_name, sys._getframe(
                            ).f_lineno,
                                  "there is no logs out of mysql-client-{} , install data success ".format(self.port))
                            break

                        else:
                            print(os.path.basename(__file__), sys._getframe(
                            ).f_code.co_name, sys._getframe().f_lineno,
                                  "failed to install mysql-{} data,  mysql-client-{} will be removed!".format(self.port,
                                                                                                              self.port))

                            container = self.client.containers.get(
                                "mysql-client-{}".format(self.port))
                            logs = container.logs(timestamps=True, tail=30)
                            return {"success": False, "message": str(logs)}

                    else:
                        print(os.path.basename(__file__), sys._getframe(
                        ).f_code.co_name, sys._getframe().f_lineno,
                              "sleep 20s, continue to wait mysql-client-{} ... ".format(self.port))
                        time.sleep(20)
                        continue

                self.get_mysql_server_log()
                container.remove()
                return {"success": True}

            except Exception as e:
                print(os.path.basename(__file__), sys._getframe(
                ).f_code.co_name, sys._getframe().f_lineno, e)

                return {"success": False, "message": str(e)}
        else:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno,
                  "error: run mysql-{} server failed! will return run_result! ".format(self.port))
            return run_result

    def Commit(self):

        run_result = self.run_mysql_client()
        print(os.path.basename(__file__), sys._getframe(
        ).f_code.co_name, sys._getframe().f_lineno, "resut of  execed self.run_mysql_client() : ", run_result)
        if run_result['success']:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno,
                  "successed to install mysql-{} data, will commit mysql-{} image".format(self.port, self.port))
            try:
                mysql_container_obj = self.client.containers.get(
                    "mysql-{}".format(self.port))

                commit_result = mysql_container_obj.commit(
                    repository=settings.MYSQL_IMAGE_BASE.split(':')[0], tag=self.tag_name,
                    author="devops")

                print(os.path.basename(__file__), sys._getframe(
                ).f_code.co_name, sys._getframe().f_lineno,
                      "  success to commit mysql-{} container: ".format(self.port), commit_result)
                # push镜像
                try:
                    push_result = self.client.images.push(
                        '{}:{}'.format(settings.MYSQL_IMAGE_BASE.split(':')[0], self.tag_name),
                        auth_config=self.auth_config)
                    print(os.path.basename(__file__), sys._getframe(
                    ).f_code.co_name, sys._getframe().f_lineno, push_result)

                    # mysql_container_obj.
                    return "success"

                except docker.errors.APIError:
                    print(os.path.basename(__file__), sys._getframe(
                    ).f_code.co_name, sys._getframe().f_lineno,
                          " docker server returns an error")

                    return "docker server returns an error"

                except Exception as e:
                    raise e
            except Exception as e:
                raise e
        else:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, "install mysql-{} data failed!".format(self.port),
                  run_result['message'])

            return "install mysql-{} data failed!".format(self.port)


if __name__ == "__main__":
    l = Insert_Data(dockerAddr="172.31.249.187:2375")
    l.Commit()
