import argparse
import asyncio
from datetime import datetime
from os.path import exists
from pathlib import Path

from conf import BASE_DIR
from uploader.bilibili_uploader.main import BilibiliUploader, extract_keys_from_json, read_cookie_json_file
from uploader.douyin_uploader.main import douyin_setup, DouYinVideo
from uploader.ks_uploader.main import ks_setup, KSVideo
from uploader.tencent_uploader.main import weixin_setup, TencentVideo
from uploader.tk_uploader.main_chrome import tiktok_setup, TiktokVideo
from utils.base_social_media import get_supported_social_media, get_cli_action, SOCIAL_MEDIA_DOUYIN, \
    SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU, SOCIAL_MEDIA_BILIBILI
from utils.constant import TencentZoneTypes, VideoZoneTypes
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags

# upload_platforms = [SOCIAL_MEDIA_DOUYIN, SOCIAL_MEDIA_BILIBILI, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_KUAISHOU]
upload_platforms = [SOCIAL_MEDIA_BILIBILI]

def parse_schedule(schedule_raw):
    if schedule_raw:
        schedule = datetime.strptime(schedule_raw, '%Y-%m-%d %H:%M')
    else:
        schedule = None
    return schedule


async def main():
    # 主解析器
    parser = argparse.ArgumentParser(description="Upload video to multiple social-media.")
    parser.add_argument("platform", metavar='platform', choices=get_supported_social_media(), help="Choose social-media platform: douyin tencent tiktok kuaishou")

    parser.add_argument("account_name", type=str, help="Account name for the platform: xiaoA")
    subparsers = parser.add_subparsers(dest="action", metavar='action', help="Choose action", required=True)

    actions = get_cli_action()
    for action in actions:
        action_parser = subparsers.add_parser(action, help=f'{action} operation')
        if action == 'login':
            # Login 不需要额外参数
            continue
        elif action == 'upload':
            action_parser.add_argument("video_file", help="Path to the Video file")
            action_parser.add_argument("-pt", "--publish_type", type=int, choices=[0, 1],
                                       help="0 for immediate, 1 for scheduled", default=0)
            action_parser.add_argument('-t', '--schedule', help='Schedule UTC time in %Y-%m-%d %H:%M format')

    # 解析命令行参数
    args = parser.parse_args()
    # 参数校验
    if args.action == 'upload':
        if not exists(args.video_file):
            raise FileNotFoundError(f'Could not find the video file at {args["video_file"]}')
        if args.publish_type == 1 and not args.schedule:
            parser.error("The schedule must must be specified for scheduled publishing.")

    account_file = Path(BASE_DIR / "cookies" / f"{args.platform}_{args.account_name}.json")
    account_file.parent.mkdir(exist_ok=True)

    # 根据 action 处理不同的逻辑
    if args.action == 'login':
        print(f"Logging in with account {args.account_name} on platform {args.platform}")
        if args.platform == SOCIAL_MEDIA_DOUYIN:
            await douyin_setup(str(account_file), handle=True)
        elif args.platform == SOCIAL_MEDIA_TIKTOK:
            await tiktok_setup(str(account_file), handle=True)
        elif args.platform == SOCIAL_MEDIA_TENCENT:
            await weixin_setup(str(account_file), handle=True)
        elif args.platform == SOCIAL_MEDIA_KUAISHOU:
            await ks_setup(str(account_file), handle=True)
    elif args.action == 'upload':
        title, description, tags = get_title_and_hashtags(args.video_file)
        video_file = args.video_file

        if args.publish_type == 0:
            print("Uploading immediately...")
            publish_date = 0
        else:
            print("Scheduling videos...")
            publish_date = parse_schedule(args.schedule)

        for platform in upload_platforms:
            if platform == SOCIAL_MEDIA_DOUYIN:
                await douyin_setup(account_file, handle=False)
                app = DouYinVideo(title, description, video_file, tags, publish_date, account_file)
            elif platform == SOCIAL_MEDIA_TIKTOK:
                await tiktok_setup(account_file, handle=True)
                app = TiktokVideo(title, video_file, tags, publish_date, account_file)
            elif platform == SOCIAL_MEDIA_TENCENT:
                await weixin_setup(account_file, handle=True)
                category = TencentZoneTypes.LIFESTYLE.value  # 标记原创需要否则不需要传
                app = TencentVideo(title, video_file, tags, publish_date, account_file, category)
            elif platform == SOCIAL_MEDIA_KUAISHOU:
                await ks_setup(account_file, handle=True)
                app = KSVideo(title, video_file, tags, publish_date, account_file)
            elif platform == SOCIAL_MEDIA_BILIBILI:
                account_file = Path(BASE_DIR / "cookies" / "bilibili_uploader" / "account.json")
                if not account_file.exists():
                    print(f"{account_file.name} 配置文件不存在")
                    exit()
                cookie_data = read_cookie_json_file(account_file)
                cookie_data = extract_keys_from_json(cookie_data)
                timestamps = generate_schedule_time_next_day(1, 1, daily_times=[16], timestamps=True)
                app = BilibiliUploader(cookie_data, video_file, title, description, VideoZoneTypes.TECH_DIGITAL.value, tags, timestamps[0])
            else:
                print("Wrong platform, please check your input")
                exit()

            if platform == SOCIAL_MEDIA_BILIBILI:
                await app.upload()
            else:
                await app.main()


if __name__ == "__main__":
    asyncio.run(main())
