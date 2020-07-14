# coding=utf-8

import docker
import os
import sys
import time



class CreateDataSetImage(object):

    def __init__(self, dockerAddr, filePath, mysqlPort):

        auth_config = {
            "username": "admin",
            "password": "Harbor12345"
        }
        self.auth_config = auth_config

        self.file_path = filePath
        self.file_name = filePath.split("/")[-1]
        self.mysql_port = mysqlPort

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

    def get_mysql_client_log(self):
        # container_list = container for container in self.client.containers.
        container = self.client.containers.get(
            "mysql-client-{}".format(self.mysql_port))
        print(os.path.basename(__file__), sys._getframe(
        ).f_code.co_name, sys._getframe().f_lineno, container.logs(timestamps=True, tail=30))

        if container.logs(timestamps=True):
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, "failed to install data for mysql-{}".format(self.mysql_port))
            return False
        else:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, "success to install data for mysql-{}".format(self.mysql_port))
            return True

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

    def run_mysql_client(self):

        if not self.client.images.list(name="arey/mysql-client:latest"):
            # 调用run_mysql，启动mysql-init容器
            run_result = self.pull_mysql_client()
        else:
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno,
                  " mysql serevr  instance {}".format(self.mysql_port))
            print(os.path.basename(__file__), sys._getframe(
            ).f_code.co_name, sys._getframe().f_lineno, "sql file_path:{}, sql file_name:{}".format(self.file_path, self
                                                                                                    .file_name))
            try:
                client_container = self.client.containers.run(
                    image="arey/mysql-client",
                    network_mode="host",
                    volumes={
                        self.file_path: {'bind': '/sql/{}'.format(self.file_name), 'mode': 'rw'}},
                    name='mysql-client-{}'.format(self.mysql_port),
                    command="-h 127.0.0.1 -P {port} -uroot -p123456 -D mysql -e 'set global max_allowed_packet = 100*1024*1024;source /sql/{file_name};'".format(
                        port=self.mysql_port, file_name=self.file_name),
                    detach=True, stdout=True, stderr=True, remove=False)

                print(os.path.basename(__file__), sys._getframe(
                ).f_code.co_name, sys._getframe().f_lineno, "success run mysql-client-{}  ".format(self.mysql_port))

                '''
                用循环的方式，去查看mysql-client容器是否退出，若退出则同时查看mysql-server日志，未退出继续循环
                '''
                while 1 == 1:
                    if [container for container in self.client.containers.list(
                            filters={'name': 'mysql-client-{}'.format(self.mysql_port), 'status': 'exited'})]:

                        client_log = self.get_mysql_client_log()
                        print(os.path.basename(__file__), sys._getframe().f_code.co_name, sys._getframe(
                        ).f_lineno, "exec self.get_mysql_client_log(): ", client_log)

                        if client_log:
                            print(os.path.basename(__file__), sys._getframe().f_code.co_name, sys._getframe(
                            ).f_lineno,
                                  "there is no logs out of mysql-client-{} , install data success ".format(
                                      self.mysql_port))
                            break

                        else:
                            print(os.path.basename(__file__), sys._getframe(
                            ).f_code.co_name, sys._getframe().f_lineno,
                                  "failed to install mysql-{} data,  mysql-client-{} will be removed!".format(
                                      self.mysql_port,
                                      self.mysql_port))

                            container = self.client.containers.get(
                                "mysql-client-{}".format(self.mysql_port))
                            logs = container.logs(timestamps=True, tail=30)
                            return {"success": False, "message": str(logs)}

                    else:
                        print(os.path.basename(__file__), sys._getframe(
                        ).f_code.co_name, sys._getframe().f_lineno,
                              "sleep 20s, continue to wait mysql-client-{} ... ".format(self.mysql_port))
                        time.sleep(20)
                        continue

                container.remove()
                return {"success": True}

            except Exception as e:
                print(os.path.basename(__file__), sys._getframe(
                ).f_code.co_name, sys._getframe().f_lineno, e)

                return {"success": False, "message": str(e)}
