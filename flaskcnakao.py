# -*- coding: utf-8 -*-
import re
import flask
import json
import requests
import logging
logging.basicConfig(level=logging.INFO)
# project supposed
# https://flask.palletsprojects.com/en/2.0.x/quickstart/
api = flask.Flask(__name__)

@api.route('/bili/hotword', methods=['GET'])
def hotword():
    from ClassBili import Bili
    return json.dumps(Bili().getHotWord(), ensure_ascii=False)

@api.route('/bili/shortlink', methods=['get'])
def shortlink():
    from ClassBili import Bili
    url =  flask.request.values.get('url')
    if url:
        r = Bili().toBiliShortUrl(url)
        if r['status'] == 0:
            x = {
                'status': 0,
                'data': r['data']
            }
            return json.dumps(x, ensure_ascii=False)
        else:
            x = {
                'status': -1,
                'data': r['data']
            }
            return json.dumps(x, ensure_ascii=False)
    else:
        x = {
            'status': -2,
            'data': 'Post paramenter can not null'
        }
        return json.dumps(x, ensure_ascii=False)

@api.route('/bili/videoinfo', methods=['GET'])
def videoinfo():
    from ClassBili import Bili
    abcode =  flask.request.values.get('abcode')
    return json.dumps(Bili().biliVideoInfo(abcode), ensure_ascii=False)

@api.route('/bili/dynamicinfo', methods=['GET'])
def dynamicinfo():
    from ClassBili import Bili
    did = flask.request.values.get('id')
    return json.dumps(Bili().getDynamicInfo(did), ensure_ascii=False)

@api.route('/weibo/hotword', methods=['GET'])
def wbhotword():
    from ClassWeiBo import Weibo
    return json.dumps(Weibo().getHotWord(), ensure_ascii=False)

@api.route('/parse/abcode', methods=['GET'])
def parse_abcode():
    from ClassRegular import Regular
    message = flask.request.values.get('message')
    return json.dumps(Regular().biliVideoUrl(message), ensure_ascii=False)

@api.route('/parse/b23', methods=['GET'])
def parse_b23():
    from ClassRegular import Regular
    message = flask.request.values.get('message')
    return json.dumps(Regular().biliShortUrl(message), ensure_ascii=False)

@api.route('/parse/bdynamci', methods=['GET'])
def parse_bdynamci():
    from ClassRegular import Regular
    message = flask.request.values.get('message')
    return json.dumps(Regular().biliDynamicId(message), ensure_ascii=False)

@api.route('/parse/savecqimgurl', methods=['GET'])
def parse_savecqimgurl():
    from ClassRegular import Regular
    message = flask.request.values.get('message')
    gid = flask.request.values.get('gid')
    return json.dumps(Regular().saveCQImageUrl(message, gid), ensure_ascii=False)

@api.route('/parse/cqimginfo', methods=['GET'])
def parse_cqimginfo():
    from ClassRegular import Regular
    groupname = flask.request.values.get('groupname')
    gid = flask.request.values.get('gid')
    if groupname:
        return json.dumps(Regular().getCQImageUrlInfo(gid, groupname), ensure_ascii=False)
    else:
        return json.dumps(Regular().getCQImageUrlInfo(gid), ensure_ascii=False)

@api.route('/parse/getcqimage', methods=['GET'])
def parse_getcqimage():
    from ClassRegular import Regular
    gid = flask.request.values.get('gid')
    num = flask.request.values.get('num')
    return json.dumps(Regular().getCQImage(gid, num), ensure_ascii=False)
    
@api.route('/parse/getgroupinfo', methods=['GET'])
def parse_getgroupinfo():
    from ClassRegular import Regular
    return json.dumps(Regular().getGroupInfo(), ensure_ascii=False)

@api.route('/parse/delete_image', methods=['GET'])
def parse_delete_image():
    from ClassRegular import Regular
    path = flask.request.values.get('path')
    # this = flask.request.values.get('this')
    hashv = flask.request.values.get('hashv')
    return json.dumps(Regular().deleteImage(path, hashv), ensure_ascii=False)

@api.route('/parse/save_new_word', methods=['GET'])
def parse_save_new_word():
    from ClassRegular import Regular
    new_word = flask.request.values.get('new_word')
    return json.dumps(Regular().new_words_save(new_word), ensure_ascii=False)

@api.route('/parse/chat', methods=['GET'])
def parse_chat():
    from chat import getmess
    m = flask.request.values.get('message')
    return json.loads(getmess(m), ensure_ascii=False)


if __name__ == '__main__':
    api.run(port=6702, debug=True, host='127.0.0.1')


'''  "PUSH_PLUS_USER": "202112241557",
  "ONEPUSH": {
    "notifier": "pushplus",
    "params": {
      "markdown": false,
      "token": "5c138ae92a004762aea6f9b228eb2ecd"
    }
  }'''