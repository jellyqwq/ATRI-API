from ast import literal_eval
import base64
import json
import re
import logging as log
import os
import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import parse
from random import randrange
from utils import userid

import requests
from werkzeug._reloader import run_with_reloader

from config import SESSDATA, WEIBO_HOT_WORD_NUM, PROXY, GROUP_NAME_TO_GID

log.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=log.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

updateTime = 0
recommendList = None

class Bili(object):
    
    headers = {
        'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'origin': 'https://www.bilibili.com',
        'pragma': 'no-cache',
        'refer': 'https://www.bilibili.com/',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.3",
        'cookie': f'SESSDATA={SESSDATA}'
    }

    @classmethod
    def getHotWord(cls):
        url = 'http://s.search.bilibili.com/main/hotword'
        response = requests.get(url,cls.headers).json()
        if response['code'] == 0:
            timestamp = response['timestamp']
            message = time.strftime("%Y-%m-%d %H:%M %a", time.localtime(timestamp))
            HotWordLsit = [[li['pos'], li['keyword']] for li in response['list']]
            for i in HotWordLsit:
                message += '\n'+str(i[0])+'.'+i[1]
            log.info('\n'+message)
            return json.dumps({'msg': message})
        else:
            log.error('Failed to get hot search')
            return json.dumps({'error': 'Failed to get hot search'})
    
    @classmethod
    def toBiliShortUrl(cls, url):
        shareUrl = 'https://api.bilibili.com/x/share/click'
        data = {
            'build': '9331',
            'buvid': 'qp92wvbiiwercf5au381g1bzajou85hg',
            'oid': url,
            'platform': 'ios',
            'share_channel': 'COPY',
            'share_id': 'public.webview.0.0.pv',
            'share_mode': '3'
            }
        try:
            response = requests.post(shareUrl, data, cls.headers).json()
            return json.dumps({'msg':response['data']['content']})
        except:
            log.error('Failed to transform short link')
            return json.dumps({'error': 'Failed to transform short link'})

    @classmethod
    def biliVideoInfo(cls, abcode):
        if 'BV' in abcode or 'bv' in abcode:
            bvid = abcode
            response = requests.get('https://api.bilibili.com/x/web-interface/view?bvid={}'.format(bvid), headers=cls.headers)
        elif 'AV' in abcode or 'av' in abcode:
            aid = abcode[2:]
            response = requests.get('http://api.bilibili.com/x/web-interface/view?aid={}'.format(aid), headers=cls.headers)
        else:
            log.error('abcode: {}'.format(abcode))
            return json.dumps({'error': 'abcode error'})

        if response.json()['code'] == 0:
            data = response.json()['data']
            stat = data['stat']
            url = 'https://www.bilibili.com/video/{}'.format(abcode)
            shortLink = cls.toBiliShortUrl(url)
            if 'error' in shortLink:
                shortLink = url
            else:
                shortLink = json.loads(shortLink)['msg']
            return json.dumps({
                'aid': stat['aid'],
                'bvid': data['bvid'],
                'uname': data['owner']['name'],
                'face': data['pic'],
                'title': data['title'],
                'desc': data['desc'],
                'view': stat['view'],
                'danmaku': stat['danmaku'],
                'reply': stat['reply'],
                'favorite': stat['favorite'],
                'coin': stat['coin'],
                'share': stat['share'],
                'like': stat['like'],
                'shortLink': shortLink})
        else:
            log.error(response.json()['code'])
            return json.dumps({'error': 'Failed to get video info, please inquire bili status codes to get help'})

    @classmethod
    def getDynamicInfo(cls, dynamic_id):
        dynamicUrl = 'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail?dynamic_id={}'.format(dynamic_id)
        try:
            response = requests.get(dynamicUrl, headers=cls.headers).json()
        except:
            log.error('http请求错误')
            return json.dumps({'error': 'http请求错误'})
        else:
            if response['code'] == 0:
                # 动态共有属性
                dynamic_format = response['data']['card']['desc']['type']
                desc = response['data']['card']['desc']
                card = response['data']['card']['card']
                timestamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(desc['timestamp']))
                card = json.loads(card)

                # 图片动态
                if dynamic_format == 2:
                    content = card['item']['description']
                    pictures = card['item']['pictures']
                    imageList = [image['img_src'] for image in pictures]
                    return json.dumps({
                        'type': 2,
                        'uid': desc['uid'],
                        'uname': desc['user_profile']['info']['uname'],
                        'view': desc['view'],
                        'repost': desc['repost'],
                        'comment': desc['comment'],
                        'like': desc['like'],
                        'time': timestamp,
                        'content': content,
                        'imageList': imageList})
            
                # 纯文本动态
                elif dynamic_format == 4:
                    content = card['item']['content']
                    return json.dumps({
                        'type': 4,
                        'uid': desc['uid'],
                        'uname': desc['user_profile']['info']['uname'],
                        'view': desc['view'],
                        'repost': desc['repost'],
                        'comment': desc['comment'],
                        'like': desc['like'],
                        'time': timestamp,
                        'content': content})

                else:
                    log.error('该动态类型未完善')
                    return json.dumps({'error': '该动态类型未完善'})
            else:
                log.error('b站请求错误')
                return json.dumps({'error': 'b站请求错误'})

class Weibo(object):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.3"
    }
    
    @classmethod
    def getHotWord(cls):
        r = requests.get('https://weibo.com/ajax/side/hotSearch', headers=cls.headers) #
        r.encoding = 'utf-8'
        data = r.json()['data']
        hotgov = data['hotgov']
        HotWordLsit = [['Top', hotgov['word'], hotgov['icon_desc']]]
        realtime = data['realtime']
        num = 1
        HotWordTime = time.strftime("%Y-%m-%d %H:%M %a", time.localtime(time.time()))
        for hot_dict in realtime:
            if num == WEIBO_HOT_WORD_NUM + 1:
                break
            if 'label_name' in hot_dict.keys():
                HotWordLsit.append([str(num), hot_dict['word']])
                num += 1
        message = HotWordTime
        for i in HotWordLsit:
            message += '\n'+i[0]+'.'+i[1]
        log.info('\n'+message)
        return json.dumps({'msg': message})

class ImageKit(object):
    
    GNAME_TO_GID = GROUP_NAME_TO_GID
    GID_TO_GNAME = {GROUP_NAME_TO_GID[key]:key for key in GROUP_NAME_TO_GID}
    
    @staticmethod
    def saveCQImageHash(hashList, gid):
        try:
            os.makedirs('./CQImageHash/{}/'.format(gid), exist_ok=True)
            with open('./CQImageHash/{}/{}.txt'.format(gid, time.strftime("%Y-%m", time.localtime(time.time()))), mode='a+', encoding='utf-8') as f:
                for hashu in hashList:
                    f.seek(0)
                    if f.read(1) != '':
                        f.seek(0)
                        count = False
                        for line in f:
                            if hashu == line.strip() and count == False:
                                log.info('图片已存在')
                                count = True
                                break
                        if count == False:
                            f.seek(0,2)
                            f.write(hashu)
                            f.write('\n')
                    else:
                        f.write(hashu)
                        f.write('\n')
                return json.dumps({'msg': '保存成功'})
        except:
            log.error('CQ图url匹配失败')
            return json.dumps({'error': 'CQ图url匹配失败'})
    
    # 获取指定群聊的hash值个数
    @staticmethod
    def countOneGroupHash(gid):
        try:
            from itertools import (takewhile, repeat)
            buffer = 1024 * 1024
            os.makedirs('./CQImageHash/{}/'.format(gid), exist_ok=True)
            imgFolderList = os.listdir('./CQImageHash/{}/'.format(gid))
            count = 0
            for imgfoldername in imgFolderList:
                with open('./CQImageHash/{}/{}'.format(gid, imgfoldername), encoding='utf-8') as f:
                    buf_gen = takewhile(lambda x: x, (f.read(buffer) for _ in repeat(None)))
                    count += sum(buf.count('\n') for buf in buf_gen)
            return {'count': count}
        except:
            log.error('组图片统计失败')
            return json.dumps({'error': '组图片统计失败'})

    # 获取所有群的总张数
    @staticmethod
    def countAllGroupHash():
        try:
            from itertools import (takewhile, repeat)
            buffer = 1024 * 1024
            os.makedirs('./CQImageHash', exist_ok=True)
            groupList = os.listdir('./CQImageHash/')
            count = 0
            for i in groupList:
                imgFolderList = os.listdir('./CQImageHash/{}/'.format(i))
                for imgfoldername in imgFolderList:
                    with open('./CQImageHash/{}/{}'.format(i, imgfoldername), encoding='utf-8') as f:
                        buf_gen = takewhile(lambda x: x, (f.read(buffer) for _ in repeat(None)))
                        count += sum(buf.count('\n') for buf in buf_gen)
            count += sum(buf.count('\n') for buf in buf_gen)
            return {'count': count}
        except:
            log.error('所有组图片统计失败')

    # 获取图片
    @classmethod
    def getCQImage(cls, gid, imgnum):
        try:
            CQImageList = os.listdir('./CQImageHash/{}/'.format(gid))
            from itertools import (takewhile, repeat)
            buffer = 1024 * 1024
            imgSet = set()
            count = cls.countOneGroupHash(gid)['count']
            if count < int(imgnum):
                return json.dumps({'msg': '群{}图库数量不足'.format(cls.GID_TO_GNAME[gid])})
            imgList = []
            while len(imgSet) != int(imgnum) and count >= int(imgnum):
                r = random.randint(0,len(CQImageList)-1)
                with open('./CQImageHash/{}/{}'.format(gid, CQImageList[r]), 'r', encoding='utf-8') as f:
                    buf_gen = takewhile(lambda x: x, (f.read(buffer) for _ in repeat(None)))
                    x = random.randint(0,sum(buf.count('\n') for buf in buf_gen)+1)
                    num = 0
                    f.seek(0)
                    line = f.readline()
                    while line:
                        if num == x:
                            hashu = line.strip()
                            if hashu not in imgSet:
                                # this = f.tell()
                                # path = './CQImageHash/{}/{}'.format(gid, CQImageList[r])
                                # imgList = [imgurl, path, this]
                                imgList.append(hashu)
                                imgSet.add(hashu)
                                break
                            else:
                                break
                        else:
                            num += 1
                        line = f.readline()
            return json.dumps({'imgList': imgList})
        except:
            log.error('获取图片失败')
            return json.dumps({'error': '获取图片失败'})

    @classmethod
    def getImageBankInfo(cls):
        try:
            os.makedirs('./CQImageHash/', exist_ok=True)
            groupList = os.listdir('./CQImageHash/')
            if groupList != []:
                # 详细信息
                m = '总数: {}张\n'.format(cls.countAllGroupHash()['count'])
                for gid in groupList:
                    if gid in cls.GID_TO_GNAME.keys():
                        m += cls.GID_TO_GNAME[gid]+': '+str(cls.countOneGroupHash(gid)['count'])+'张\n'
                return json.dumps({'msg': m})
            else:
                log.error('图库空空如也')
                return json.dumps({'error': '图库空空如也'})
        except:
            log.error('图库信息获取失败')
            return json.dumps({'error': '图库信息获取失败'})

class AtriMath:

    @staticmethod
    def inversion_number(numList):
        try:
            msg = ''
            for num in numList:
                list_1 = []
                for i in str(num):
                    list_1.append(int(i))
                list_2 = []
                for i in list_1:
                    count = 0
                    for j in list_1[:list_1.index(i)]:
                        if j > i:
                            count += 1
                    list_2.append(count)
                result = 0
                for i in list_2:
                    result += i
                msg += '{}的逆序数为{}\n'.format(num, result)
            return json.dumps({'msg':msg})
        except:
            return json.dumps({'error':'逆序数获取失败'})

class AtriPixiv(object):

    # @https://github.com/MeteorsLiu/PyBot/blob/main/startpixiv.py

    # 通过图片url获取base64 string
    @staticmethod
    def getImage(picPath):
        headers = {
                'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1',
                'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'sec-fetch-site': 'cross-site',
                'sec-fetch-mode': 'no-cors',
                'sec-fetch-dest': 'image',
                'referer': 'https://www.pixiv.net/',
                'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh-MO;q=0.7,zh;q=0.6'
        }
        r = requests.get(url=picPath, headers=headers)
        return base64.b64encode(r.content).decode('utf-8')
    
    # 获取Pixiv排行榜
    @staticmethod
    def getList():
        r = requests.get("https://www.pixiv.net/touch/ajax/recommender/top?limit=500&lang=jp").json()
        return r["body"]["related"]

    # 定时刷新检测
    @staticmethod
    def event_minute_later(event, timeout):
        return event + timeout < time.time()

    # 随机获取top500榜一张图片的base64 string
    @classmethod
    def getTop(cls):
        global updateTime 
        global recommendList
        if recommendList:
            if updateTime != 0:
                if cls.event_minute_later(updateTime, 1440):
                    updateTime = time.time()
                    recommendList = cls.getList()
        else:
            updateTime = time.time()
            recommendList = cls.getList()
        
        id = recommendList[randrange(0, 499)]
        r = requests.get(f"https://www.pixiv.net/touch/ajax/illust/details/many?illust_ids[]={id}&lang=jp").json()
        return cls.getImage(r["body"]["illust_details"][0]["url"])
    
    # 获取指定画师id随机一个画作图片Base64 值,画师id,画师名字的json
    # 返回b64  画师id   画师名字
    #  b64      uid      uname
    @classmethod
    def SearchPainter(cls, id):
        r = requests.get("https://www.pixiv.net/touch/ajax/user/illusts?id={}&type=illust&lang=en".format(id)).json()
        if r["error"]:
            return json.dumps({"error": "画师{}不存在！".format(id)})
        if int(r["body"]["lastPage"]) > 1:
            message = requests.get("https://www.pixiv.net/touch/ajax/user/illusts?id={}&type=illust&lang=en&p={}".format(id, randrange(1, r["body"]["lastPage"]))).json()
        
        randlink = message["body"]["illusts"][randrange(0, len(message["body"]["illusts"])-1)]
        return json.dumps({
            "b64": cls.getImage(randlink["url"]), 
            "uid": randlink["author_details"]["user_id"],
            "uname": randlink["author_details"]["user_name"]
            })

    @classmethod
    def getRandom(cls):
        userlen = len(userid) - 1
        uid = userid[randrange(0, userlen)]
        return cls.SearchPainter(uid)
    
    # 根据关键词和张数从Pixiv获取含有n张图片的列表,列表中包含了n个字典
    @classmethod
    def getName(cls, name, num):
        message = requests.get(url='https://www.pixiv.net/touch/ajax/search/illusts?include_meta=0&type=illust_and_ugoira&s_mode=s_tag_full&word={}&lang=en'.format(name)).json()
        b64lists = []
        if int(message["body"]["lastPage"]) > 1:
            message = requests.get(url='https://www.pixiv.net/touch/ajax/search/illusts?include_meta=0&type=illust_and_ugoira&s_mode=s_tag_full&word={}&lang=en&p={}'.format(name, randrange(1, message["body"]["lastPage"]))).json()
        #print(message)
        for _ in range(int(num)):
            randlink = message["body"]["illusts"][randrange(0, len(message["body"]["illusts"])-1)]
            b64lists.append({
                "b64":    cls.getImage(randlink["url"]),
                "uid": randlink["author_details"]["user_id"],
                "uname": randlink["author_details"]["user_name"]
                })
        return json.dumps(b64lists)

    # 根据关键词搜索Pinterest,并随机抽取一个,返回其Base64值
    @classmethod
    def getPinterest(cls, name, num):
        payload = json.dumps(
            {
                "options": {
                    "query":name,
                    "scope": "pins",
                    "page_size":100,
                    "no_fetch_context_on_resource": False
                },
                "context": {}
            }
        )
        # sourceurl = "/search/pins/?q={}&rs=sitelinks_searchbox".format(name)
        message = requests.get('https://www.pinterest.com/resource/BaseSearchResource/get/?data={}'.format(payload)).json()
        # log.info(message)
        b64list = []
        if "resource_response" in message:
            for _ in range(int(num)):
                try:
                    b64list.append(cls.getPin(message["resource_response"]["data"]["results"][randrange(0,len(message["resource_response"]["data"]["results"])-1)]["images"]["orig"]["url"]))
                except:
                    return json.dumps({"error": "关键词{}不存在！".format(name)})
        return json.dumps(b64list)
    
class Handler(BaseHTTPRequestHandler, Bili):

    def _set_headers(self, len):
            self.send_response(200)
            self.send_header('Content-type','text/plain; charset=utf-8')
            self.send_header('Content-length', str(len))
            self.end_headers()

    def do_GET(self):
        if '/bhot' in self.path:
            message = Bili.getHotWord()
            self._set_headers(len(message))
            self.wfile.write(message.encode('utf-8'))
    
        if '/whot' in self.path:
            message = Weibo.getHotWord()
            self._set_headers(len(message))
            self.wfile.write(message.encode('utf-8'))
        
        if 'saveImage' in self.path:
            query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
            if len(query) == 0:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            elif 'gid' not in query or 'hashList' not in query:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            else:
                log.info(query['hashList'][0])
                message = ImageKit.saveCQImageHash(literal_eval(query['hashList'][0]), query['gid'][0])
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))
        
        if 'getCQImage' in self.path:
            query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
            if len(query) == 0:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            elif 'gid' not in query or 'num' not in query:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            else:
                message = ImageKit.getCQImage(query['gid'][0],query['num'][0])
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))

        if '/atrimath/invernum' in self.path:
            query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
            # log.info('query: %s', query)
            if len(query) == 0:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))     
            elif 'numList' not in query:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            else:
                log.info(query["numList"][0])
                message = AtriMath.inversion_number(literal_eval(query["numList"][0]))
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))

        if 'ImageBank' in self.path:
            message = ImageKit.getImageBankInfo()
            self._set_headers(len(message))
            self.wfile.write(message.encode('utf-8'))

        if 'getDynamicInfo' in self.path:
            query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
            if len(query) == 0:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            elif 'dynamic_id' not in query:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            else:
                message = Bili.getDynamicInfo(query['dynamic_id'][0])
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))
        
        if 'getBiliVideoInfo' in self.path:
            query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
            if len(query) == 0:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            elif 'abcode' not in query:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            else:
                message = Bili.biliVideoInfo(query['abcode'][0])
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))
        
        if "getrandom" in self.path:
            message = AtriPixiv.getRandom()
            self._set_headers(len(message))
            self.wfile.write(message.encode('utf-8'))

        if "getname" in self.path:
            query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
            if len(query) == 0:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            else:
                message = AtriPixiv.getName(query["name"][0], query["num"][0])
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))
        
        if "getpin" in self.path:
            query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
            if len(query) == 0:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            else:
                message = AtriPixiv.getPinterest(query["name"][0], query["num"][0])
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))

        if "getbyid" in self.path:
            query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
            if len(query) == 0:
                self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
            else:
                message = AtriPixiv.SearchPainter(query["id"][0])
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))

def main():
    host = '10.244.110.84'
    port = 6702
    log.info('服务器准备启动...')
    log.info('アトリは、高性能ですから!')
    HTTPServer((host,port),Handler).serve_forever() 

if __name__ == '__main__':
    run_with_reloader(main())
