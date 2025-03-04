import json
import pathlib
import random
import os
from biliup.plugins.bili_webup import BiliBili, Data

from utils.log import bilibili_logger


def extract_keys_from_json(data):
    """Extract specified keys from the provided JSON data."""
    keys_to_extract = ["SESSDATA", "bili_jct", "DedeUserID__ckMd5", "DedeUserID", "access_token"]
    extracted_data = {}

    # Extracting cookie data
    for cookie in data['cookie_info']['cookies']:
        if cookie['name'] in keys_to_extract:
            extracted_data[cookie['name']] = cookie['value']

    # Extracting access_token
    if "access_token" in data['token_info']:
        extracted_data['access_token'] = data['token_info']['access_token']

    return extracted_data


def read_cookie_json_file(filepath: pathlib.Path):
    with open(filepath, 'r', encoding='utf-8') as file:
        content = json.load(file)
        return content


def random_emoji():
    emoji_list = ["🍏", "🍎", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🍈", "🍒", "🍑", "🍍", "🥭", "🥥", "🥝",
                  "🍅", "🍆", "🥑", "🥦", "🥒", "🥬", "🌶", "🌽", "🥕", "🥔", "🍠", "🥐", "🍞", "🥖", "🥨", "🥯", "🧀", "🥚", "🍳", "🥞",
                  "🥓", "🥩", "🍗", "🍖", "🌭", "🍔", "🍟", "🍕", "🥪", "🥙", "🌮", "🌯", "🥗", "🥘", "🥫", "🍝", "🍜", "🍲", "🍛", "🍣",
                  "🍱", "🥟", "🍤", "🍙", "🍚", "🍘", "🍥", "🥮", "🥠", "🍢", "🍡", "🍧", "🍨", "🍦", "🥧", "🍰", "🎂", "🍮", "🍭", "🍬",
                  "🍫", "🍿", "🧂", "🍩", "🍪", "🌰", "🥜", "🍯", "🥛", "🍼", "☕️", "🍵", "🥤", "🍶", "🍻", "🥂", "🍷", "🥃", "🍸", "🍹",
                  "🍾", "🥄", "🍴", "🍽", "🥣", "🥡", "🥢"]
    return random.choice(emoji_list)


class BilibiliUploader(object):
    def __init__(self, cookie_data, file: pathlib.Path, title, desc, tid, tags, dtime):
        self.upload_thread_num = 3
        self.copyright = 1
        self.lines = 'AUTO'
        self.cookie_data = cookie_data
        self.file = file
        self.title = title
        self.desc = desc
        self.tid = tid
        self.tags = tags
        self.dtime = dtime
        self._init_data()

    def _init_data(self):
        self.data = Data()
        self.data.copyright = self.copyright
        self.data.title = self.title
        self.data.desc = self.desc
        self.data.tid = self.tid
        self.data.set_tag(self.tags)
        self.data.dtime = self.dtime

    async def upload(self):
        with BiliBili(self.data) as bili:
            bili.login_by_cookies(self.cookie_data)
            bili.access_token = self.cookie_data.get('access_token')
            
            # 使用upload_file方法，但避免嵌套asyncio.run()
            file_path = str(self.file) if isinstance(self.file, pathlib.Path) else self.file
            
            # 获取上传信息
            if not bili._auto_os:
                bili._auto_os = bili.probe()
                if not bili._auto_os:
                    bilibili_logger.error(f'[-] 获取上传线路失败')
                    return False
                
            # 准备上传参数
            total_size = os.path.getsize(file_path)
            with open(file_path, 'rb') as f:
                query = {
                    'r': bili._auto_os['os'],
                    'profile': 'ugcupos/bup' if 'upos' == bili._auto_os['os'] else "ugcupos/bupfetch",
                    'ssl': 0,
                    'version': '2.8.12',
                    'build': 2081200,
                    'name': os.path.basename(file_path),
                    'size': total_size,
                }
                resp = bili._BiliBili__session.get(
                    f"https://member.bilibili.com/preupload?{bili._auto_os['query']}", params=query,
                    timeout=5)
                ret = resp.json()
                
                # 直接使用upos方法上传
                video_part = await bili.upos(f, total_size, ret, tasks=self.upload_thread_num)
            
            video_part['title'] = self.title
            self.data.append(video_part)
            
            # submit方法不是异步方法，不需要await
            ret = bili.submit()  # 提交视频
            if ret.get('code') == 0:
                bilibili_logger.success(f'[+] {os.path.basename(file_path)}上传 成功')
                return True
            else:
                bilibili_logger.error(f'[-] {os.path.basename(file_path)}上传 失败, error messge: {ret.get("message")}')
                return False
