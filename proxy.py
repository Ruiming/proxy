#!/usr/bin/python
# -*- coding:utf-8 -*-
# __author__ = 'Ruiming Zhuang'
# 代理爬取
import urllib2
import re
import threading
import cookielib
import time
import multiprocessing

proxyList = []              # 全部代理列表
checkedProxyList = []       # 检验可用代理列表
proxy_ok = []               # 最终代理列表
f = open("proxy_list.txt", 'a')


class Target(multiprocessing.Process):

    def __init__(self, website):
        multiprocessing.Process.__init__(self)
        self.page = website["page"]
        self.url = website["pageurl"]
        self.pattern = website["pattern"]
        self.header = website["header"]
        self.links = []

    def run(self):
        # 使用正则替换数字
        # 只适用于网站链接只有页码为数字的情况
        url_pattern = re.compile('(1){1}', re.S)
        get_threads = []
        check_threads = []
        if self.page > 0:
            for x in xrange(1, self.page):
                link = re.sub(url_pattern, str(x), self.url)
                self.links.append(link)
        else:
            self.links.append(self.url)
        # 抓取代理，多线程，每页一个线程
        print '.'*10 + "正在读取网站上的代理" + '.'*10
        for x in range(len(self.links)):
            t = GetProxy(self, self.links[x])
            get_threads.append(t)
        for x in range(len(self.links)):
            get_threads[x].start()
        for x in range(len(self.links)):
            get_threads[x].join()
        print '.'*10+"一共抓取了%s个代理" % len(proxyList) + '.'*10
        # 检验代理，多线程，每页一个线程
        for i in range(20):
            t = CheckProxy(proxyList[((len(proxyList)+19)/20) * i:((len(proxyList)+19)/20) * (i+1)])
            check_threads.append(t)
        for i in range(len(check_threads)):
            check_threads[i].start()
        for i in range(len(check_threads)):
            check_threads[i].join()
        print '.'*10+"总共有%s个代理通过校验" % len(checkedProxyList) +'.'*10
        # 存入文件
        for proxy in checkedProxyList:
            proxy_url = proxy[0] + ":" + proxy[1]
            proxy_ok.append(proxy_url)
            f.write("%s:%s\r\n" % (proxy[0], proxy[1]))
        print '.'*10 + "成功存入文件 proxy_list.txt" + '.'*10


class GetProxy(threading.Thread):
    # 接收target的header,正则以及抓取页面链接
    def __init__(self, target, link):
        threading.Thread.__init__(self)
        self.pattern = target.pattern
        self.header = target.header
        self.link = link

    def get_proxy(self):
        retry = True
        while retry:
            # 默认使用代理
            try:
                proxy_support = urllib2.ProxyHandler()
                opener = urllib2.build_opener(proxy_support)
                urllib2.install_opener(opener)
                request = urllib2.Request(self.link, None, self.header)
                response = urllib2.urlopen(request)
                response = response.read()
                match = self.pattern.findall(response)
                for line in match:
                    ip = line[0]
                    port = line[1]
                    proxy = [ip, port]
                    proxyList.append(proxy)
                retry = False
            except Exception, e:
                retry = True

    def run(self):
        self.get_proxy()


class CheckProxy(threading.Thread):
    def __init__(self, proxy_list):
        threading.Thread.__init__(self)
        self.proxyList = proxy_list
        self.timeout = 8
        # 测试网站
        self.testStr = "html"
        self.testURL = "http://www.baidu.com"

    def check_proxy(self):
        cookies = urllib2.HTTPCookieProcessor()
        for proxy in self.proxyList:
            proxy_handler = urllib2.ProxyHandler({"http": r'http://%s:%s' % (proxy[0], proxy[1])})
            opener = urllib2.build_opener(cookies, proxy_handler)
            # 根据测试网站自行补全headers
            opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                                'Chrome/48.0.2564.116 Safari/537.36')]
            t1 = time.time()
            try:
                request = opener.open(self.testURL, timeout = self.timeout)
                result = request.read()
                timeused = time.time() - t1
                pos = result.find(self.testStr)
                if pos > 1:
                    print r'success --http://%s:%s' % (proxy[0], proxy[1])
                    checkedProxyList.append((proxy[0], proxy[1]))
                else:
                    print r'fail    --http://%s:%s' % (proxy[0], proxy[1])
                    continue
            except Exception, e:
                print r'fail    --http://%s:%s' % (proxy[0], proxy[1])
                continue

    def run(self):
        self.check_proxy()

if __name__ == '__main__':
    user_agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) ' \
                 'Version/9.0 Mobile/13B143 Safari/601.1'
    website = [
        {
            'pageurl': r"http://www.proxy.com.ru/list_1.html",
            'page': 10,
            'header': {
                'Referer': 'www.proxy.com.ru',
                'User-Agent': user_agent,
                'Host': 'www.proxy.com.ru'
            },
            'pattern': re.compile('<tr.*?<td>\d{1,4}</t.*?<td>(.*?)<.*?<td>(.*?)</td>', re.S)
        },
        {
            'pageurl': r"https://www.us-proxy.org/",
            'page': 0,
            'header': {
                'Referer': 'https://www.us-proxy.org/',
                'User-Agent': user_agent,
            },
            'pattern': re.compile('<tr><td>(.*?)</td><td>(\d{1,5})</td>', re.S)
        },
        {
            'pageurl': r"http://www.cz88.net/proxy/",
            'page': 0,
            'header': {
                'Referer': 'www.cz88.net',
                'User-Agent': user_agent,
                'Host': 'www.cz88.net'
            },
            'pattern': re.compile('<li><div.*?ip">(.*?)</div>.*?port">(.*?)</div>')
        },
    ]
    n = 0
    proxy_process = []
    for x in range(len(website)):
        p = Target(website[x])
        proxy_process.append(p)
    for x in range(len(website)):
        proxy_process[x].start()
    for x in range(len(website)):
        proxy_process[x].join()
    f.close()
