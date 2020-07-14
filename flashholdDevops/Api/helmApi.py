#coding=utf-8
from pyhelm.chartbuilder import ChartBuilder
from pyhelm.tiller import Tiller


class HelmApi(object):
    def __init__(self):
        #nginx-ingress asign tcp 38888 to tiller-deploy 43134
        self.tiller = Tiller("192.168.21.145",port=38888)

    #type=repo,directory,git
    def get_chart(self,chart_name="",type="",location=""):
        chart = ChartBuilder({"name": chart_name, "source": {"type": type, "location": location}})
        return chart

    def install_release(self,chart,namespace="",release_name=""):
        if hasattr(chart,"get_helm_chart"):
            self.tiller.install_release(chart.get_helm_chart(), dry_run=False, namespace=namespace,name = release_name)
        return

    def upgrade_release(self,chart,namespace="",release_name=""):
        if hasattr(chart,"get_helm_chart"):
            self.tiller.update_release(chart.get_helm_chart(), dry_run=False, namespace=namespace,name = release_name)
        return

    def delete_release(self,release_name=""):
        self.tiller.uninstall_release(release_name)
        return

if __name__ == "__main__":
    l = HelmApi()
    chart = l.get_chart("mysql",type="directory",location="/tmp/mysql")
    # l.upgrade_release(chart,namespace="default",release_name="mysql-111111111")
    l.delete_release(release_name="mysql-111111111")
