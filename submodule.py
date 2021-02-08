import os
import configparser
import subprocess
import pydot
import click
import requests



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

    def buildGraph(self, graph, parent, indentation, graphmode, with_url,level=0):
        color="#ACE7EF"

        if level==0:
            color="#FFBEBC"
        elif level==1:
            color="#FFF5BA"

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


    def get_Label(self, with_url, sep=' - '):
        label = ""
        main_repo_name=self.get_main_repo_name()
        if main_repo_name in self.data['name']:
            label=sep + label+self.data["name"]
            label = label + sep+self.get_master_tag()+sep

        if with_url and 'url' in self.data and self.data['url']:
            repo_name = self.data['url'].replace("https://github.com/", "")
            label += sep + repo_name
            parent_repo=self.get_parent_repo(repo_name.replace(".git",""))
            if parent_repo:
                if parent_repo:
                    label += sep + "(Forked from: " + parent_repo + ")"
                    print(parent_repo)

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
            res.append((p, u))
        return res

    def parse(self,path, url=None):
        if os.path.isfile(os.path.join(path, '.gitmodules')) is False:
            return Tree({'name': os.path.basename(os.path.normpath(path)),
                         'path': path, 'url': url})

        tree = Tree({'name': os.path.basename(os.path.normpath(path)),
                     'path': path, 'url': url})
        moduleFile = os.path.join(path, '.gitmodules')

        if os.path.isfile(moduleFile) is True:
            subs = self.parseGitModuleFile(moduleFile)
            for p, u in subs:
                newPath = os.path.join(path, p)
                newTree = self.parse(newPath, u)
                tree.createChild(newTree)
        return tree

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

def main(repo, graphmode, out):
    root = repo
    parser=Parser()
    tree = parser.parse(root)
    graph = pydot.Dot(graph_type='digraph',rankdir = 'LR')
    [graph, indentation] = tree.buildGraph(graph, None, 1, graphmode, with_url=True)
    filename = out + '.png'
    graph.write_png(filename)

if __name__ == '__main__':
    main()



