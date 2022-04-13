# -*- coding: utf-8 -*-

import asyncio
import time
import base64
import json
import logging as log
import re
import requests
import websockets
from werkzeug._reloader import run_with_reloader
from config import GROUP_NAME_TO_GID, FUNCTION_MESSAGE, COEH

alcoeh = False

log.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s', 
    level=log.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

allow_group_list = [980514385,649451770] # 
allow_user_list = [577430840] #

class Robot(object):
    
    def __init__(self, websocket, loop):
        self.websockets = websocket
        self.loop = loop
        self.GNAME_TO_GID = GROUP_NAME_TO_GID
        self.isprivate = False
        self.group_id = None
        self.user_id = None

    # 消息过滤设置
    def filter_container(self):
        if self.group_id in allow_group_list:
            self.group_id = self.group_id
        else:
            self.group_id = None
        if self.user_id in allow_user_list:
            self.user_id = self.user_id
        else:
            self.user_id = None
        return self.group_id, self.user_id
    
    # 发送消息
    async def sendMessage(self, message):
        self.group_id, self.user_id = self.filter_container()
        if self.group_id != None or self.user_id != None:
            if self.isprivate:
                # logging.info(f'私聊id{self.user_id}')
                await self.websockets.send(
                    json.dumps(
                        {
                            "action": "send_private_msg",
                            "params": {
                                "user_id": self.user_id,
                                "message": message
                            }
                        }
                    )
                )
            else:
                await self.websockets.send(
                    json.dumps(
                        {
                            "action": "send_group_msg",
                            "params": {
                                "group_id": self.group_id,
                                "message": message
                            }
                        }
                    )
                )
    
    # 发送图片两种模式
    async def sendImage(self, b64=False, url=False):
        self.group_id, self.user_id = self.filter_container()
        if self.group_id != None or self.user_id != None:
            if self.isprivate:
                if b64:
                    await self.websockets.send(
                        json.dumps(
                            {
                                "action": "send_private_msg",
                                "params": {
                                    "user_id": self.user_id,
                                    "message": "[CQ:image,file=base64://{}]".format(b64)
                                }
                            }
                        )
                    )
                else:
                    await self.websockets.send(
                        json.dumps(
                            {
                                "action": "send_private_msg",
                                "params": {
                                    "user_id": self.user_id,
                                    "message": "[CQ:image,file={}]".format(url)
                                }
                            }
                        )
                    )
            else:
                if b64:
                    await self.websockets.send(
                        json.dumps(
                            {
                                "action": "send_group_msg",
                                "params": {
                                    "group_id" : self.group_id,
                                    "message": "[CQ:image,file=base64://{}]".format(b64)
                                }
                            }
                        )
                    )
                else:
                    await self.websockets.send(
                        json.dumps(
                            {
                                "action": "send_group_msg",
                                "params": {
                                    "group_id" : self.group_id,
                                    "message": "[CQ:image,file={}]".format(url)
                                }
                            }
                        )
                    )

    # 通过mid获取消息
    async def getMessage(self, mid):
        await self.websockets.send(
            json.dumps(
                {
                    "action": "get_msg",
                    "params": {
                        "message_id": int(mid),
                    }
                }
            )
        )
        return json.loads(await self.websockets.recv())

    async def saveImageHash(self, hashList):
        requests.get('http://127.0.0.1:6702/saveImage?gid={}&hashList={}'.format(self.group_id, hashList))

    # b站的信息转发模块
    async def sendBiliMessage(self, message):
        message = message.replace('\\','')
        log.info(message)
        # 当动态域名在消息中
        if 't.bilibili.com' in message or 'm.bilibili.com' in message:
            try:
                dynamic_id = re.findall(r'(?:t|m).bilibili.com/(?:dynamic/)?([0-9]+)', message)[0]
            except:
                log.error('动态id匹配失败') 
                await self.sendMessage('动态id匹配失败')
            else:
                info = requests.get(f'http://127.0.0.1:6702/getDynamicInfo?dynamic_id={dynamic_id}').json()
                # 判断请求处理状态
                if 'error' in info:
                    await self.sendMessage(info['error'])
                else:
                    # 动态基本消息模板
                    if info['type'] in [2,4]:
                        # 发布时间,up名字
                        await self.sendMessage('时间:{}\nUP:{}'.format(info['time'],info['uname']))
                        await self.sendMessage('内容:{}\n\n浏览:{} 转发:{}\n评论:{} 点赞{}'.format(info['content'], info['view'], info['repost'], info['comment'], info['like']))

                    # 2类型动态有图片列表,调用发图
                    if info['type'] in [2]:
                        for dynamic_image in info['imageList']:
                            # r = requests.get(dynamic_image)
                            # b64 = base64.b64encode(r.content).decode('utf-8')
                            # await self.sendImage(b64=b64)
                            await self.sendMessage(dynamic_image)
                            await self.sendImage(url=dynamic_image)
                            
        # https://www.bilibili.com/video/BV1db4y1e7B2
        # 当视频链接存在于b站域名下时
        elif 'bilibili.com/video' in message:
            try:
                abcode = re.findall(r'video/([0-9A-Za-z]+)', message)[0]
            except:
                log.error('abcode匹配失败')
                await self.sendMessage('abcode匹配失败')
            else:
                info = requests.get(f'http://127.0.0.1:6702/getBiliVideoInfo?abcode={abcode}').json()
                if 'error' in info:
                    await self.sendMessage(info['error'])
                else:
                    await self.sendMessage('标题:{}\n作者:{}\n\n简介:{}'.format(info['title'], info['uname'], info['desc']))
                    await self.sendMessage('评论:{} 弹幕:{}\n硬币:{} 收藏:{}\n点赞:{} 分享:{}'.format(info['reply'], info['danmaku'], info['coin'], info['favorite'], info['like'], info['share']))
                    await self.sendMessage('[CQ:image,file={}]\n播放量:{}\n传送门->{}'.format(info['face'], info['view'], info['shortLink']))
        
    async def sendB23Message(self, message):
        try:
            message = message.replace('\/','/')
            b23 = re.findall(r'http(?:s)://b23.tv/[a-zA-Z0-9]+', message)[0]
        except:
            log.error('重定向链接匹配失败')
            await self.sendMessage('重定向链接匹配失败')
        else:
            response = requests.get(b23, allow_redirects=False) #关闭重定向,取请求标头
            headers = dict(response.headers)
            goal = headers['Location']
            if 'bilibili.com' in goal:
                await self.sendBiliMessage(goal)
            else:
                await self.sendMessage(f'非b站链接,请注意访问\n{goal}')
    
    def getRandom(self):
        r = requests.get("http://127.0.0.1:6702/getrandom")
        return json.loads(r.content.decode('utf-8'))
    
    async def sendRandomPic(self, times):
        for _ in range(times):
            r = self.getRandom()
            # log.info(r)
            # r: a dict
            if "error" in r:
                await self.sendMessage(r["error"])
                return
            else:
                await asyncio.gather(
                    self.sendImage(b64=r["b64"]),
                    self.sendMessage("画师ID:{}, 画师名字: {}".format(r["uid"], r["uname"])))

    async def searchPicAndSend(self, name, times):
        try:
            message = requests.get("http://127.0.0.1:6702/getname?name={}&num={}".format(name, times)).json()
        except:
            await self.sendMessage("关键词{}无法查找".format(name))
            return
        #print(message)
        if "error" in message:
            await self.sendMessage(message["error"])
            return
        for m in message:
            await asyncio.gather(
                self.sendImage(b64=m["b64"]),
                self.sendMessage("画师ID:{}, 画师名字: {}".format(m["uid"], m["uname"]))
            )

    async def searchPinterest(self, word, num):
        try:
            message = requests.get("http://127.0.0.1:6702/getpin?name={}&num={}".format(word, num)).json()
        except:
            await self.sendMessage("关键词{}无法查找".format(word))
            return
        if "error" in message:
            await self.sendMessage(message["error"])
            return
        for m in message:
            await self.sendImage(b64=m)
        
    async def sendPaimonMessage(self, message):
        if '功能' in message:
            await self.sendMessage(FUNCTION_MESSAGE)
            return
        
        elif '逆序数' in message:
            numList = re.findall(r'([0-9]+)', message)
            r = requests.get(f'http://127.0.0.1:6702/atrimath/invernum?numList={numList}').json()
            if 'error' in r:
                await self.sendMessage(r['error'])
                return
            else:
                await self.sendMessage(r['msg'])
                return
        
        elif '派蒙图库' == message:
            r = requests.get('http://127.0.0.1:6702/ImageBank').json()
            log.info(r)
            if 'error' in r:
                await self.sendMessage(r['error'])
                return
            else:
                await self.sendMessage(r['msg'])
                return

        elif '图' in message or '张' in message or '点' in message:
            m = message
            m = re.sub(r'[零一二三四五六七八九十]+一张', '1张', m)
            m = re.sub(r'[零一二三四五六七八九十]+二张', '2张', m)
            m = re.sub(r'[零一二三四五六七八九十]+三张', '3张', m)
            m = re.sub(r'[零一二三四五六七八九十]+几张', '3张', m)
            m = re.sub(r'[零一二三四五六七八九十]+四张', '4张', m)
            m = re.sub(r'[零一二三四五六七八九十]+五张', '5张', m)
            m = re.sub(r'[零一二三四五六七八九十]+六张', '6张', m)
            m = re.sub(r'[零一二三四五六七八九十]+七张', '7张', m)
            m = re.sub(r'[零一二三四五六七八九十]+八张', '8张', m)
            m = re.sub(r'[零一二三四五六七八九十]+九张', '9张', m)
            m = re.sub(r'[零一二三四五六七八九十]+十张', '10张', m)
            
            # 数量匹配
            if '张' in m:
                needList = re.findall(r'([0-9]+)张',m)
                if len(needList) == 1:
                    num = int(needList[0])
                    if num <= 10:
                        pass
                    else:
                        num = 1
                else:
                    num = 1
            else:
                num = 1

            # 搜索词匹配
            if len(re.findall(r'(派蒙)', m)) > 1:
                word = '派蒙'
                await self.searchPicAndSend(word, num)
                return
            else:
                wordList = re.findall(r'(?:点|张)(.*?)(?:|图|涩图)$',m)
                if len(wordList) == 1:
                    word = wordList[0]
                    if word =='':
                        await self.sendRandomPic(num)
                        return
                    else:
                        await self.searchPicAndSend(word, num)
                        return
                else:
                    await self.sendRandomPic(num)
                    return

        elif '派蒙' == message:
            await self.sendMessage('你好!')
            return

        else:
            await self.sendMessage('前面的区域以后再来探索吧!')
            return
    


async def work(message,robot):
    log.info(message)
    if 'CQ:image' in message and robot.isprivate == False:
        hashList = re.findall(r'CQ:image,file=([0-9a-z]{32}).image',message)
        await robot.saveImageHash(hashList)

    if 'bilibili.com' in message:
        await robot.sendBiliMessage(message)

    if 'b23.tv' in message:
        await robot.sendB23Message(message)

    # b站热搜
    if 'bhot' == message:
        await robot.sendMessage('b站热搜来咯~（。＾▽＾）')
        r = requests.get('http://127.0.0.1:6702/bhot').json()
        if 'error' in r:
            await robot.sendMessage(r['error'])
        await robot.sendMessage(r['msg'])

    # 微博热搜
    if 'whot' == message:
        await robot.sendMessage('微博热搜来咯~（。＾▽＾）')
        r = requests.get('http://127.0.0.1:6702/whot').json()
        if 'error' in r:
            await robot.sendMessage(r['error'])
        await robot.sendMessage(r['msg'])

    if '派蒙' in message:
        await robot.sendPaimonMessage(message)

loop = asyncio.get_event_loop()

async def echo(websocket, path):
    global alcoeh
    robot = Robot(websocket, loop)
    while websocket.open:
        message = await websocket.recv()
        # 将原始字符串json加载成字典形式
        message = json.loads(message)
        
        # 整点报时-主动行为
        t = time.localtime()
        tm_hour = t[3]
        tm_min = t[4]
        change_tm = {
            6:'早上六点',
            7:'早上七点',
            8:'早上八点',
            9:'早上九点',
            10:'早上十点',
            11:'早上十一点',
            12:'正午十二点',
            13:'下午一点',
            14:'下午两点',
            15:'下午三点',
            16:'下午四点',
            17:'下午五点',
            18:'傍晚六点',
            19:'晚上七点',
            20:'晚上八点',
            21:'晚上九点',
            22:'晚上十点',
            23:'晚上十一点'
        }
        if 6 <= tm_hour <= 23 and tm_min == 0 and alcoeh == False:
            # 指定发送位置
            robot.isprivate = False
            robot.group_id = 649451770
            chime = ''
            if tm_hour in COEH:
                chime += ',' + COEH[tm_hour]

            r = robot.getRandom()
            if 'error' in r:
                alcoeh = True
                await robot.sendMessage('{}了{}'.format(change_tm[tm_hour],chime))
            else:
                alcoeh = True
                await robot.sendMessage('{}了{}\n[CQ:image,file=base64://{}]'.format(change_tm[tm_hour],chime,r['b64']))
        elif tm_min == 1:
            alcoeh = False
        else:
            pass

        # 消息分流-被动行为
        if 'message_type' in message:
            if message['message_type'] == 'private':
                robot.isprivate = True
                robot.user_id = message['sender']['user_id']
            else:
                robot.isprivate = False
                robot.group_id = message['group_id']
            await work(message['message'], robot)

async def main():
    async with websockets.serve(echo, "127.0.0.1", 6701):
        await asyncio.Future()  # run forever

def main_loop():
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.close()
    except:
        raise

if __name__ == "__main__":
    run_with_reloader(main_loop)
