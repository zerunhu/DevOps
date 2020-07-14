#coding=utf-8
from django.forms import ModelForm,TextInput,ChoiceField,EmailInput,PasswordInput,SelectMultiple,CheckboxInput,Textarea,CheckboxSelectMultiple
from django.forms.widgets import Select
from app.models import *
from django.contrib.auth.models import User,Group
from django import forms
from helper import helper
from Api.gitlabApi import Api
import re
from django.conf import settings
from django.db.models import Q
class ProjectForm(ModelForm):
    #################################################################
    #以后要用baseAppVersion = form.ModelChoiceField(queryset=Branch.objects.filter(name__contains="release/pro",project__name="publicApp"))
    #################################################################
    baseApp = forms.ChoiceField(required=False,widget=CheckboxSelectMultiple)
    class Meta:
        model = Project
        # fields = ['name', 'slugName', 'desc', 'members', 'admin']
        fields = ['name', 'slugName', 'desc']
        widgets = {
            'name': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
            'slugName': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
            # 'admin': SelectMultiple(attrs={"class":"form-control col-md-7 col-xs-12"}),
            # 'members': SelectMultiple(attrs={"class": "form-control col-md-7 col-xs-12"}),
            'desc': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
        }

    # def __init__(self, *args, **kwargs):
    #     super(ProjectForm, self).__init__(*args, **kwargs)
    #     self.auto_id = True

    def clean_name(self):
        data = self.cleaned_data['name']
        # decode:  将其它编码转成  ===》unicode
        # encode:  将 unicode   ====》其它编码
        for ch in data:
            if u'\u4e00' <= ch <= u'\u9fff':
                raise forms.ValidationError("此字段不允许中文和大写字母")

        return data.lower()

class AppForm(ModelForm):
    extendApp = forms.ChoiceField(required=False,widget=CheckboxSelectMultiple)
    class Meta:
        model = App
        fields = ['name', 'slugName', 'project', 'langauge', 'desc']
        widgets = {
            'name': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
            'slugName': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
            'desc': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
        }

    # def __init__(self, *args, **kwargs):
    #     super(AppForm, self).__init__(*args, **kwargs)
    #     l = Api()
    #     self.fields['extendApp'].choices = l.get_baseapp_project()

    def clean_name(self):
        data = self.cleaned_data['name']
        # decode:  将其它编码转成  ===》unicode
        # encode:  将 unicode   ====》其它编码
        for ch in data:
            if u'\u4e00' <= ch <= u'\u9fff' or 65 <= ch <= 90:
                raise forms.ValidationError("此字段不允许中文和大写字母")
        # not.
        return data.lower()


class UserForm(ModelForm):
    maxDeployNum = forms.IntegerField(label="环境限制数",max_value=10)
    class Meta:
        model = User
        fields = ['username','email','password',"last_name",'groups','maxDeployNum']
        widgets = {
            'username': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
            'last_name': TextInput(attrs={"class": "form-control col-md-7 col-xs-12"}),
            'password': PasswordInput(attrs={"class": "form-control col-md-7 col-xs-12"}),
            'email': EmailInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
            'groups': SelectMultiple(attrs={"class":"form-control col-md-7 col-xs-12"}),
        }

    def clean_username(self):
        data = self.cleaned_data['username']
        # decode:  将其它编码转成  ===》unicode
        # encode:  将 unicode   ====》其它编码
        for ch in data:
            if u'\u4e00' <= ch <= u'\u9fff':
                raise forms.ValidationError("此字段不允许中文")
        # not.
        return data

class FGroupForm(ModelForm):

    class Meta:
        model = FGroup
        fields = ['name','nameSlug']
        widgets = {
            'name': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
            'nameSlug': TextInput(attrs={"class": "form-control col-md-7 col-xs-12"}),
        }

class BranchForm(ModelForm):
    baseBranch = forms.ModelChoiceField(queryset=Branch.objects.filter(Q(name__startswith="release") | Q(name__startswith="master")|Q(name__contains="tag")))
    singleApp = forms.ModelChoiceField(queryset=None,required=False)
    version = forms.CharField(required=False)
    class Meta:
        model = Branch
        # fields = ['name','desc','app','flag','version']
        fields = ['name', 'desc', 'project','type','version','baseBranch','singleApp',"projectFlag"]
        widgets = {
            'name': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
            'desc': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
            # 'app': SelectMultiple(attrs={"class": "form-control col-md-7 col-xs-12"}),
            'projectFlag': CheckboxInput(),
        }

class EnvTemplateForm(ModelForm):
    featureApp = forms.ModelMultipleChoiceField(queryset=App.objects.all(), required=False,widget=CheckboxSelectMultiple)
    class Meta:
        model = EnvTemplate
        fields = ['name', 'desc','featureApp','baseApp']
        widgets = {
            'name': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
            'desc': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
        }

    def clean_name(self):
        data = self.cleaned_data['name']
        # decode:  将其它编码转成  ===》unicode
        # encode:  将 unicode   ====》其它编码
        for ch in data:
            if u'\u4e00' <= ch <= u'\u9fff':
                raise forms.ValidationError("此字段不允许中文")
        return data

class ProjectUserForm(ModelForm):
    class Meta:
        model = ProjectUser
        fields = ['user','project']

class DeployForm(ModelForm):
    deploy = forms.ModelChoiceField(queryset=Deployment.objects.all(),required=False)
    # deployMode = forms.ChoiceField(choices=(("network","网络"),("host","主机")),required=False)
    # baseApp= forms.ModelMultipleChoiceField(queryset=App.objects.filter(project__name="baseApp"),required=False,widget=CheckboxSelectMultiple)
    baseAppVersion = forms.ModelChoiceField(queryset=Branch.objects.all(),required=False)
    commonApp = forms.ChoiceField(required=False, choices=settings.COMMON_APP,widget=CheckboxSelectMultiple)
    envTemplate = forms.ModelChoiceField(queryset=EnvTemplateList.objects.all(),required=False)
    dataSet = forms.ModelChoiceField(queryset=DataSet2.objects.all(), required=False)
    # def __init__(self, *args, **kwargs):
    #     super(DeployForm, self).__init__(*args, **kwargs)
    #     l = Api()
    #     self.fields['baseApp'].choices = l.get_publicapp_project()
        # self.fields['baseAppVersion'].queryset = Branch.objects.filter(project__id=kwargs['project_id'])

    class Meta:
        model = Deployment
        # fields = ['name','desc','app','flag','version']
        fields = ['project', 'envName','envDesc','dataSet','envTemplate',"commonApp","group"]
        # fields = ['project', 'envName','envDesc','envTemplate','dataSet',"commonApp"]

class ProDeployForm(ModelForm):
    deploy = forms.ModelChoiceField(queryset=Deployment.objects.all(), required=False)
    project_name = forms.CharField()
    version = forms.CharField()

    class Meta:
        model = Deployment
        # fields = ['name','desc','app','flag','version']
        fields = ['project', 'version','deploy']









class DataSetImageForm(ModelForm):
    # username = forms.ChoiceField(required=False)
    # password = forms.ChoiceField(required=False)
    class Meta:
        model = DataSet2
        # fields = ['name','desc','app','flag','version']
        fields = ['name','imageName']
        widgets = {
            'imageName': TextInput(attrs={"class":"form-control col-md-7","readonly":"true"}),
            # 'desc': TextInput(attrs={"class":"form-control col-md-7 col-xs-12"}),
            # 'flag': CheckboxInput(),
        }

    def clean_name(self):
        data = self.cleaned_data['name']
        # decode:  将其它编码转成  ===》unicode
        # encode:  将 unicode   ====》其它编码
        data = helper.validateData(data)
        return data

class DataSetForm2(ModelForm):
    class Meta:
        model = DataSet2
        fields = ['name','f']

    def clean_name(self):
        data = self.cleaned_data['name']
        data = helper.validateData(data)
        return data

class DataSetForm3(ModelForm):
    class Meta:
        model = DataSet2
        fields = ['f']

    def clean_name(self):
        data = self.cleaned_data['name']
        data = helper.validateData(data)
        return data





class LimitForm(ModelForm):
    class Meta:
        model = Limit
        # fields = ['name','desc','app','flag','version']
        fields = ['user','group','resource','limit']
