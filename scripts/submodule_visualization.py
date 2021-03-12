import os
import configparser
import subprocess
import pydot
import click
import requests
from requests.auth import HTTPBasicAuth

#RUN : python ./scripts/submodule_visualization.py ../GW-Releases

class Tree(object):

    def __init__(self, data=None):
        self.left = None
        self.children = []
        self.data = data

    def createChild(self,tree):
        self.children.append(tree)

    def getChildren(self):
        return self.children

    def getChildByURL(self, url):
        if self.data['url'] == url:
            return self
        for child in self.children:
            result = child.getChildByURL(url)
            if result is not False:
                return result
        return False

    def getData(self):
        return self.data

    def get_main_repo_name(self):
        main_repo_cmd=["git","rev-parse","--show-toplevel"]
        parent_repo_name=subprocess.check_output(main_repo_cmd, encoding='UTF-8').split("/")[-1].strip()
        return parent_repo_name

    def get_master_tag(self):
        get_tag_commit = ["git", "rev-list", "--tags", "--max-count=1"]
        tags=['git', 'fetch', '--all', '--tags']
        subprocess.check_output(tags)
        tag_commit_id = subprocess.check_output(get_tag_commit, encoding='UTF-8').strip()
        args = ["git", "describe", "--tags", tag_commit_id]
        master_tag = subprocess.check_output(args, encoding='UTF-8')
        return master_tag

    def get_master_branch(self):
        git_command=["git","branch","--show-current"]
        master_branch=subprocess.check_output(git_command, encoding='UTF-8')
        return master_branch

    def buildGraph(self, graph, parent, indentation, graphmode, with_url,level=0):
        color="#B8CFE0"

        if level==0:
            color="#FFBEBC"
        elif level==1:
            color="#FFF5BA"
        elif level==2:
            color = "#ACE7EF"


        label = self.get_Label(with_url, "\n")

        # Add explicit quotation marks to avoid parsing confusion in dot
        if graphmode == 'scattered':
            node = pydot.Node('"' + label + '"',style="filled", fillcolor=color,shape='box', fontsize='22')
        else:
            node = pydot.Node('"' + label + '"', fillcolor=color,shape='box', fontsize='22')
        indentation += 20

        if parent is not None:
            graph.add_edge(pydot.Edge(parent, node))
        graph.add_node(node)

        if self.children:
            level=level+1

        for child in self.children:
            [graph, indentation] = child.buildGraph(
                graph, node, indentation, graphmode, with_url,level)
            indentation += 1
        return [graph, indentation]

    def get_parent_repo(self,repo_name):
        parent_repo=None
        api_url = "https://api.github.com/repos/%s" % repo_name
        details = requests.get(api_url)
        if details.status_code is 200:
            json = details.json()
            if "parent" in json:
                parent_repo = json["parent"]["full_name"]

        return parent_repo

    def get_Label(self, with_url, sep="\n"):
        label = ""
        main_repo_name=self.get_main_repo_name()
        if main_repo_name in self.data['name']:
            label=sep + label+self.data["name"]
            label = label + sep + sep+ "branch =" + self.get_master_branch()+sep
            #label += sep+"filedrop-centos"+sep


        if with_url and 'url' in self.data and self.data['url']:
            repo_name = self.data['url'].replace("https://github.com/", "")
            label += sep + repo_name
            parent_repo=self.get_parent_repo(repo_name.replace(".git",""))
            if parent_repo:
                if parent_repo:
                    label += sep + "(Forked from: " + parent_repo + ")"
                    print(parent_repo)
        if self.data["branch"]:
            label += sep + sep + "branch =" + self.data["branch"] + sep + sep

        json = self.get_submodules_json()
        for each in json:
            each = each.split()
            repo_name=each[1].decode("utf-8")

            if repo_name.split("/")[-1]==self.data['name']:
                commit_id=each[0].decode("utf-8")
                tag=each[2].decode("utf-8").strip("()")
                label +=  sep+f"{tag}"+sep
                label=label+sep

        return label

    def get_submodules_json(self):
        submodules_list = subprocess.check_output(["git", "submodule", "status", "--recursive"],
                                                  stderr=subprocess.STDOUT, )
        submodules_list = submodules_list.splitlines()
        for submodules in submodules_list:
            submodules_json = submodules.split()
            commit_id = submodules_json[0]
            repo_name = submodules_json[1]
            repo_url = submodules_json[2]
        return submodules_list

class Parser:
    def parseGitModuleFile(self,file):
        config = configparser.ConfigParser()
        config.read(file)
        res = []
        for section in config.sections():
            p = os.path.join(config[section]['path'])
            u = config[section]['url']
            b=""
            if "branch" in  config[section]:
                b = config[section]['branch']
            # else:
            #     cmd = ["git", "symbolic-ref", "refs/remotes/origin/HEAD"]
            #     b = subprocess.check_output(cmd, encoding='UTF-8').split("/")[-1].strip()


            res.append((p, u, b))
        return res

    def parse(self,path, url=None,branch=None):
        if os.path.isfile(os.path.join(path, '.gitmodules')) is False:
            return Tree({'name': os.path.basename(os.path.normpath(path)),
                         'path': path, 'url': url,"branch": branch})

        tree = Tree({'name': os.path.basename(os.path.normpath(path)),
                     'path': path, 'url': url,"branch": branch})
        moduleFile = os.path.join(path, '.gitmodules')

        if os.path.isfile(moduleFile) is True:
            subs = self.parseGitModuleFile(moduleFile)
            print(subs)
            for p, u , b in subs:
                newPath = os.path.join(path, p)
                newTree = self.parse(newPath, u, b)
                tree.createChild(newTree)
        return tree

    def checkout_branch(self,branch):
        cmd = ["git", "fetch", "--all"]
        subprocess.check_output(cmd)
        cmd = ["git", "checkout",branch]
        subprocess.check_output(cmd)
        cmd = ["git", "reset", "--hard", "HEAD"]
        subprocess.check_output(cmd)
        cmd = ["git", "submodule", "update", "--init", "--recursive"]
        subprocess.check_output(cmd)

    def get_latest_tag(self):
        get_tag_commit = ["git", "rev-list", "--tags", "--max-count=1"]
        tags=["git", "fetch", "--all"]
        subprocess.check_output(tags)
        #tag_commit_id = subprocess.check_output(get_tag_commit, encoding='UTF-8').strip()
        #args = ["git", "describe", "--tags", tag_commit_id]
        args = ["git", "describe", "--tags","--abbrev=0"]
        args=["git", "for-each-ref" ,"refs/tags", "--sort=-taggerdate", "--format='%(refname:short)'" ,"--count=1"]
        latest_tag = subprocess.check_output(args, encoding='UTF-8').strip()
        return latest_tag

@click.command()
@click.option('-g', '--graphmode',
              default='scattered',
              show_default=True,
              help="GraphMode: scattered | clustered")
@click.option('-o', '--out',
              default='graph',
              show_default=True,
              help="Image filename")

@click.argument('repo')
@click.argument('branches')

@click.argument('path')

def main(repo, graphmode, out, branches, path):
    branches=branches.strip('][').split(' ')
    parser = Parser()
    latest_tag=parser.get_latest_tag()
    print(latest_tag)

    for branch in branches:
        graph_path = path + "/" + out + "_" + branch
        root = repo
        if branch == latest_tag:
            print(branch)
            graph_path = path + "/" + out + "_" + "latest_tag"
        parser.checkout_branch(branch=branch)
        tree = parser.parse(root)
        graph = pydot.Dot(graph_type='digraph',rankdir = 'LR')
        [graph, indentation] = tree.buildGraph(graph, None, 1, graphmode, with_url=True)
        filename = graph_path + '.png'
        graph.write_png(filename)

if __name__ == '__main__':
    main()



