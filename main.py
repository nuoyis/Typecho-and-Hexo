# -*- coding: utf-8 -*-
# 原作者:https://github.com/zhourongyu/Typecho2Hexo
# 新数据库借鉴作者:https://www.jianshu.com/p/4e72faebd27f
# 老版的源码丢了，这是反编译出来部分然后大部分重新编写的
import os
import re
import pymysql
import arrow
import urllib
import codecs
import yaml
import time
from markdown import markdown as parse_markdown

class typechohexo:
    def __init__(self):
        self.host = input("请输入数据库公网地址:")
        self.port = input("请输入数据库端口(回车即默认3306):")
        self.db = input("请输入数据库名称:")
        self.user = input("请输入数据库用户名称:")
        self.password = input("请输入数据库用户密码:")
        self.qianzhui = input("请输入表前缀(默认为typecho_,可直接回车):")
        if self.port == "":
            self.port = 3306
        if self.qianzhui == "":
            self.qianzhui = "typecho_"
        self.port = int(self.port)

        if self.host == "" or self.db == "" or self.host == "" or self.password == "":
            print("你的参数未输入完毕，请重新启动程序输入")
            input("按任意键继续")
            exit(1)

        print("正在与数据库，稍安勿躁~")
        try:
            self.conn = pymysql.connect(host=self.host, port=self.port, db=self.db, user=self.user, password=self.password)
        except Exception as e:
            print("检测发生错误，请重新检查:\n"
                "1.数据库用户密码等内容输入是否正确\n"
                "2.是否打开数据库端口\n"
                "请重新启动程序输入\n"
                 "错误日志:"+str(e))
            input("按任意键继续")
            exit(1)
        self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)

    def typecho_to_hexo(self):
        try:
            # 创建分类和标签
            self.cursor.execute("select type, slug, name from "+self.qianzhui+"metas")
            for cate in self.cursor.fetchall():
                path = 'data/分类/%s' % urllib.parse.unquote(cate['slug'])
                if not os.path.exists(path):
                    os.makedirs(path)
                f = codecs.open('%s/index.md' % path, 'w', "utf-8")
                f.write("title: %s\n" % urllib.parse.unquote(cate['slug']))
                f.write("date: %s\n" % arrow.now().format('YYYY-MM-DD HH:mm:ss'))
                # 区分分类和标签
                if cate['type'] == 'category':
                    f.write('type: "categories"\n')
                elif cate['type'] == 'tags':
                    f.write('type: "tags"\n')
                # 禁止评论
                f.write("comments: false\n")
                f.write("---\n")
                f.close()

            # 创建文章
            self.cursor.execute("select cid, title, slug, text, created from "+self.qianzhui+"contents where type='post'")
            for e in self.cursor.fetchall():
                title = re.sub('[\\/:*?"<>|]','-',e['title'].encode('raw_unicode_escape').decode("unicode-escape"))
                content = str(e['text'].replace('<!--markdown-->', ''))
                tags = []
                category = ""
                # 找出文章的tag及category
                self.cursor.execute(
                    "select type, name, slug from `"+self.qianzhui+"relationships` ts, "+self.qianzhui+"metas tm where tm.mid = ts.mid and ts.cid = %s",
                e['cid'])
                for m in self.cursor.fetchall():
                    if m['type'] == 'tag':
                        tags.append(m['name'])
                    if m['type'] == 'category':
                        category = urllib.parse.unquote(m['slug'])
                path = 'data/文章/'
                if not os.path.exists(path):
                    os.makedirs(path)
                f = codecs.open('%s%s.md' % (path, title), 'w', "utf-8")
                f.write("---\n")
                f.write("title: %s\n" % title)
                f.write("date: %s\n" % arrow.get(e['created']).format('YYYY-MM-DD HH:mm:ss'))
                f.write("categories: %s\n" % category)
                f.write("tags: [%s]\n" % ','.join(tags))
                f.write("---\n")
                f.write(content)
                f.close()
            self.conn.close()
            print("操作完毕，请检查同目录下生成的文件")
        except Exception as e:
            print("发生错误，请重新检查数据库内是否有正确的表项，请重新启动程序运行\n"
                  "错误日志:"+str(e))
            exit(1)

    def hexo_to_typecho(self,dir):
        metas = []

        for file in os.listdir(dir):
            if os.path.isdir(os.path.join(dir, file)):
                if file == '_posts':
                    self.cursor.execute('SELECT * FROM `' + self.qianzhui + 'contents` ORDER BY `cid` DESC LIMIT 1')
                    results = self.cursor.fetchall()
                    if not results:
                        nuoyis = 0
                        print('当前数据库内没有数据')
                    else:
                        nuoyis = results[0]['cid']
                        print('当前typecho内cid最大值为:' + str(nuoyis))
                    print('正在导入Hexo文章')
                    for postfile in os.listdir(os.path.join(dir, file)):
                        print('正在执行:' + postfile)
                        (yaml_data, markdown_content) = parse_markdown(os.path.join(dir, file, postfile))
                        post = '<!--markdown-->' + markdown_content + "\n\n</br>由<a href='https://blog.nuoyis.net'>诺依阁</a>提供Hexo转Typecho软件支持\n"
                        if 'abbrlink' in yaml_data:
                            sql = 'SELECT * FROM `' + self.qianzhui + 'contents` WHERE slug = %s'
                            self.cursor.execute(sql, yaml_data['abbrlink'])
                            results = self.cursor.fetchall()
                            if not results:
                                slug = yaml_data['abbrlink']
                            else:
                                print(f'''abbrlink值重复,文件slug:{yaml_data['abbrlink']}, 数据库存在:{results[0]['slug']} 已改为cid:{nuoyis}''')
                                slug = nuoyis
                        else:
                            slug = nuoyis
                        title = yaml_data['title']
                        posttime = str(yaml_data['date'])
                        localtime = time.strptime(posttime, '%Y-%m-%d %H:%M:%S')
                        nuoyis = nuoyis + 1
                        sql = 'INSERT INTO `' + self.qianzhui + "contents` (`cid`, `title`, `slug`, `created`, `modified`, `text`, `order`, `authorId`, `template`, `type`, `status`, `password`, `commentsNum`, `allowComment`, `allowPing`, `allowFeed`, `parent`, `views`, `stars`) VALUES (%s, %s, %s, %s, %s, %s,0,1,NULL,'post','publish',NULL, '0', '1', '1', '1', '0', '0', '0')"
                        self.cursor.execute(sql, (nuoyis, title, slug, int(time.mktime(localtime)), int(time.time()), post))
                        self.conn.commit()
                        if file not in ('_data', '_posts', '_posts'):
                            metas.append(file)
        print('执行完毕，请登录数据库查看')
        return None

if __name__ == "__main__":
    init = typechohexo()
    init.typecho_to_hexo()
    init.hexo_to_typecho()
    input("请按任意键继续")